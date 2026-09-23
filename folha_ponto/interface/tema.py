"""Tokens visuais (cores claro/escuro, fontes) e componentes reutilizáveis da interface."""
import customtkinter as ctk
from tkinter import ttk

# Cada cor é (modo claro, modo escuro)
PRIMARIA = ("#1F4E8C", "#3B7DD8")
PRIMARIA_HOVER = ("#173B6A", "#2F66B3")
SUCESSO = ("#2E9E6B", "#34B37A")
AVISO = ("#D08A1F", "#E0A040")
PERIGO = ("#C0392B", "#E05A4B")
FUNDO = ("#F4F6FA", "#0F172A")
CARTAO = ("#FFFFFF", "#1E293B")
BORDA = ("#E2E8F0", "#334155")
TEXTO = ("#1E293B", "#E2E8F0")
SUAVE = ("#64748B", "#94A3B8")
MENU_FUNDO = ("#16233B", "#0B1220")
MENU_ATIVO = ("#1F4E8C", "#1E3A66")
MENU_HOVER = ("#22324F", "#16233B")

FONTE = "Segoe UI"


def fonte(tamanho=13, negrito=False):
    return ctk.CTkFont(family=FONTE, size=tamanho, weight="bold" if negrito else "normal")


def _cor(par):
    return par[1] if ctk.get_appearance_mode() == "Dark" else par[0]


def aplicar_estilo_tabelas():
    """Estiliza as ttk.Treeview para combinar com o tema atual (claro/escuro).
    Deve ser chamada novamente sempre que o modo de aparência mudar."""
    style = ttk.Style()
    style.theme_use("clam")
    fundo, texto, borda = _cor(CARTAO), _cor(TEXTO), _cor(BORDA)
    cab = "#EEF2F7" if ctk.get_appearance_mode() != "Dark" else "#273449"
    style.configure(
        "Treeview", background=fundo, fieldbackground=fundo, foreground=texto,
        rowheight=32, font=(FONTE, 11), borderwidth=0, relief="flat",
    )
    style.configure(
        "Treeview.Heading", background=cab, foreground=texto, font=(FONTE, 10, "bold"),
        relief="flat", borderwidth=0, padding=(8, 6),
    )
    style.map("Treeview.Heading", background=[("active", cab)])
    style.map(
        "Treeview",
        background=[("selected", _cor(PRIMARIA))],
        foreground=[("selected", "#FFFFFF")],
    )
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Vertical.TScrollbar", background=cab, troughcolor=fundo, bordercolor=borda, arrowcolor=texto)
    return {
        "impar": "#F8FAFC" if ctk.get_appearance_mode() != "Dark" else "#223047",
        "ok": _cor(SUCESSO),
        "erro": _cor(PERIGO),
        "aviso": _cor(AVISO),
        "suave": _cor(SUAVE),
    }


def cartao(master, **kw):
    kw.setdefault("fg_color", CARTAO)
    kw.setdefault("corner_radius", 12)
    kw.setdefault("border_width", 1)
    kw.setdefault("border_color", BORDA)
    return ctk.CTkFrame(master, **kw)


def botao_primario(master, texto, comando, **kw):
    kw.setdefault("height", 40)
    kw.setdefault("font", fonte(13, True))
    return ctk.CTkButton(
        master, text=texto, command=comando, fg_color=PRIMARIA, hover_color=PRIMARIA_HOVER,
        corner_radius=8, **kw,
    )


def botao_secundario(master, texto, comando, **kw):
    kw.setdefault("height", 36)
    kw.setdefault("font", fonte(12))
    return ctk.CTkButton(
        master, text=texto, command=comando, fg_color="transparent", border_width=1,
        border_color=BORDA, text_color=TEXTO, hover_color=BORDA, corner_radius=8, **kw,
    )


def link(master, texto, comando, **kw):
    kw.setdefault("font", fonte(12))
    return ctk.CTkButton(
        master, text=texto, command=comando, fg_color="transparent", hover_color=BORDA,
        text_color=PRIMARIA, width=0, height=28, corner_radius=6, **kw,
    )


CAMPO = ("#FFFFFF", "#0F172A")


def entrada(master, **kw):
    kw.setdefault("height", 36)
    kw.setdefault("font", fonte(13))
    return ctk.CTkEntry(master, fg_color=CAMPO, border_color=BORDA, border_width=1, corner_radius=8,
                        text_color=TEXTO, **kw)


def combo(master, **kw):
    kw.setdefault("height", 36)
    kw.setdefault("font", fonte(13))
    return ctk.CTkComboBox(master, fg_color=CAMPO, border_color=BORDA, button_color=BORDA, border_width=1,
                           corner_radius=8, text_color=TEXTO, **kw)


def titulo_pagina(master, titulo, subtitulo=""):
    frame = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(frame, text=titulo, font=fonte(22, True), text_color=TEXTO).pack(anchor="w")
    frame.subtitulo = ctk.CTkLabel(frame, text=subtitulo, font=fonte(13), text_color=SUAVE, justify="left")
    frame.subtitulo.pack(anchor="w")
    return frame
