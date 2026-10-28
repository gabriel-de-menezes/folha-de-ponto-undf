"""Extração de texto das folhas: camada de texto do PDF (PyMuPDF) e OCR (Tesseract)."""
import hashlib
import os
import shutil

import pymupdf
import pytesseract
from PIL import Image, ImageFilter, ImageOps, ImageStat


def _tessdata_do_registro():
    """TESSDATA_PREFIX gravado no Windows. Um programa aberto antes de o Tesseract ser instalado (VS Code, terminal)
    não herda a variável, e sem ela o Tesseract não acha os idiomas."""
    try:
        import winreg
    except ImportError:
        return ""
    for raiz, chave in ((winreg.HKEY_CURRENT_USER, r"Environment"),
                        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
        try:
            with winreg.OpenKey(raiz, chave) as k:
                valor = os.path.expandvars(winreg.QueryValueEx(k, "TESSDATA_PREFIX")[0])
            if os.path.isdir(valor):
                return valor
        except OSError:
            pass
    return ""


def _configurar_tesseract():
    """Encontra o tesseract.exe mesmo que não esteja no PATH (instalação padrão no Windows)."""
    if not os.environ.get("TESSDATA_PREFIX"):
        tessdata = _tessdata_do_registro()
        if tessdata:
            os.environ["TESSDATA_PREFIX"] = tessdata
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


def _binarizar(imagem):
    return ImageOps.grayscale(imagem).point(lambda v: 255 if v > 170 else 0)


def inclinacao(imagem, limite=20):
    """Ângulo (graus, anti-horário) que deixa as linhas da folha na horizontal: com as linhas retas, a soma
    das bordas de cada faixa horizontal da imagem varia mais (linhas de texto x espaços em branco)."""
    bordas = ImageOps.grayscale(imagem).filter(ImageFilter.FIND_EDGES)
    bordas.thumbnail((800, 800))

    def contraste(angulo):
        perfil = bordas.rotate(angulo, resample=Image.BILINEAR).resize((1, bordas.height), Image.BOX)
        return ImageStat.Stat(perfil).var[0]

    grosso = max(range(-limite, limite + 1), key=contraste)
    return max((grosso + d / 4 for d in range(-4, 5)), key=contraste)


def endireitar(imagem):
    """Desfaz o giro de uma foto: 90/180/270° (detecção de orientação do Tesseract) e inclinação de até 20°.
    Devolve a própria imagem quando ela já está reta."""
    try:
        giro = pytesseract.image_to_osd(imagem, output_type=pytesseract.Output.DICT)["rotate"]
    except Exception:  # sem osd.traineddata ou pouco texto para decidir
        giro = 0
    if giro:
        imagem = imagem.rotate(-giro, expand=True, fillcolor="white")
    angulo = inclinacao(imagem)
    if abs(angulo) >= 0.5:
        imagem = imagem.rotate(angulo, expand=True, resample=Image.BICUBIC, fillcolor="white")
    return imagem


class LeitorFolhasTesseract:
    """Lê PDFs página a página: cada página é uma folha de ponto."""

    # (dpi, binarizar), da mais à menos provável de funcionar. Em digitalizações o Tesseract às vezes não lê nada
    # (ou pula o cabeçalho) numa resolução e lê tudo em outra. 72 dpi (padrão do PyMuPDF) é baixo demais para OCR.
    VARIACOES_OCR = ((200, False), (300, True), (300, False))

    def __init__(self):
        _configurar_tesseract()

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

    def leituras_ocr(self, caminho, pagina):
        """Uma leitura OCR por variação de imagem (VARIACOES_OCR); quem chama para quando já tiver o que precisa.
        Por último, a página endireitada: foto de celular deitada, de cabeça para baixo ou torta."""
        with pymupdf.open(caminho) as doc:
            for dpi, binarizar in self.VARIACOES_OCR:
                pix = doc[pagina - 1].get_pixmap(dpi=dpi)
                imagem = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                yield self._ocr(_binarizar(imagem) if binarizar else imagem)
        endireitada = endireitar(imagem)
        if endireitada is not imagem:
            yield self._ocr(endireitada)
            yield self._ocr(_binarizar(endireitada))

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
        """Tesseract instalado e com algum idioma: sem os idiomas ele roda, mas toda leitura falha."""
        try:
            return bool(pytesseract.get_languages(config=""))
        except Exception:
            return False
