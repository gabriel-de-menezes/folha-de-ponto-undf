"""Consultas (somente leitura) usadas pelas telas de Arquivo e Auditoria."""
from ..dominio.competencia import separar_competencia


class Consultas:
    def __init__(self, repositorio_folhas, repositorio_envios):
        self.folhas = repositorio_folhas
        self.envios = repositorio_envios

    def folhas_arquivadas(self, termo="", competencia=""):
        return self.folhas.listar_arquivadas(termo, competencia)

    def competencias(self):
        """Competências com folhas, da mais recente para a mais antiga."""
        def chave(c):
            mes, ano = separar_competencia(c)
            return (ano or 0, mes or 0)
        return sorted(set(self.folhas.competencias()), key=chave, reverse=True)

    def envios_realizados(self):
        return self.envios.listar()
