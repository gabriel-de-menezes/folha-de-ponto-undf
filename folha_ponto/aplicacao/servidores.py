"""Casos de uso de servidores: listagem, edição, importação de planilha e planilha base."""
import os
from dataclasses import dataclass, field

from ..dominio.entidades import InfoPlanilhaBase
from ..dominio.regras import PlanilhaInvalida


@dataclass
class ResultadoImportacao:
    ids: list = field(default_factory=list)   # ids dos servidores da planilha, na ordem da planilha
    novos: int = 0
    atualizados: int = 0
    ignoradas: list = field(default_factory=list)

    @property
    def mensagem(self):
        msg = f"{self.novos} servidor(es) novo(s) e {self.atualizados} atualizado(s)."
        if self.ignoradas:
            msg += f" Ignoradas: {', '.join(self.ignoradas[:5])}" + ("…" if len(self.ignoradas) > 5 else "") + "."
        return msg


class ServicoServidores:
    def __init__(self, repositorio, leitor_planilha, armazenamento, configuracoes, ambiente):
        self.repositorio = repositorio
        self.leitor = leitor_planilha
        self.armazenamento = armazenamento
        self.configuracoes = configuracoes
        self.ambiente = ambiente

    def listar(self, busca=""):
        return self.repositorio.listar(busca)

    def obter(self, servidor_id):
        return self.repositorio.obter(servidor_id)

    def contar(self):
        return self.repositorio.contar()

    def salvar(self, servidor):
        """Levanta MatriculaDuplicada se a matrícula já for de outro servidor."""
        if not servidor.nome.strip() or not servidor.matricula.strip():
            raise PlanilhaInvalida("Nome e matrícula são obrigatórios.")
        self.repositorio.salvar(servidor)

    def importar_planilha(self, caminho):
        """Cadastra/atualiza (pela matrícula) os servidores da planilha. Levanta PlanilhaInvalida."""
        registros, ignoradas = self.leitor.ler(caminho)
        if not registros:
            raise PlanilhaInvalida("Nenhum servidor encontrado na planilha (cada linha precisa ter nome e matrícula).")
        resultado = ResultadoImportacao(ignoradas=ignoradas)
        for dados in registros:
            servidor_id, novo = self.repositorio.importar(dados)
            if servidor_id not in resultado.ids:
                resultado.ids.append(servidor_id)
            if novo:
                resultado.novos += 1
            else:
                resultado.atualizados += 1
        return resultado

    # ---------- planilha base ----------
    def definir_planilha_base(self, caminho):
        resultado = self.importar_planilha(caminho)
        self.guardar_como_base(caminho)
        return resultado

    def guardar_como_base(self, caminho):
        self.armazenamento.guardar_planilha_base(caminho)
        self.configuracoes.definir("planilha_base_nome", os.path.basename(caminho))
        self.configuracoes.definir("planilha_base_data", self.ambiente.agora())

    def planilha_base(self):
        caminho = self.armazenamento.planilha_base
        if not self.armazenamento.existe(caminho):
            return None
        return InfoPlanilhaBase(
            caminho=caminho,
            nome=self.configuracoes.obter("planilha_base_nome", os.path.basename(caminho)),
            definida_em=self.configuracoes.obter("planilha_base_data", ""),
            quantidade=self.leitor.contar(caminho),
        )
