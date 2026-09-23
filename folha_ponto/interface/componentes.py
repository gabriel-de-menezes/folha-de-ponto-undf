"""Componentes visuais reutilizáveis: tabela, pré-visualização, seletor de mês, etapas e diálogos."""
import dataclasses
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

import customtkinter as ctk

from ..dominio.competencia import MESES, montar_competencia
from ..dominio.regras import ErroDominio
from . import tema as T
from .utilitarios import abrir_arquivo, gerar_preview


class Tabela(ctk.CTkFrame):
    """Treeview estilizada com barra de rolagem, linhas zebradas, mensagem de vazio, menu de contexto
    e (opcional) uma coluna de caixas de seleção. Cada linha é identificada por um iid (string)."""

    MARCADO, DESMARCADO, BLOQUEADO = "☑", "☐", "—"

    def __init__(self, master, app, colunas, altura=12, ao_duplo_clique=None, menu=None, ao_selecionar=None,
                 checkbox=False, ao_marcar=None):
        super().__init__(master, fg_color=T.CARTAO, corner_radius=12, border_width=1, border_color=T.BORDA)
        self.checkbox = checkbox
        self.ao_marcar = ao_marcar
        self.marcados, self.bloqueados = set(), set()
        if checkbox:
            colunas = [("_sel", self.DESMARCADO, 48, "center")] + list(colunas)
        self.tree = ttk.Treeview(self, columns=[c[0] for c in colunas], show="headings", height=altura, selectmode="browse")
        for chave, titulo, largura, *resto in colunas:
            ancora = resto[0] if resto else "w"
            self.tree.heading(chave, text=titulo, anchor=ancora)
            self.tree.column(chave, width=largura, minwidth=40, anchor=ancora, stretch=chave != "_sel")
        barra = ctk.CTkScrollbar(self, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        barra.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=8)
        self.lbl_vazio = ctk.CTkLabel(self, text="", text_color=T.SUAVE, font=T.fonte(13))

        self._menu = menu
        if ao_duplo_clique:
            self.tree.bind("<Double-1>", lambda e: self._duplo(e, ao_duplo_clique))
            self.tree.bind("<Return>", lambda e: self.selecionado() and ao_duplo_clique(self.selecionado()))
        if ao_selecionar:
            self.tree.bind("<<TreeviewSelect>>", lambda e: self.selecionado() and ao_selecionar(self.selecionado()))
        if menu:
            self.tree.bind("<Button-3>", self._abrir_menu)
        if checkbox:
            self.tree.heading("_sel", command=self.alternar_todos)
            self.tree.bind("<Button-1>", self._clique, add="+")
            self.tree.bind("<space>", lambda e: self.selecionado() and self.alternar(self.selecionado()))

        app.tabelas.append(self)
        self.aplicar_cores(app.cores_tabela)

    def aplicar_cores(self, cores):
        self.tree.tag_configure("impar", background=cores["impar"])
        for tag in ("ok", "erro", "aviso", "suave"):
            self.tree.tag_configure(tag, foreground=cores[tag])

    def preencher(self, linhas, texto_vazio="Nada por aqui ainda.", marcados=None, bloqueados=None):
        """linhas: lista de (iid, valores, tag_status ou None)."""
        anterior = self.selecionado()
        if marcados is not None:
            self.marcados = {str(m) for m in marcados}
        if bloqueados is not None:
            self.bloqueados = {str(b) for b in bloqueados}
        self.tree.delete(*self.tree.get_children())
        for i, (iid, valores, tag) in enumerate(linhas):
            iid = str(iid)
            tags = tuple(t for t in (tag, "impar" if i % 2 else None) if t)
            if self.checkbox:
                valores = (self._simbolo(iid), *valores)
            self.tree.insert("", "end", iid=iid, values=valores, tags=tags)
        self.marcados &= set(self.iids())
        if anterior and self.tree.exists(anterior):
            self.tree.selection_set(anterior)
            self.tree.see(anterior)
        if linhas:
            self.lbl_vazio.place_forget()
        else:
            self.lbl_vazio.configure(text=texto_vazio)
            self.lbl_vazio.place(relx=0.5, rely=0.5, anchor="center")
        self._atualizar_cabecalho()

    def selecionado(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def selecionar(self, iid):
        if iid and self.tree.exists(str(iid)):
            self.tree.selection_set(str(iid))
            self.tree.focus(str(iid))
            self.tree.see(str(iid))

    def limpar_selecao(self):
        self.tree.selection_remove(*self.tree.selection())

    def iids(self):
        return list(self.tree.get_children())

    # ---- caixas de seleção ----
    def _simbolo(self, iid):
        if iid in self.bloqueados:
            return self.BLOQUEADO
        return self.MARCADO if iid in self.marcados else self.DESMARCADO

    def _clique(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#1":
            iid = self.tree.identify_row(event.y)
            if iid:
                self.alternar(iid)

    def alternar(self, iid):
        if iid in self.bloqueados:
            return
        self.marcados ^= {iid}
        self.tree.set(iid, "_sel", self._simbolo(iid))
        self._atualizar_cabecalho()
        if self.ao_marcar:
            self.ao_marcar()

    def alternar_todos(self):
        elegiveis = set(self.iids()) - self.bloqueados
        self.marcados = set() if elegiveis and elegiveis <= self.marcados else elegiveis
        for iid in self.iids():
            self.tree.set(iid, "_sel", self._simbolo(iid))
        self._atualizar_cabecalho()
        if self.ao_marcar:
            self.ao_marcar()

    def _atualizar_cabecalho(self):
        if self.checkbox:
            elegiveis = set(self.iids()) - self.bloqueados
            todos = elegiveis and elegiveis <= self.marcados
            self.tree.heading("_sel", text=self.MARCADO if todos else self.DESMARCADO)

    # ---- eventos ----
    def _duplo(self, event, acao):
        if self.checkbox and self.tree.identify_column(event.x) == "#1":
            return  # duplo clique na caixa de seleção só marca/desmarca
        if self.selecionado():
            acao(self.selecionado())

    def _abrir_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        itens = self._menu(iid)
        if not itens:
            return
        menu = tk.Menu(self, tearoff=0, font=(T.FONTE, 10))
        for rotulo, acao in itens:
            if rotulo is None:
                menu.add_separator()
            else:
                menu.add_command(label=rotulo, command=lambda a=acao, i=iid: a(i))
        menu.tk_popup(event.x_root, event.y_root)


class PainelPreview(ctk.CTkFrame):
    """Cartão lateral com miniatura clicável (abre o arquivo), texto informativo e área de ações."""

    def __init__(self, master, largura=360):
        super().__init__(master, fg_color=T.CARTAO, corner_radius=12, border_width=1, border_color=T.BORDA, width=largura)
        self.pack_propagate(False)
        self.caminho = None
        self._img = None
        # Empacotada primeiro para nunca ser espremida pela imagem
        self.acoes = ctk.CTkFrame(self, fg_color="transparent")
        self.acoes.pack(side="bottom", fill="x", padx=16, pady=16)
        self.lbl_img = ctk.CTkLabel(self, text="Selecione uma folha\npara visualizar", text_color=T.SUAVE, height=220)
        self.lbl_img.pack(padx=16, pady=(16, 8), fill="x")
        self.lbl_img.bind("<Button-1>", lambda e: self.caminho and abrir_arquivo(self.caminho))
        self.lbl_info = ctk.CTkLabel(self, text="", wraplength=largura - 32, justify="left", anchor="w", font=T.fonte(12))
        self.lbl_info.pack(padx=16, pady=(0, 8), fill="x")

    def mostrar(self, caminho, info=""):
        self.caminho = caminho
        self._img = gerar_preview(caminho)
        if self._img:
            self.lbl_img.configure(image=self._img, text="", cursor="hand2")
        elif caminho:
            self.lbl_img.configure(image=None, text="Sem pré-visualização para este tipo de arquivo.\n"
                                                    "Clique em “Abrir arquivo”.", cursor="")
        else:
            self.lbl_img.configure(image=None, text="Sem folha", cursor="")
        self.lbl_info.configure(text=info)

    def limpar(self, texto="Selecione uma folha\npara visualizar"):
        self.caminho = None
        self._img = None
        self.lbl_img.configure(image=None, text=texto, cursor="")
        self.lbl_info.configure(text="")


class SeletorMes(ctk.CTkFrame):
    """Mês + ano, devolvendo a competência no formato "SETEMBRO/2026"."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        hoje = date.today()
        self.opt_mes = ctk.CTkOptionMenu(self, values=[m.capitalize() for m in MESES], width=170, height=40,
                                         font=T.fonte(14), fg_color=T.PRIMARIA, button_color=T.PRIMARIA_HOVER)
        self.opt_mes.set(MESES[hoje.month - 1].capitalize())
        self.opt_mes.pack(side="left", padx=(0, 8))
        self.opt_ano = ctk.CTkOptionMenu(self, values=[str(a) for a in range(hoje.year - 3, hoje.year + 2)], width=100,
                                         height=40, font=T.fonte(14), fg_color=T.PRIMARIA, button_color=T.PRIMARIA_HOVER)
        self.opt_ano.set(str(hoje.year))
        self.opt_ano.pack(side="left")

    def get(self):
        mes = [m.capitalize() for m in MESES].index(self.opt_mes.get()) + 1
        return montar_competencia(mes, self.opt_ano.get())


class Etapas(ctk.CTkFrame):
    """Indicador de etapas do fluxo: ① Mês e planilha — ② Conferir — ③ Enviar."""

    def __init__(self, master, nomes):
        super().__init__(master, fg_color="transparent")
        self.itens = []
        for i, nome in enumerate(nomes):
            if i:
                ctk.CTkFrame(self, height=2, width=48, fg_color=T.BORDA).pack(side="left", padx=10)
            bolinha = ctk.CTkLabel(self, text=str(i + 1), width=28, height=28, corner_radius=14, font=T.fonte(12, True))
            bolinha.pack(side="left")
            rotulo = ctk.CTkLabel(self, text=nome, font=T.fonte(13))
            rotulo.pack(side="left", padx=(8, 0))
            self.itens.append((bolinha, rotulo))

    def definir(self, atual):
        for i, (bolinha, rotulo) in enumerate(self.itens):
            if i < atual:
                bolinha.configure(text="✓", fg_color=T.SUCESSO, text_color="#FFFFFF")
                rotulo.configure(text_color=T.TEXTO, font=T.fonte(13))
            elif i == atual:
                bolinha.configure(text=str(i + 1), fg_color=T.PRIMARIA, text_color="#FFFFFF")
                rotulo.configure(text_color=T.TEXTO, font=T.fonte(13, True))
            else:
                bolinha.configure(text=str(i + 1), fg_color=T.BORDA, text_color=T.SUAVE)
                rotulo.configure(text_color=T.SUAVE, font=T.fonte(13))


class _Dialogo(ctk.CTkToplevel):
    def _focar(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()  # só funciona depois que a janela está visível
        except tk.TclError:
            pass


class DialogoServidor(_Dialogo):
    CAMPOS = [
        ("nome", "Nome"), ("matricula", "Matrícula"), ("cpf", "CPF"), ("email", "E-mail pessoal"),
        ("carga_horaria", "Carga horária"), ("ua", "UA"), ("cargo", "Cargo"), ("padrao", "Padrão"),
        ("funcao", "Função"), ("exercicio", "Exercício (lotação)"),
    ]

    def __init__(self, app, servidor_id, ao_salvar=None):
        super().__init__(app)
        self.app = app
        self.ao_salvar = ao_salvar
        self.servidor = app.servicos.servidores.obter(servidor_id)
        if not self.servidor:
            self.destroy()
            return
        self.title(f"Editar servidor — {self.servidor.nome}")
        self.geometry("520x660")
        self.resizable(False, True)
        self.transient(app)
        self.configure(fg_color=T.FUNDO)

        corpo = T.cartao(self)
        corpo.pack(fill="both", expand=True, padx=16, pady=16)
        corpo.grid_columnconfigure(1, weight=1)
        self.entradas = {}
        for linha, (chave, rotulo) in enumerate(self.CAMPOS):
            ctk.CTkLabel(corpo, text=rotulo, font=T.fonte(12), text_color=T.SUAVE).grid(row=linha, column=0, padx=(16, 8), pady=5, sticky="w")
            entrada = T.entrada(corpo)
            entrada.insert(0, getattr(self.servidor, chave) or "")
            entrada.grid(row=linha, column=1, padx=(0, 16), pady=5, sticky="ew")
            self.entradas[chave] = entrada
        linha = len(self.CAMPOS)
        ctk.CTkLabel(corpo, text="Acumula cargo?", font=T.fonte(12), text_color=T.SUAVE).grid(row=linha, column=0, padx=(16, 8), pady=6, sticky="w")
        self.seg_acumula = ctk.CTkSegmentedButton(corpo, values=["Sim", "Não"], selected_color=T.PRIMARIA)
        self.seg_acumula.set("Sim" if self.servidor.acumula else "Não")
        self.seg_acumula.grid(row=linha, column=1, padx=(0, 16), pady=6, sticky="w")

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=16, pady=(0, 16))
        T.botao_primario(rodape, "Salvar alterações", self.salvar).pack(side="right")
        T.botao_secundario(rodape, "Cancelar", self.destroy).pack(side="right", padx=8)
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(150, self._focar)

    def salvar(self):
        dados = {k: e.get().strip() for k, e in self.entradas.items()}
        dados["acumula_cargo"] = self.seg_acumula.get()
        servidor = dataclasses.replace(self.servidor, **dados)
        try:
            self.app.servicos.servidores.salvar(servidor)
        except ErroDominio as e:
            messagebox.showwarning("Editar servidor", str(e), parent=self)
            return
        self.destroy()
        self.app.notificar(f"Dados de {servidor.nome} atualizados.")
        if self.ao_salvar:
            self.ao_salvar(servidor)
        self.app.atualizar_pagina()


class DialogoResultado(_Dialogo):
    """Pop-up de conclusão do envio de e-mails."""

    def __init__(self, app, resultado, ao_fechar):
        super().__init__(app)
        self.ao_fechar = ao_fechar
        erros = resultado.erros
        self.title("Envio concluído")
        self.geometry("520x460" if erros else "480x340")
        self.resizable(False, False)
        self.transient(app)
        self.configure(fg_color=T.CARTAO)
        sucesso = not erros
        ctk.CTkLabel(self, text="✓" if sucesso else "!", width=72, height=72, corner_radius=36,
                     fg_color=T.SUCESSO if sucesso else T.AVISO, text_color="#FFFFFF",
                     font=T.fonte(34, True)).pack(pady=(28, 12))
        titulo = "E-mails enviados com sucesso!" if sucesso else "Envio concluído com pendências"
        ctk.CTkLabel(self, text=titulo, font=T.fonte(20, True), text_color=T.TEXTO).pack()
        ctk.CTkLabel(self, text=f"{resultado.enviados} de {resultado.total} e-mail(s) enviado(s), cada um com a sua folha em anexo.",
                     font=T.fonte(13), text_color=T.SUAVE).pack(pady=(6, 0))
        if erros:
            caixa = ctk.CTkTextbox(self, height=120, font=T.fonte(12), fg_color=T.FUNDO, wrap="word")
            caixa.pack(fill="x", padx=28, pady=(14, 0))
            caixa.insert("end", "\n".join(erros))
            caixa.configure(state="disabled")
        ctk.CTkLabel(self, text="O relatório de auditoria desta operação foi salvo.", font=T.fonte(12),
                     text_color=T.SUAVE).pack(pady=(14, 0))
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(pady=(16, 24))
        T.botao_secundario(rodape, "Abrir relatório de auditoria", lambda: abrir_arquivo(resultado.relatorio)).pack(side="left", padx=6)
        T.botao_primario(rodape, "Concluir", self.fechar, width=120).pack(side="left", padx=6)
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.bind("<Return>", lambda e: self.fechar())
        self.after(150, self._focar)

    def fechar(self):
        self.destroy()
        self.ao_fechar()
