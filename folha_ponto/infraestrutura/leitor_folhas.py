"""Extração de texto das folhas: camada de texto do PDF (PyMuPDF) e OCR (Tesseract)."""
import hashlib
import os
import shutil

import pymupdf
import pytesseract
from PIL import Image


def _configurar_tesseract():
    """Encontra o tesseract.exe mesmo que não esteja no PATH (instalação padrão no Windows)."""
    if shutil.which("tesseract"):
        return
    from .armazenamento import pasta_padrao_app
    # 1º: Tesseract portátil ao lado do sistema (pasta de rede), sem instalação no computador
    portatil = os.path.join(pasta_padrao_app(), "Tesseract-OCR", "tesseract.exe")
    if os.path.exists(portatil):
        pytesseract.pytesseract.tesseract_cmd = portatil
        return
    for pasta in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                  os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        exe = os.path.join(pasta, "Tesseract-OCR", "tesseract.exe")
        if os.path.exists(exe):
            pytesseract.pytesseract.tesseract_cmd = exe
            return


class LeitorFolhasTesseract:
    """Lê PDFs página a página: cada página é uma folha de ponto."""

    def __init__(self, dpi=300):
        _configurar_tesseract()
        self.dpi = dpi  # 72 dpi (padrão do PyMuPDF) é baixo demais para OCR

    @staticmethod
    def e_pdf(caminho):
        """Extensão .pdf e cabeçalho %PDF (um JPG renomeado para .pdf não passa)."""
        if not caminho.lower().endswith(".pdf"):
            return False
        try:
            with open(caminho, "rb") as f:
                return b"%PDF" in f.read(1024)
        except OSError:
            return False

    @staticmethod
    def contar_paginas(caminho):
        with pymupdf.open(caminho) as doc:
            return len(doc)

    @staticmethod
    def texto_pagina(caminho, pagina):
        """Texto já existente na página (1..n). Rápido; vazio em PDFs escaneados."""
        try:
            with pymupdf.open(caminho) as doc:
                return doc[pagina - 1].get_text()
        except Exception:
            return ""

    @staticmethod
    def assinatura_pagina(caminho, pagina):
        """SHA-256 do conteúdo da página (desenho + imagens). Estável: a mesma folha tem a mesma assinatura
        mesmo vindo de outro arquivo ou sendo regravada, ao contrário do hash dos bytes do PDF."""
        h = hashlib.sha256()
        with pymupdf.open(caminho) as doc:
            pg = doc[pagina - 1]
            h.update(pg.read_contents())
            h.update(pg.get_text().encode())
            for img in pg.get_images(full=True):
                try:
                    h.update(doc.extract_image(img[0])["image"])
                except Exception:
                    h.update(str(img[0]).encode())
        return h.hexdigest()

    def ocr_pagina(self, caminho, pagina):
        with pymupdf.open(caminho) as doc:
            pix = doc[pagina - 1].get_pixmap(dpi=self.dpi)
            return self._ocr(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

    @staticmethod
    def salvar_pagina(caminho, pagina, destino):
        """Grava só a página indicada como um PDF próprio."""
        with pymupdf.open(caminho) as origem, pymupdf.open() as novo:
            novo.insert_pdf(origem, from_page=pagina - 1, to_page=pagina - 1)
            novo.save(destino)

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
