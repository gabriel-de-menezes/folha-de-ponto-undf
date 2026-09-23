"""Pastas e arquivos do sistema (ao lado do executável ou na raiz do projeto)."""
import hashlib
import os
import shutil
import sys

MODELO_FOLHA = "Modelo de folha de ponto - Exemplo.docx"
MODELO_PLANILHA = "Planilha de professores - exemplo.xlsx"


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

    def arquivar_digitalizada(self, origem, competencia):
        """Copia o arquivo para a pasta de arquivo do sistema (sem sobrescrever) e devolve o novo caminho,
        para a folha continuar acessível mesmo que o original seja movido ou apagado."""
        pasta = os.path.join(self.pasta_digitalizadas_raiz, self._pasta_mes(competencia))
        os.makedirs(pasta, exist_ok=True)
        base, ext = os.path.splitext(os.path.basename(origem))
        destino, n = os.path.join(pasta, base + ext), 1
        while os.path.exists(destino):
            destino = os.path.join(pasta, f"{base} ({n}){ext}")
            n += 1
        shutil.copy2(origem, destino)
        return destino

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
