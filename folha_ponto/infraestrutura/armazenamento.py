"""Pastas e arquivos do sistema (ao lado do executável ou na raiz do projeto)."""
import hashlib
import os
import shutil
import sys
from datetime import datetime

from ..dominio.regras import nome_arquivo_folha, pasta_folhas_mes

MODELO_FOLHA = os.path.join("recursos", "Modelo de folha de ponto - Exemplo.docx")
MODELO_PLANILHA = os.path.join("recursos", "Planilha de professores - exemplo.xlsx")


def pasta_padrao_app():
    """Pasta do .exe (PyInstaller) ou a raiz do projeto — os dados ficam sempre ao lado do app,
    independentemente da pasta de onde ele foi iniciado."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ArmazenamentoLocal:
    def __init__(self, pasta_app=None):
        self.pasta_app = pasta_app or pasta_padrao_app()
        self.pasta_dados = os.path.join(self.pasta_app, "dados")
        self.pasta_relatorios = os.path.join(self.pasta_app, "Relatorios_Auditoria")
        self.pasta_geradas_raiz = os.path.join(self.pasta_app, "Folhas_Geradas")
        self.pasta_digitalizadas_raiz = os.path.join(self.pasta_app, "Folhas_Digitalizadas")
        self.banco = os.path.join(self.pasta_app, "folha_ponto.db")
        self.planilha_base = os.path.join(self.pasta_dados, "planilha_base.xlsx")
        self.modelo_folha = self.recurso(MODELO_FOLHA)
        self.modelo_planilha = self.recurso(MODELO_PLANILHA)

    def recurso(self, nome):
        """Arquivos embutidos no .exe ficam em sys._MEIPASS; senão, na pasta do app."""
        local = os.path.join(self.pasta_app, nome)
        if os.path.exists(local):
            return local
        return os.path.join(getattr(sys, "_MEIPASS", self.pasta_app), nome)

    @staticmethod
    def _pasta_mes(competencia):
        return (competencia or "SEM_COMPETENCIA").replace("/", "_")

    def pasta_geradas(self, competencia):
        pasta = os.path.join(self.pasta_geradas_raiz, self._pasta_mes(competencia))
        os.makedirs(pasta, exist_ok=True)
        return pasta

    def pasta_importacao(self):
        """Área de espera: páginas já separadas, ainda não conferidas."""
        pasta = os.path.join(self.pasta_dados, "importacao")
        os.makedirs(pasta, exist_ok=True)
        return pasta

    def caminho_folha_arquivada(self, nome_servidor, competencia):
        """Folhas_Digitalizadas/Folhas_AAAA-MM/Nome_do_Servidor-AAAA-MM.pdf"""
        return os.path.join(self.pasta_digitalizadas_raiz, pasta_folhas_mes(competencia),
                            nome_arquivo_folha(nome_servidor, competencia))

    def arquivar_folha(self, origem, nome_servidor, competencia, momento=None):
        """Grava a folha no destino padrão. Se já existir uma do mesmo servidor/mês, ela é renomeada para
        `..._OLD_AAAAMMDD-HHMMSS.pdf` antes. Retorna (destino, backup ou None)."""
        destino = self.caminho_folha_arquivada(nome_servidor, competencia)
        if os.path.abspath(origem) == os.path.abspath(destino):
            return destino, None
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        backup = None
        if os.path.exists(destino):
            carimbo = (momento or datetime.now()).strftime("%Y%m%d-%H%M%S")
            base = destino[:-len(".pdf")] + f"_OLD_{carimbo}"
            backup, n = base + ".pdf", 1
            while os.path.exists(backup):  # duas substituições no mesmo segundo
                backup, n = f"{base}_{n}.pdf", n + 1
            os.replace(destino, backup)
        shutil.copy2(origem, destino)
        return destino, backup

    def guardar_planilha_base(self, origem):
        os.makedirs(self.pasta_dados, exist_ok=True)
        if os.path.abspath(origem) != os.path.abspath(self.planilha_base):
            shutil.copyfile(origem, self.planilha_base)

    @staticmethod
    def hash(caminho):
        """SHA-256 do conteúdo (identifica o arquivo de forma única no relatório de auditoria)."""
        if not caminho or not os.path.exists(caminho):
            return ""
        h = hashlib.sha256()
        with open(caminho, "rb") as f:
            for bloco in iter(lambda: f.read(1 << 20), b""):
                h.update(bloco)
        return h.hexdigest()

    @staticmethod
    def existe(caminho):
        return bool(caminho) and os.path.exists(caminho)
