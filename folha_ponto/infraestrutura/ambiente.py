"""Relógio e identificação de quem executa (usados nos registros de auditoria)."""
import getpass
import platform
from datetime import datetime


class AmbienteLocal:
    @staticmethod
    def agora():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def usuario():
        return getpass.getuser()

    @staticmethod
    def computador():
        return platform.node()
