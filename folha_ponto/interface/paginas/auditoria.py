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
            ("data", "Data/hora", 130, "center"), ("op", "Operação", 90, "center"), ("servidor", "Servidor", 220),
            ("dest", "Destinatário", 220), ("comp", "Mês", 110, "center"), ("status", "Situação", 100, "center"),
            ("det", "Detalhes", 240),
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
            self.tab_env.pack(fill="both", expand=True)
            self.lbl_dica.configure(text="Dois cliques abrem o arquivo que foi enviado.")
            envios = self.servicos.consultas.envios_realizados()
            self._envios = {str(e.id): e for e in envios}
            self.tab_env.preencher([
                (e.id, (data_br(e.enviado_em), codigo_operacao(e.operacao_id) if e.operacao_id else "—", e.nome,
                        e.destinatario, rotulo_competencia(e.competencia),
                        "✓ Enviado" if e.status == StatusEnvio.ENVIADO else "✕ Erro", e.detalhes),
                 "ok" if e.status == StatusEnvio.ENVIADO else "erro")
                for e in envios
            ], "Nenhum e-mail enviado ainda.")
