from tkinter import messagebox

import customtkinter as ctk

from ...dominio.competencia import rotulo_competencia
from ...dominio.entidades import StatusEnvio, codigo_operacao
from ...dominio.regras import data_br
from .. import tema as T
from ..componentes import Tabela
from ..utilitarios import abrir_arquivo, abrir_pasta, mostrar_na_pasta
from .base import Pagina
from .inicio import tag_status


class PaginaAuditoria(Pagina):
    nav = "auditoria"

    def __init__(self, master, app):
        super().__init__(master, app)
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", pady=(0, 12))
        T.titulo_pagina(topo, "Auditoria", "Cada operação gera um relatório em PDF com os servidores, arquivos e envios."
                        ).pack(side="left")
        T.botao_secundario(topo, "Abrir pasta de relatórios",
                           lambda: abrir_pasta(self.servicos.armazenamento.pasta_relatorios)).pack(side="right", anchor="s")
        self.seg = ctk.CTkSegmentedButton(self, values=["Operações", "E-mails enviados"], command=lambda v: self.atualizar(),
                                          selected_color=T.PRIMARIA, selected_hover_color=T.PRIMARIA_HOVER, height=34,
                                          font=T.fonte(13))
        self.seg.set("Operações")
        self.seg.pack(anchor="w", pady=(0, 12))

        self.barra_env = ctk.CTkFrame(self, fg_color="transparent")
        self.busca = T.entrada(self.barra_env, placeholder_text="Buscar por nome, CPF ou matrícula do servidor…")
        self.busca.pack(side="left", fill="x", expand=True)
        self.busca.bind("<KeyRelease>", lambda e: self.atualizar())
        self.opt_status = ctk.CTkOptionMenu(self.barra_env, values=["Todos", "Enviados", "Com erro"], width=130, height=36,
                                            command=lambda v: self.atualizar(), fg_color=T.PRIMARIA,
                                            button_color=T.PRIMARIA_HOVER)
        self.opt_status.pack(side="left", padx=8)
        self.btn_reenviar = T.botao_primario(self.barra_env, "Reenviar os com erro", self._reenviar, width=180)
        self.btn_reenviar.pack(side="left")

        self.tab_ops = Tabela(self, app, [
            ("op", "Operação", 90, "center"), ("inicio", "Início", 130, "center"), ("tipo", "Tipo", 250),
            ("comp", "Mês", 110, "center"), ("usuario", "Usuário", 120, "center"), ("env", "Enviados", 90, "center"),
            ("status", "Situação", 170, "center"),
        ], altura=10, ao_duplo_clique=lambda i: app.abrir_relatorio(int(i)), menu=lambda i: [
            ("Abrir relatório", lambda x: app.abrir_relatorio(int(x))),
            ("Gerar relatório novamente", lambda x: app.abrir_relatorio(int(x), regerar=True)),
            ("Mostrar na pasta", lambda x: mostrar_na_pasta(self.servicos.auditoria.relatorio(int(x)))),
        ])
        self.tab_env = Tabela(self, app, [
            ("data", "Data/hora", 130, "center"), ("op", "Operação", 90, "center"), ("servidor", "Servidor", 200),
            ("matricula", "Matrícula", 90, "center"), ("dest", "Destinatário", 200), ("comp", "Mês", 100, "center"),
            ("status", "Situação", 90, "center"), ("det", "Detalhes", 220),
        ], altura=10, ao_duplo_clique=self._abrir_anexo)
        self.lbl_dica = ctk.CTkLabel(self, text="", font=T.fonte(12), text_color=T.SUAVE)
        self.lbl_dica.pack(side="bottom", anchor="w", pady=(6, 0))
        self._envios = {}

    def _abrir_anexo(self, iid):
        envio = self._envios.get(iid)
        if envio and envio.anexo:
            abrir_arquivo(envio.anexo)

    def atualizar(self):
        if self.seg.get() == "Operações":
            self.barra_env.pack_forget()
            self.tab_env.pack_forget()
            self.tab_ops.pack(fill="both", expand=True)
            self.lbl_dica.configure(text="Dois cliques abrem o relatório de auditoria (PDF) da operação.")
            self.tab_ops.preencher([
                (o.id, (o.codigo, data_br(o.iniciado_em), o.descricao_tipo, rotulo_competencia(o.competencia), o.usuario,
                        f"{o.qtd_enviados}/{o.qtd_itens}", o.status), tag_status(o.status))
                for o in self.servicos.auditoria.listar()
            ], "Nenhuma operação realizada ainda.")
        else:
            self.tab_ops.pack_forget()
            self.barra_env.pack(fill="x", pady=(0, 8), before=self.lbl_dica)
            self.tab_env.pack(fill="both", expand=True)
            self.lbl_dica.configure(text="Dois cliques abrem o arquivo que foi enviado.")
            status = {"Todos": "", "Enviados": StatusEnvio.ENVIADO, "Com erro": StatusEnvio.ERRO}[self.opt_status.get()]
            envios = self.servicos.consultas.envios_realizados(self.busca.get(), status)
            self._envios = {str(e.id): e for e in envios}
            self.tab_env.preencher([
                (e.id, (data_br(e.enviado_em), codigo_operacao(e.operacao_id) if e.operacao_id else "—", e.nome, e.matricula,
                        e.destinatario, rotulo_competencia(e.competencia),
                        "✓ Enviado" if e.status == StatusEnvio.ENVIADO else "✕ Erro", e.detalhes),
                 "ok" if e.status == StatusEnvio.ENVIADO else "erro")
                for e in envios
            ], "Nenhum e-mail enviado ainda." if not self.busca.get() else "Nenhum envio encontrado para a busca.")

    def _reenviar(self):
        erros = self.servicos.consultas.envios_realizados("", StatusEnvio.ERRO)
        if not erros:
            messagebox.showinfo("Reenviar", "Não há envios com erro registrados.")
            return
        if not self.servicos.configuracoes.email().configurado:
            messagebox.showwarning("Reenviar", "O envio de e-mail ainda não foi configurado (menu Configurações).")
            return
        if not messagebox.askyesno("Reenviar os com erro",
                                   "Reenviar a folha a todos os servidores cujo último envio deu erro?\n\n"
                                   "Corrija antes o e-mail dos servidores, se for o caso (menu Servidores)."):
            return

        def fim(r):
            op_id, resultado = r
            messagebox.showinfo("Reenvio concluído", f"{resultado.enviados} de {resultado.total} e-mail(s) enviado(s)."
                                + (f"\n\nAinda com erro:\n• " + "\n• ".join(resultado.erros[:8]) if resultado.erros else ""))
            self.atualizar()

        self.app.executar_tarefa("Reenviando e-mails", lambda p: self.servicos.envio.reenviar_erros(erros, p), fim)
