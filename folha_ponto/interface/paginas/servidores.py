from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...dominio.regras import ErroDominio, data_br
from .. import tema as T
from ..componentes import DialogoServidor, Tabela
from ..utilitarios import TIPOS_PLANILHA, abrir_arquivo, salvar_copia
from .base import Pagina


class PaginaServidores(Pagina):
    nav = "servidores"

    def __init__(self, master, app):
        super().__init__(master, app)
        cab = T.titulo_pagina(self, "Servidores")
        cab.pack(fill="x", pady=(0, 12))
        self.lbl_sub = cab.subtitulo

        base = T.cartao(self)
        base.pack(fill="x", pady=(0, 12))
        esq = ctk.CTkFrame(base, fg_color="transparent")
        esq.pack(side="left", fill="x", expand=True, padx=20, pady=16)
        ctk.CTkLabel(esq, text="Planilha base", font=T.fonte(15, True)).pack(anchor="w")
        self.lbl_base = ctk.CTkLabel(esq, text="", font=T.fonte(12), text_color=T.SUAVE, justify="left", anchor="w")
        self.lbl_base.pack(anchor="w", fill="x")
        links = ctk.CTkFrame(esq, fg_color="transparent")
        links.pack(anchor="w")
        T.link(links, "Abrir planilha base", lambda: abrir_arquivo(self.servicos.armazenamento.planilha_base)).pack(side="left")
        T.link(links, "Baixar modelo da planilha",
               lambda: salvar_copia(self.servicos.armazenamento.modelo_planilha, "Salvar modelo da planilha")
               ).pack(side="left", padx=8)
        self.btn_base = T.botao_primario(base, "Definir planilha base…", self.definir_base)
        self.btn_base.pack(side="right", padx=20)

        self.busca = T.entrada(self, placeholder_text="Buscar por nome, matrícula, CPF ou e-mail…")
        self.busca.pack(fill="x", pady=(0, 12))
        self.busca.bind("<KeyRelease>", lambda e: self.atualizar())
        self.tabela = Tabela(self, app, [
            ("nome", "Nome", 260), ("matricula", "Matrícula", 110, "center"), ("cpf", "CPF", 120, "center"),
            ("email", "E-mail pessoal", 230), ("carga", "Carga horária", 100, "center"),
            ("acumula", "Acumula cargo", 110, "center"),
        ], altura=10, ao_duplo_clique=lambda i: DialogoServidor(app, int(i)),
            menu=lambda i: [("Editar dados…", lambda x: DialogoServidor(app, int(x))),
                            ("Ver folhas no Arquivo", self._ver_no_arquivo)])
        self.tabela.pack(fill="both", expand=True)

    def definir_base(self):
        caminho = filedialog.askopenfilename(title="Selecione a planilha base de servidores", filetypes=TIPOS_PLANILHA)
        if not caminho:
            return
        try:
            resultado = self.servicos.servidores.definir_planilha_base(caminho)
        except ErroDominio as e:
            messagebox.showwarning("Planilha base", str(e))
            return
        self.app.notificar(f"Planilha base definida. {resultado.mensagem}")
        self.atualizar()

    def _ver_no_arquivo(self, iid):
        servidor = self.servicos.servidores.obter(int(iid))
        self.app.mostrar("arquivo")
        self.app.paginas["arquivo"].buscar(servidor.matricula)

    def atualizar(self):
        info = self.servicos.servidores.planilha_base()
        if info:
            self.lbl_base.configure(text=f"{info.nome} · {info.quantidade} servidor(es) · definida em {data_br(info.definida_em)}\n"
                                         "Usada no fluxo “Gerar e enviar folhas de ponto”.")
            self.btn_base.configure(text="Substituir planilha base…")
        else:
            self.lbl_base.configure(text="Nenhuma planilha base definida. Defina uma para usá-la direto no fluxo de geração.")
            self.btn_base.configure(text="Definir planilha base…")
        servidores = self.servicos.servidores.listar(self.busca.get())
        self.lbl_sub.configure(text=f"{self.servicos.servidores.contar()} cadastrado(s) · dois cliques para editar")
        self.tabela.preencher(
            [(s.id, (s.nome, s.matricula, s.cpf, s.email or "⚠ sem e-mail", s.carga_horaria, s.acumula_cargo),
              None if s.tem_email else "aviso") for s in servidores],
            "Nenhum servidor. Defina a planilha base acima." if not self.busca.get() else "Nenhum resultado para a busca.")
