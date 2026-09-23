import customtkinter as ctk

from ...aplicacao.folhas_assinadas import LIMITE_ARQUIVOS
from ...dominio.competencia import rotulo_competencia
from ...dominio.regras import data_br
from .. import tema as T
from ..componentes import Tabela
from .base import Pagina


def tag_status(status):
    s = status.lower()
    if status == "Concluída":
        return "ok"
    if "erro" in s or "falha" in s:
        return "erro"
    return None if status == "Em andamento" else "aviso"


class PaginaInicio(Pagina):
    nav = "inicio"

    def __init__(self, master, app):
        super().__init__(master, app)
        T.titulo_pagina(self, "O que você quer fazer?",
                        "Escolha um fluxo. Cada um guia você passo a passo e gera um relatório de auditoria no final."
                        ).pack(fill="x", pady=(0, 20))

        grade = ctk.CTkFrame(self, fg_color="transparent")
        grade.pack(fill="x")
        grade.grid_columnconfigure((0, 1), weight=1, uniform="c")
        self._cartao_fluxo(grade, 0, "📄", "Gerar e enviar folhas de ponto",
                           "Escolha o mês e a planilha de servidores. O sistema gera a folha de cada servidor para "
                           "você conferir e enviar por e-mail.", lambda: app.iniciar_fluxo("fluxo_gerar"))
        self._cartao_fluxo(grade, 1, "✍", "Enviar folhas assinadas",
                           f"Escolha o mês e importe até {LIMITE_ARQUIVOS} folhas assinadas (PDF ou imagem). O sistema "
                           "identifica de quem é cada folha para você conferir e enviar por e-mail.",
                           lambda: app.iniciar_fluxo("fluxo_assinadas"))

        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", pady=(28, 8))
        ctk.CTkLabel(cab, text="Últimas operações", font=T.fonte(15, True), text_color=T.TEXTO).pack(side="left")
        T.link(cab, "Ver auditoria completa →", lambda: app.mostrar("auditoria")).pack(side="right")
        self.tabela = Tabela(self, app, [
            ("op", "Operação", 90, "center"), ("data", "Data", 130, "center"), ("tipo", "Tipo", 260),
            ("comp", "Mês", 120, "center"), ("env", "E-mails enviados", 130, "center"), ("status", "Situação", 170, "center"),
        ], altura=6, ao_duplo_clique=lambda iid: app.abrir_relatorio(int(iid)))
        self.tabela.pack(fill="both", expand=True)
        ctk.CTkLabel(self, text="Dois cliques em uma operação abrem o relatório de auditoria em PDF.",
                     font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w", pady=(6, 0))

    def _cartao_fluxo(self, master, coluna, icone, titulo, descricao, acao):
        card = T.cartao(master, border_width=2)
        card.grid(row=0, column=coluna, padx=(0, 10) if coluna == 0 else (10, 0), sticky="nsew")
        icone_lbl = ctk.CTkLabel(card, text=icone, width=64, height=64, corner_radius=32, fg_color=T.PRIMARIA,
                                 text_color="#FFFFFF", font=T.fonte(28))
        icone_lbl.pack(anchor="w", padx=28, pady=(28, 14))
        titulo_lbl = ctk.CTkLabel(card, text=titulo, font=T.fonte(20, True), text_color=T.TEXTO, anchor="w")
        titulo_lbl.pack(anchor="w", fill="x", padx=28)
        desc_lbl = ctk.CTkLabel(card, text=descricao, font=T.fonte(13), text_color=T.SUAVE, justify="left",
                                anchor="w", wraplength=380)
        desc_lbl.pack(anchor="w", fill="x", padx=28, pady=(6, 18))
        T.botao_primario(card, "Começar  →", acao, height=44, width=160).pack(anchor="w", padx=28, pady=(0, 28))
        # O cartão inteiro é clicável, com destaque ao passar o mouse
        for w in (card, icone_lbl, titulo_lbl, desc_lbl):
            w.bind("<Button-1>", lambda e: acao())
            w.bind("<Enter>", lambda e: card.configure(border_color=T.PRIMARIA))
            w.bind("<Leave>", lambda e: card.configure(border_color=T.BORDA))
            w.configure(cursor="hand2")

    def atualizar(self):
        self.tabela.preencher([
            (o.id, (o.codigo, data_br(o.iniciado_em), o.descricao_tipo, rotulo_competencia(o.competencia),
                    f"{o.qtd_enviados}/{o.qtd_itens}", o.status), tag_status(o.status))
            for o in self.servicos.auditoria.listar()[:15]
        ], "Nenhuma operação realizada ainda.")
