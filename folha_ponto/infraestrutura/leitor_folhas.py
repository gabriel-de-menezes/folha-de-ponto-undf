"""Extração de texto das folhas: camada de texto do PDF (PyMuPDF) e OCR (Tesseract)."""
import os
import shutil

import pymupdf
import pytesseract
from PIL import Image, ImageOps


def _configurar_tesseract():
    """Encontra o tesseract.exe mesmo que não esteja no PATH (instalação padrão no Windows)."""
    if shutil.which("tesseract"):
        return
    for pasta in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                  os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        exe = os.path.join(pasta, "Tesseract-OCR", "tesseract.exe")
        if os.path.exists(exe):
            pytesseract.pytesseract.tesseract_cmd = exe
            return


class LeitorFolhasTesseract:
    def __init__(self, max_paginas=3, dpi=300):
        _configurar_tesseract()
        self.max_paginas = max_paginas
        self.dpi = dpi  # 72 dpi (padrão do PyMuPDF) é baixo demais para OCR

    @staticmethod
    def texto_direto(caminho):
        """Texto já existente no PDF. Rápido; vazio em imagens e PDFs escaneados."""
        if not caminho.lower().endswith(".pdf"):
            return ""
        try:
            with pymupdf.open(caminho) as doc:
                return "".join(page.get_text() for page in doc)
        except Exception:
            return ""

    def texto_ocr(self, caminho):
        if caminho.lower().endswith(".pdf"):
            with pymupdf.open(caminho) as doc:
                texto = ""
                for page in list(doc)[:self.max_paginas]:
                    pix = page.get_pixmap(dpi=self.dpi)
                    texto += self._ocr(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
                return texto
        # exif_transpose: fotos de celular vêm "deitadas", com a rotação só nos metadados
        return self._ocr(ImageOps.exif_transpose(Image.open(caminho)).convert("RGB"))

    @staticmethod
    def _ocr(imagem):
        """Português quando o idioma estiver instalado; senão, inglês (padrão do instalador)."""
        try:
            idiomas = set(pytesseract.get_languages(config=""))
        except Exception:
            idiomas = set()
        lang = "+".join(l for l in ("por", "eng") if l in idiomas) or "eng"
        return pytesseract.image_to_string(imagem, lang=lang)

    @staticmethod
    def ocr_disponivel():
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
