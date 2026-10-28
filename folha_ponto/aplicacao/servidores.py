"""Casos de uso de servidores: listagem, edição, importação de planilha e planilha base."""
import os
from dataclasses import dataclass, field

from ..dominio.entidades import InfoPlanilhaBase
from ..dominio.regras import PlanilhaInvalida


@dataclass
class ResumoImportacao:
    """Prévia da importação de uma planilha: o que seria feito, antes de gravar."""
    registros: list = field(default_factory=list)      # dicts a gravar (novos + atualizados)
    todos: list = field(default_factory=list)          # todos os registros válidos da planilha
    novos: int = 0
    atualizados: int = 0
    sem_alteracao: int = 0
    ignoradas: list = field(default_factory=list)

    @property
    def total_ignorados(self):
        return len(self.ignoradas) + self.sem_alteracao

    @property
    def mensagem(self):
        msg = f"{self.novos} novo(s) cadastrado(s), {self.atualizados} atualizado(s)"
        if self.sem_alteracao:
            msg += f", {self.sem_alteracao} sem alteração"
        msg += f", {len(self.ignoradas)} ignorado(s)"
        if self.ignoradas:
            msg += " (" + "; ".join(self.ignoradas[:5]) + ("…" if len(self.ignoradas) > 5 else "") + ")"
        return msg + "."


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

    def remover(self, servidor_id):
        """Remove o servidor das listas. Folhas e envios já registrados continuam consultáveis."""
        if not self.repositorio.obter(servidor_id):
            raise PlanilhaInvalida("Servidor não encontrado.")
        self.repositorio.remover(servidor_id)

    def remover_todos(self):
        """Remove todos os servidores das listas (ex.: antes de importar uma planilha base nova).
        Folhas e envios já registrados continuam consultáveis. Devolve quantos foram removidos."""
        return self.repositorio.remover_todos()

    def analisar_planilha(self, caminho):
        """Lê e valida a planilha (extensão, colunas, linhas) e conta o que mudaria, sem gravar nada.
        Levanta PlanilhaInvalida."""
        registros, ignoradas = self.leitor.ler(caminho)
        if not registros:
            raise PlanilhaInvalida("Nenhum servidor encontrado na planilha (cada linha precisa ter nome e matrícula).")
        existentes = {s.matricula: s for s in self.repositorio.listar()}
        resumo = ResumoImportacao(ignoradas=list(ignoradas))
        for dados in registros:
            atual = existentes.get(dados["matricula"])
            if atual is None:
                resumo.novos += 1
            elif all(str(getattr(atual, c) or "") == str(v or "") for c, v in dados.items()):
                resumo.sem_alteracao += 1
                continue
            else:
                resumo.atualizados += 1
            resumo.registros.append(dados)
        resumo.todos = registros
        return resumo

    def confirmar_importacao(self, resumo):
        """Grava o que a análise prévia apontou como novo ou atualizado."""
        resultado = ResultadoImportacao(ignoradas=resumo.ignoradas)
        for dados in resumo.todos:
            servidor_id, novo = self.repositorio.importar(dados)
            if servidor_id not in resultado.ids:
                resultado.ids.append(servidor_id)
            if novo:
                resultado.novos += 1
            elif dados in resumo.registros:
                resultado.atualizados += 1
        return resultado

    def importar_planilha(self, caminho):
        """Analisa e grava de uma vez (cadastra/atualiza pela matrícula). Levanta PlanilhaInvalida."""
        return self.confirmar_importacao(self.analisar_planilha(caminho))

    # ---------- planilha base ----------
    def definir_planilha_base(self, caminho, resumo=None):
        """Importa (usando a análise já confirmada pelo usuário, se houver) e guarda como planilha base."""
        resultado = self.confirmar_importacao(resumo) if resumo else self.importar_planilha(caminho)
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
