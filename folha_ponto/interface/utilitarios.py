"""Ações de sistema usadas pelas telas (abrir arquivo, salvar cópia, miniaturas)."""
import os
import shutil
import subprocess
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pymupdf
from PIL import Image, ImageOps

TIPOS_FOLHA_ASSINADA = [("PDF ou imagens", "*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp"), ("PDF", "*.pdf"),
                        ("Imagens", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp")]
TIPOS_PLANILHA = [("Planilhas Excel", "*.xlsx *.xlsm")]


def abrir_arquivo(caminho):
    if not caminho or not os.path.exists(caminho):
        messagebox.showwarning("Arquivo não encontrado", "O arquivo não foi localizado no disco.")
        return
    try:
        os.startfile(caminho)
    except Exception as e:
        messagebox.showerror("Erro ao abrir", f"Não foi possível abrir o arquivo:\n{e}")


def abrir_pasta(pasta):
    os.makedirs(pasta, exist_ok=True)
    os.startfile(pasta)


def mostrar_na_pasta(caminho):
    if caminho and os.path.exists(caminho):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(caminho)])


def salvar_copia(caminho, titulo="Salvar cópia"):
    if not caminho or not os.path.exists(caminho):
        messagebox.showwarning("Arquivo não encontrado", "O arquivo não foi localizado no disco.")
        return
    ext = os.path.splitext(caminho)[1]
    destino = filedialog.asksaveasfilename(title=titulo, initialfile=os.path.basename(caminho),
                                           defaultextension=ext, filetypes=[("Arquivo", f"*{ext}")])
    if destino:
        shutil.copyfile(caminho, destino)


def gerar_preview(caminho, max_w=320, max_h=330):
    """Miniatura (CTkImage) da 1ª página de um PDF ou de uma imagem. None se não houver preview."""
    if not caminho or not os.path.exists(caminho):
        return None
    ext = os.path.splitext(caminho)[1].lower()
    try:
        if ext == ".pdf":
            with pymupdf.open(caminho) as doc:
                pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        elif ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
            img = ImageOps.exif_transpose(Image.open(caminho)).convert("RGB")  # fotos de celular giradas
        else:
            return None
        img.thumbnail((max_w, max_h))
        return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None
