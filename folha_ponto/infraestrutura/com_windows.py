"""Inicialização do COM do Windows (Word/Outlook), necessária em cada thread que o utiliza."""
from contextlib import contextmanager


@contextmanager
def com_inicializado():
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pythoncom = None
    try:
        yield
    finally:
        if pythoncom is not None:
            pythoncom.CoUninitialize()
