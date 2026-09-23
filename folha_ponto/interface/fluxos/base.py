"""Estrutura comum dos fluxos guiados (etapas, rodapé) e a etapa final de envio por e-mail."""
import os
import traceback
from tkinter import messagebox

import customtkinter as ctk

from ...dominio.competencia import rotulo_competencia
from .. import tema as T
from ..componentes import DialogoResultado, DialogoServidor, Etapas, Tabela
from ..paginas.base import Pagina
from ..utilitarios import abrir_arquivo


class Fluxo(Pagina):
    """Cabeçalho, indicador de etapas, conteúdo por etapa e rodapé com botões."""
    nav = "inicio"
    TIPO = ""
    TITULO = ""
    ETAPAS = ()

    def __init__(self, master, app):
        super().__init__(master, app)
        self.op_id = None
        self.finalizado = True
        self.competencia = ""
        self.itens = []  # ItemOperacao prontos para envio

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x")
        T.link(topo, "← Início", self.cancelar).pack(side="left")
        self.cab = T.titulo_pagina(self, self.TITULO)
        self.cab.pack(fill="x", pady=(4, 12))
        self.etapas = Etapas(self, self.ETAPAS)
        self.etapas.pack(anchor="w", pady=(0, 16))

        self.corpo = ctk.CTkFrame(self, fg_color="transparent")
        self.corpo.pack(fill="both", expand=True)
        self.rodape = ctk.CTkFrame(self, fg_color="transparent")
        self.rodape.pack(fill="x", pady=(12, 0))
        self.btn_esq = T.botao_secundario(self.rodape, "Cancelar", self.cancelar, width=130)
        self.btn_esq.pack(side="left")
        self.btn_avancar = T.botao_primario(self.rodape, "Avançar  →", lambda: None, width=200)
        self.btn_avancar.pack(side="right")
        self.btn_meio = T.botao_secundario(self.rodape, "", lambda: None, width=170)

        self.frames = [ctk.CTkFrame(self.corpo, fg_color="transparent") for _ in self.ETAPAS]
        self.etapa_envio = EtapaEnvio(self.frames[-1], self)
        self.etapa_envio.pack(fill="both", expand=True)
        self.etapa = 0

    # ---- ciclo de vida ----
    def iniciar(self):
        self.encerrar_se_aberto()
        self.op_id, self.finalizado, self.itens, self.competencia = None, False, [], ""
        self.ir_para(0)

    def comecar_operacao(self, op_id, itens):
        self.op_id, self.itens, self.finalizado = op_id, itens, False

    def encerrar_se_aberto(self, status="Interrompida pelo usuário"):
        """Se o fluxo foi abandonado no meio, registra o que já foi feito e gera o relatório."""
        if self.op_id and not self.finalizado:
            self.finalizado = True
            try:
                self.servicos.auditoria.finalizar(self.op_id, status, self.itens_auditoria())
            except Exception:
                traceback.print_exc()

    def cancelar(self):
        if self.op_id and not self.finalizado:
            if not messagebox.askyesno("Sair do fluxo", "Deseja sair deste fluxo sem enviar os e-mails?\n\n"
                                                        "O que já foi feito ficará registrado no relatório de auditoria."):
                return
            self.encerrar_se_aberto()
        self.finalizado = True
        self.app.mostrar("inicio")

    def ir_para(self, etapa):
        self.etapa = etapa
        for f in self.frames:
            f.pack_forget()
        self.frames[etapa].pack(fill="both", expand=True)
        self.etapas.definir(etapa)
        self.btn_meio.pack_forget()
        self.btn_esq.configure(text="Cancelar", command=self.cancelar)
        self.cab.subtitulo.configure(text="")
        if etapa == 0:
            self.btn_avancar.pack_forget()
        else:
            self.btn_avancar.pack(side="right")
            self.btn_avancar.configure(text="Avançar para o envio  →", state="normal")
        if etapa == len(self.ETAPAS) - 1:
            self.etapa_envio.mostrar()
        else:
            self.mostrar_etapa(etapa)

    def mostrar_etapa(self, etapa):
        raise NotImplementedError

    def atualizar(self):
        if self.etapa == len(self.ETAPAS) - 1:
            self.etapa_envio.atualizar_rotulos()

    def itens_auditoria(self):
        """Tudo o que entra no relatório de auditoria (os fluxos podem acrescentar itens)."""
        return self.itens

    def concluir_sem_enviar(self):
        if not messagebox.askyesno("Concluir sem enviar", "Concluir a operação sem enviar e-mails?"):
            return
        self.finalizado = True
        caminho = self.servicos.envio.concluir_sem_envio(self.op_id, self.itens_auditoria())
        self.app.notificar("Operação concluída. Relatório de auditoria salvo.")
        if messagebox.askyesno("Relatório de auditoria", "Deseja abrir o relatório de auditoria desta operação?"):
            abrir_arquivo(caminho)
        self.app.mostrar("inicio")


class EtapaEnvio(ctk.CTkFrame):
    """Última etapa de ambos os fluxos: destinatários com caixas de seleção e envio."""

    def __init__(self, master, fluxo):
        super().__init__(master, fg_color="transparent")
        self.fluxo = fluxo
        self.app = fluxo.app
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 8))
        self.lbl_contagem = ctk.CTkLabel(barra, text="", font=T.fonte(13, True), text_color=T.TEXTO)
        self.lbl_contagem.pack(side="left")
        T.link(barra, "alterar", lambda: self.app.mostrar("config")).pack(side="right")
        self.lbl_metodo = ctk.CTkLabel(barra, text="", font=T.fonte(12), text_color=T.SUAVE)
        self.lbl_metodo.pack(side="right")
        self.tabela = Tabela(self, self.app, [
            ("nome", "Servidor", 230), ("matricula", "Matrícula", 90, "center"), ("email", "E-mail", 230),
            ("folha", "Folha em anexo", 200), ("acumula", "Acumula", 80, "center"),
        ], altura=8, checkbox=True, ao_marcar=self.atualizar_rotulos, ao_duplo_clique=self._abrir_folha, menu=self._menu)
        self.tabela.pack(fill="both", expand=True)
        ctk.CTkLabel(self, text="Clique na caixa ☐ para marcar ou desmarcar · clique no ☐ do cabeçalho para todos · "
                                "dois cliques abrem a folha · servidores sem e-mail aparecem com —",
                     font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w", pady=(6, 0))
        self._itens = {}

    def mostrar(self):
        f = self.fluxo
        f.btn_esq.configure(text="←  Voltar", command=self._voltar)
        f.btn_meio.configure(text="Concluir sem enviar", command=f.concluir_sem_enviar)
        f.btn_meio.pack(side="right", padx=8)
        f.btn_avancar.configure(command=self.enviar)
        f.cab.subtitulo.configure(text=rotulo_competencia(f.competencia))
        self._itens = {str(i.servidor_id): i for i in f.itens if i.servidor_id and i.arquivo}
        bloqueados = {k for k, i in self._itens.items() if not i.tem_email}
        marcados = {k for k, i in self._itens.items() if i.selecionado} - bloqueados
        linhas = [(k, (i.nome, i.matricula, i.email or "⚠ sem e-mail cadastrado", os.path.basename(i.arquivo), i.acumula or ""),
                   "aviso" if k in bloqueados else None)
                  for k, i in sorted(self._itens.items(), key=lambda kv: kv[1].nome)]
        self.tabela.preencher(linhas, "Nenhuma folha disponível para envio.", marcados=marcados, bloqueados=bloqueados)
        self.atualizar_rotulos()

    def _voltar(self):
        self._guardar_marcacoes()
        self.fluxo.ir_para(len(self.fluxo.ETAPAS) - 2)

    def _guardar_marcacoes(self):
        """Grava nos itens quem está marcado (servidores sem e-mail mantêm o valor anterior)."""
        for k, item in self._itens.items():
            if k not in self.tabela.bloqueados:
                item.selecionado = k in self.tabela.marcados

    def atualizar_rotulos(self):
        cfg = self.app.servicos.configuracoes.email()
        self.lbl_metodo.configure(text=f"Envio via {cfg.descricao()} ·" if cfg.configurado else "⚠ E-mail ainda não configurado ·")
        n = len(self.tabela.marcados)
        self.lbl_contagem.configure(text=f"{n} de {len(self._itens)} servidor(es) selecionado(s) para receber a folha "
                                         f"de {rotulo_competencia(self.fluxo.competencia)}")
        self.fluxo.btn_avancar.configure(text=f"Enviar {n} e-mail(s)" if n else "Enviar e-mails",
                                         state="normal" if n else "disabled")

    def _abrir_folha(self, iid):
        if iid in self._itens:
            abrir_arquivo(self._itens[iid].arquivo)

    def _menu(self, iid):
        return [("Abrir folha", self._abrir_folha),
                ("Editar dados / e-mail do servidor…", lambda i: DialogoServidor(self.app, int(i), self._pos_edicao))]

    def _pos_edicao(self, servidor):
        for item in self.fluxo.itens:
            if item.servidor_id == servidor.id:
                item.atualizar_servidor(servidor)
        self._guardar_marcacoes()
        self.mostrar()

    def enviar(self):
        f = self.fluxo
        selecionados = [self._itens[k] for k in self.tabela.marcados if k in self._itens]
        if not selecionados:
            return
        cfg = self.app.servicos.configuracoes.email()
        if not cfg.configurado:
            if messagebox.askyesno("E-mail não configurado", "O envio de e-mail ainda não foi configurado.\n\n"
                                                             "Deseja abrir as Configurações agora?"):
                self.app.mostrar("config")
            return
        if not messagebox.askyesno(
                "Confirmar envio",
                f"Enviar a folha de ponto de {rotulo_competencia(f.competencia)} para {len(selecionados)} servidor(es)?\n\n"
                f"Cada servidor recebe apenas a sua própria folha, no e-mail cadastrado.\nEnvio via {cfg.descricao()}."):
            return

        def trabalho(progresso):
            resultado = self.app.servicos.envio.executar(f.op_id, f.competencia, f.TIPO, selecionados,
                                                         f.itens_auditoria(), progresso)
            f.finalizado = True
            return resultado

        self.app.executar_tarefa("Enviando e-mails", trabalho,
                                 lambda r: DialogoResultado(self.app, r, ao_fechar=lambda: self.app.mostrar("inicio")))
