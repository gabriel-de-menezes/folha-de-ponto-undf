"""Fluxo 1: gerar as folhas do mês a partir da planilha, conferir e enviar por e-mail."""
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...dominio.competencia import rotulo_competencia
from ...dominio.entidades import TipoOperacao
from ...dominio.regras import data_br
from .. import tema as T
from ..componentes import DialogoServidor, PainelPreview, SeletorMes, Tabela
from ..utilitarios import TIPOS_PLANILHA, abrir_arquivo, mostrar_na_pasta, salvar_copia
from .base import Fluxo


class FluxoGerar(Fluxo):
    TIPO = TipoOperacao.GERACAO
    TITULO = "Gerar e enviar folhas de ponto"
    ETAPAS = ("Mês e planilha", "Conferir folhas", "Enviar por e-mail")

    def __init__(self, master, app):
        super().__init__(master, app)
        # ---- Etapa 1: mês e planilha ----
        f0 = self.frames[0]
        card_mes = T.cartao(f0)
        card_mes.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card_mes, text="1. Mês de referência", font=T.fonte(16, True)).pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(card_mes, text="O mês escolhido vai no cabeçalho da folha e define o calendário (fins de semana e dias do mês).",
                     font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w", padx=24)
        self.seletor = SeletorMes(card_mes)
        self.seletor.pack(anchor="w", padx=24, pady=(12, 20))

        card_pl = T.cartao(f0)
        card_pl.pack(fill="x")
        ctk.CTkLabel(card_pl, text="2. Planilha de servidores", font=T.fonte(16, True)).pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(card_pl, text="Será gerada uma folha para cada servidor da planilha. Escolha uma opção para começar:",
                     font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w", padx=24)
        opcoes = ctk.CTkFrame(card_pl, fg_color="transparent")
        opcoes.pack(fill="x", padx=24, pady=(14, 8))
        opcoes.grid_columnconfigure((0, 1), weight=1, uniform="o")
        self.btn_base = T.botao_primario(opcoes, "Usar planilha base do sistema", lambda: self._comecar(usar_base=True),
                                         height=64, font=T.fonte(14, True))
        self.btn_base.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        T.botao_secundario(opcoes, "Enviar uma nova planilha…", lambda: self._comecar(usar_base=False),
                           height=64, font=T.fonte(14, True)).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.lbl_base = ctk.CTkLabel(opcoes, text="", font=T.fonte(12), text_color=T.SUAVE)
        self.lbl_base.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.var_salvar_base = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opcoes, text="Guardar a nova planilha como planilha base", variable=self.var_salvar_base,
                        font=T.fonte(12), fg_color=T.PRIMARIA).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        T.link(card_pl, "Baixar modelo da planilha (.xlsx)",
               lambda: salvar_copia(self.servicos.armazenamento.modelo_planilha, "Salvar modelo da planilha")
               ).pack(anchor="w", padx=18, pady=(4, 16))

        # ---- Etapa 2: conferir folhas ----
        f1 = self.frames[1]
        ctk.CTkLabel(f1, text="Clique em um servidor para ver a folha gerada. Dois cliques abrem o arquivo.",
                     font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w", pady=(0, 8))
        corpo = ctk.CTkFrame(f1, fg_color="transparent")
        corpo.pack(fill="both", expand=True)
        self.painel = PainelPreview(corpo)
        self.painel.pack(side="right", fill="y")
        T.botao_secundario(self.painel.acoes, "Abrir arquivo",
                           lambda: self.painel.caminho and abrir_arquivo(self.painel.caminho)).pack(fill="x")
        self.tab_folhas = Tabela(corpo, app, [
            ("nome", "Servidor", 220), ("matricula", "Matrícula", 90, "center"), ("email", "E-mail", 210),
            ("folha", "Folha", 70, "center"),
        ], altura=8, ao_selecionar=self._ver_folha, ao_duplo_clique=self._abrir_folha, menu=lambda i: [
            ("Abrir folha", self._abrir_folha),
            ("Mostrar na pasta", lambda x: mostrar_na_pasta(self._item(x).arquivo)),
            ("Editar dados do servidor…", lambda x: DialogoServidor(app, int(x), self._regerar)),
        ])
        self.tab_folhas.pack(side="left", fill="both", expand=True, padx=(0, 12))

    def _item(self, iid):
        return next((i for i in self.itens if str(i.servidor_id) == str(iid)), None)

    def mostrar_etapa(self, etapa):
        if etapa == 0:
            info = self.servicos.servidores.planilha_base()
            if info:
                self.btn_base.configure(state="normal")
                self.lbl_base.configure(text=f"{info.nome} · {info.quantidade} servidor(es) · definida em {data_br(info.definida_em)}")
            else:
                self.btn_base.configure(state="disabled")
                self.lbl_base.configure(text="Nenhuma planilha base definida (defina em Servidores).")
        elif etapa == 1:
            self.cab.subtitulo.configure(text=f"{rotulo_competencia(self.competencia)} · {len(self.itens)} folha(s) gerada(s)")
            self.btn_avancar.configure(command=lambda: self.ir_para(2))
            self._preencher_folhas()

    def _preencher_folhas(self):
        linhas = [(i.servidor_id, (i.nome, i.matricula, i.email or "⚠ sem e-mail",
                                   "—" if not i.arquivo else ("PDF" if i.arquivo.lower().endswith(".pdf") else "Word")),
                   None if i.tem_email and i.arquivo else "aviso") for i in self.itens]
        self.tab_folhas.preencher(linhas, "Nenhuma folha gerada.")
        if linhas and not self.tab_folhas.selecionado():
            self.tab_folhas.selecionar(linhas[0][0])

    def _ver_folha(self, iid):
        i = self._item(iid)
        if i:
            self.painel.mostrar(i.arquivo, f"{i.nome}\nMatrícula {i.matricula} · {rotulo_competencia(self.competencia)}\n"
                                           f"{os.path.basename(i.arquivo or '') or 'Folha não gerada'}")

    def _abrir_folha(self, iid):
        i = self._item(iid)
        if i:
            abrir_arquivo(i.arquivo)

    def _comecar(self, usar_base):
        planilha = None
        if not usar_base:
            planilha = filedialog.askopenfilename(title="Selecione a planilha de servidores", filetypes=TIPOS_PLANILHA)
            if not planilha:
                return
        competencia = self.seletor.get()
        salvar_base = not usar_base and self.var_salvar_base.get()
        self.competencia = competencia

        def fim(resultado):
            self.comecar_operacao(resultado.op_id, resultado.itens)
            if resultado.erros:
                messagebox.showwarning("Gerar folhas", "Algumas folhas não foram geradas:\n" + "\n".join(resultado.erros[:10]))
            if resultado.sem_pdf:
                self.app.notificar("Folhas geradas em Word — instale o Microsoft Word ou LibreOffice para gerar em PDF.", "aviso")
            else:
                self.app.notificar(f"{len(resultado.itens)} folha(s) de {rotulo_competencia(competencia)} gerada(s).")
            self.ir_para(1)

        self.app.executar_tarefa(
            "Gerando folhas de ponto",
            lambda progresso: self.servicos.gerar_folhas.executar(competencia, planilha, salvar_base, progresso), fim)

    def _regerar(self, servidor):
        """Depois de corrigir os dados de um servidor na conferência, gera a folha dele de novo."""
        item = self._item(servidor.id)
        if not item:
            return

        def fim(_):
            self._preencher_folhas()
            self._ver_folha(str(servidor.id))
            self.app.notificar(f"Folha de {servidor.nome} gerada novamente com os dados corrigidos.")

        self.app.executar_tarefa("Gerando a folha novamente",
                                 lambda p: self.servicos.gerar_folhas.regerar(self.op_id, self.competencia, item), fim)
