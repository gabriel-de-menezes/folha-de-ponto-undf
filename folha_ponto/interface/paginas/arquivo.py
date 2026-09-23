import customtkinter as ctk

from ...dominio.competencia import normalizar_competencia, rotulo_competencia
from ...dominio.regras import data_br
from .. import tema as T
from ..componentes import PainelPreview, Tabela
from ..utilitarios import abrir_arquivo, mostrar_na_pasta, salvar_copia
from .base import Pagina

TODOS = "Todos os meses"


class PaginaArquivo(Pagina):
    nav = "arquivo"

    def __init__(self, master, app):
        super().__init__(master, app)
        T.titulo_pagina(self, "Arquivo de folhas", "Todas as folhas geradas e assinadas, de todos os meses.").pack(fill="x", pady=(0, 12))
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))
        self.busca = T.entrada(barra, placeholder_text="Buscar por nome ou matrícula…")
        self.busca.pack(side="left", fill="x", expand=True)
        self.busca.bind("<KeyRelease>", lambda e: self.atualizar())
        self.opt_comp = ctk.CTkOptionMenu(barra, values=[TODOS], command=lambda v: self.atualizar(),
                                          height=36, width=200, fg_color=T.PRIMARIA, button_color=T.PRIMARIA_HOVER)
        self.opt_comp.pack(side="left", padx=(8, 0))

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True)
        self.painel = PainelPreview(corpo)
        self.painel.pack(side="right", fill="y")
        T.botao_primario(self.painel.acoes, "Abrir arquivo",
                         lambda: self.painel.caminho and abrir_arquivo(self.painel.caminho)).pack(fill="x")
        T.link(self.painel.acoes, "Salvar uma cópia…",
               lambda: self.painel.caminho and salvar_copia(self.painel.caminho)).pack(pady=(6, 0))
        self.tabela = Tabela(corpo, app, [
            ("tipo", "Tipo", 90, "center"), ("nome", "Servidor", 230), ("matricula", "Matrícula", 100, "center"),
            ("comp", "Mês", 120, "center"), ("data", "Registrada em", 130, "center"),
        ], altura=10, ao_selecionar=self._selecionar, ao_duplo_clique=self._abrir, menu=lambda i: [
            ("Abrir arquivo", self._abrir),
            ("Salvar uma cópia…", lambda x: salvar_copia(self._folhas[x].caminho)),
            ("Mostrar na pasta", lambda x: mostrar_na_pasta(self._folhas[x].caminho)),
        ])
        self.tabela.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self._folhas = {}

    def buscar(self, termo):
        self.busca.delete(0, "end")
        self.busca.insert(0, termo or "")
        self.opt_comp.set(TODOS)
        self.atualizar()

    def atualizar(self):
        rotulos = [TODOS] + [rotulo_competencia(c) for c in self.servicos.consultas.competencias()]
        self.opt_comp.configure(values=rotulos)
        if self.opt_comp.get() not in rotulos:
            self.opt_comp.set(TODOS)
        filtro = self.opt_comp.get()
        competencia = "" if filtro == TODOS else normalizar_competencia(filtro)
        folhas = self.servicos.consultas.folhas_arquivadas(self.busca.get(), competencia)
        self._folhas = {f.chave: f for f in folhas}
        self.tabela.preencher([
            (f.chave, ("Assinada" if f.assinada else "Gerada", f.nome, f.matricula, rotulo_competencia(f.competencia),
                       data_br(f.data_registro)), "ok" if f.assinada else None)
            for f in folhas
        ], "Nenhuma folha encontrada.")
        if not self.tabela.selecionado():
            self.painel.limpar()

    def _selecionar(self, iid):
        f = self._folhas.get(iid)
        if f:
            tipo = "Folha assinada (digitalizada)" if f.assinada else "Folha gerada"
            self.painel.mostrar(f.caminho, f"{f.nome}\nMatrícula {f.matricula} · {rotulo_competencia(f.competencia)}\n{tipo}")

    def _abrir(self, iid):
        if iid in self._folhas:
            abrir_arquivo(self._folhas[iid].caminho)
