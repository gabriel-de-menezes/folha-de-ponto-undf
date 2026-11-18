"""Conversão .docx -> .pdf via Microsoft Word (COM) ou, na falta dele, LibreOffice.

O instalador leva um LibreOffice portátil (pasta "LibreOffice" ao lado do .exe), então o PDF é gerado mesmo
em um computador sem Office. O Word, quando existe, continua tendo prioridade (é o editor do modelo)."""
import os
import shutil
import subprocess
import tempfile
from contextlib import ExitStack
from pathlib import Path

from .com_windows import com_inicializado

# Folhas por processo do LibreOffice: abrir um processo por folha é lento, e um lote muito grande deixa a
# barra de progresso parada por muito tempo.
LOTE_LIBREOFFICE = 20


def achar_libreoffice():
    """soffice do LibreOffice que acompanha o sistema; senão, um instalado no computador."""
    from .armazenamento import pasta_padrao_app
    candidatos = [os.path.join(pasta_padrao_app(), "LibreOffice", "program", "soffice.exe")]
    for variavel in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variavel)
        if base:
            candidatos.append(os.path.join(base, "LibreOffice", "program", "soffice.exe"))
    for candidato in candidatos:
        if os.path.isfile(candidato):
            return candidato
    return shutil.which("soffice") or shutil.which("libreoffice")


class ConversorPDF:
    """
    Reaproveita UMA instância do Word para vários arquivos (abrir/fechar o Word a cada folha deixava
    a geração em lote muito lenta). Uso:

        with ConversorPDF() as conv:
            ok = conv.converter(docx, pdf)
            oks = conv.converter_lote([(docx1, pdf1), (docx2, pdf2)])
    """

    def __init__(self, usar_word=True):
        self._word = None
        self._word_indisponivel = not usar_word
        self._soffice = achar_libreoffice()
        self._perfil = None
        self._pilha = ExitStack()

    def __enter__(self):
        self._pilha.enter_context(com_inicializado())
        return self

    def __exit__(self, *exc):
        if self._word is not None:
            try:
                self._word.Quit()
            except Exception:
                pass
            self._word = None
        self._pilha.close()

    @property
    def disponivel(self):
        return self._soffice is not None or self._obter_word() is not None

    def _obter_word(self):
        if self._word is None and not self._word_indisponivel:
            try:
                import win32com.client
                self._word = win32com.client.DispatchEx("Word.Application")  # instância própria, não a do usuário
                self._word.Visible = False
                self._word.DisplayAlerts = 0
            except Exception:
                self._word_indisponivel = True
        return self._word

    def _pelo_word(self, docx, pdf):
        word = self._obter_word()
        if word is None:
            return False
        try:
            doc = word.Documents.Open(docx, ReadOnly=True)
            try:
                doc.SaveAs(pdf, FileFormat=17)  # 17 = wdFormatPDF
            finally:
                doc.Close(False)
            return os.path.exists(pdf)
        except Exception:
            return False

    def _perfil_libreoffice(self):
        """Perfil próprio e descartável: funciona num computador onde o LibreOffice nunca foi aberto e não
        se junta a um LibreOffice que o usuário esteja usando."""
        if self._perfil is None:
            self._perfil = self._pilha.enter_context(tempfile.TemporaryDirectory(prefix="digep_lo_", ignore_cleanup_errors=True))
        return Path(self._perfil).as_uri()

    def _pelo_libreoffice(self, pares):
        """Converte um grupo de arquivos num único processo. pares = [(docx, pdf)] já absolutos."""
        por_pasta = {}
        for docx, pdf in pares:
            por_pasta.setdefault(os.path.dirname(pdf), []).append((docx, pdf))
        for pasta, grupo in por_pasta.items():
            comando = [self._soffice, f"-env:UserInstallation={self._perfil_libreoffice()}", "--headless",
                       "--norestore", "--nologo", "--nodefault", "--nolockcheck",
                       "--convert-to", "pdf:writer_pdf_Export", "--outdir", pasta, *[d for d, _ in grupo]]
            try:
                subprocess.run(comando, capture_output=True, text=True, timeout=120 + 30 * len(grupo),
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                continue
            for docx, pdf in grupo:  # o LibreOffice grava <pasta>/<nome do docx>.pdf
                gerado = os.path.join(pasta, os.path.splitext(os.path.basename(docx))[0] + ".pdf")
                if gerado != pdf and os.path.exists(gerado):
                    os.replace(gerado, pdf)

    def converter_lote(self, pares, progresso=None):
        """pares = [(docx, pdf)]. Devolve [bool] na mesma ordem. progresso(feitos, total) ao longo do lote."""
        pares = [(os.path.abspath(d), os.path.abspath(p)) for d, p in pares]
        for _, pdf in pares:  # um PDF antigo não pode passar por convertido
            try:
                os.remove(pdf)
            except OSError:
                pass
        total, feitos = len(pares), 0
        ok = [False] * total
        pendentes = []
        for i, (docx, pdf) in enumerate(pares):
            if self._pelo_word(docx, pdf):
                ok[i] = True
                feitos += 1
                if progresso:
                    progresso(feitos, total)
            else:
                pendentes.append(i)
        if self._soffice:
            for inicio in range(0, len(pendentes), LOTE_LIBREOFFICE):
                grupo = pendentes[inicio:inicio + LOTE_LIBREOFFICE]
                self._pelo_libreoffice([pares[i] for i in grupo])
                for i in grupo:
                    ok[i] = os.path.exists(pares[i][1])
                feitos += len(grupo)
                if progresso:
                    progresso(feitos, total)
        return ok

    def converter(self, docx, pdf):
        return self.converter_lote([(docx, pdf)])[0]
