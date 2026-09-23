"""Conversão .docx -> .pdf via Microsoft Word (COM) ou, na falta dele, LibreOffice."""
import os
import shutil
import subprocess
from contextlib import ExitStack

from .com_windows import com_inicializado


class ConversorPDF:
    """
    Reaproveita UMA instância do Word para vários arquivos (abrir/fechar o Word a cada folha deixava
    a geração em lote muito lenta). Uso:

        with ConversorPDF() as conv:
            ok = conv.converter(docx, pdf)
    """

    def __init__(self):
        self._word = None
        self._word_indisponivel = False
        self._soffice = shutil.which("soffice") or shutil.which("libreoffice")
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

    def converter(self, docx, pdf):
        docx, pdf = os.path.abspath(docx), os.path.abspath(pdf)
        word = self._obter_word()
        if word is not None:
            try:
                doc = word.Documents.Open(docx, ReadOnly=True)
                try:
                    doc.SaveAs(pdf, FileFormat=17)  # 17 = wdFormatPDF
                finally:
                    doc.Close(False)
                if os.path.exists(pdf):
                    return True
            except Exception:
                pass
        if self._soffice:
            try:
                res = subprocess.run([self._soffice, "--headless", "--convert-to", "pdf", docx, "--outdir", os.path.dirname(pdf)],
                                     capture_output=True, text=True, timeout=120,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if res.returncode == 0 and os.path.exists(pdf):
                    return True
            except Exception:
                pass
        return False
