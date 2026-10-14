"""Casos de uso do calendário acadêmico: carga por planilha, edição manual e datas de um mês."""
from dataclasses import dataclass, field

from ..dominio.competencia import separar_competencia
from ..dominio.regras import ErroDominio, PlanilhaInvalida


@dataclass
class ResumoCalendario:
    novos: int = 0
    atualizados: int = 0
    sem_alteracao: int = 0
    ignoradas: list = field(default_factory=list)
    registros: list = field(default_factory=list)   # [(date, especificação)] a gravar (novos + atualizados)

    @property
    def mensagem(self):
        msg = f"{self.novos} novo(s), {self.atualizados} atualizado(s)"
        if self.sem_alteracao:
            msg += f", {self.sem_alteracao} sem alteração"
        return msg + f", {len(self.ignoradas)} ignorado(s)."


class ServicoCalendario:
    def __init__(self, repositorio, leitor):
        self.repositorio = repositorio
        self.leitor = leitor

    def listar(self, ano=None):
        return self.repositorio.listar(ano)

    def anos(self):
        return self.repositorio.anos()

    def salvar(self, data, especificacao):
        """Inclui ou altera a data especial (uma especificação por data)."""
        especificacao = " ".join((especificacao or "").split())
        if not data:
            raise ErroDominio("Informe uma data válida (DD/MM/AAAA).")
        if not especificacao:
            raise ErroDominio("Informe a especificação (ex.: Feriado Nacional, Recesso Acadêmico).")
        self.repositorio.salvar(data, especificacao)

    def remover(self, data):
        self.repositorio.remover(data)

    def analisar_planilha(self, caminho):
        registros, ignoradas = self.leitor.ler(caminho)
        if not registros:
            raise PlanilhaInvalida("Nenhuma data válida encontrada na planilha.")
        resumo = ResumoCalendario(ignoradas=list(ignoradas))
        for data, esp in registros:
            atual = self.repositorio.obter(data)
            if atual is None:
                resumo.novos += 1
            elif atual.especificacao == esp:
                resumo.sem_alteracao += 1
                continue
            else:
                resumo.atualizados += 1
            resumo.registros.append((data, esp))
        return resumo

    def confirmar_importacao(self, resumo):
        for data, esp in resumo.registros:
            self.repositorio.salvar(data, esp)
        return resumo

    def importar_planilha(self, caminho):
        return self.confirmar_importacao(self.analisar_planilha(caminho))

    def do_mes(self, competencia):
        """{dia: especificação} das datas especiais do mês."""
        mes, ano = separar_competencia(competencia)
        if not mes:
            return {}
        return {d.data.day: d.especificacao for d in self.repositorio.listar(ano) if d.data.month == mes}
