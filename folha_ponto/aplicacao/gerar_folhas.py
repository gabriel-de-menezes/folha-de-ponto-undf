"""Caso de uso: gerar as folhas de ponto do mês a partir da planilha de servidores."""
import os
from dataclasses import dataclass, field

from ..dominio.competencia import rotulo_competencia
from ..dominio.entidades import ItemOperacao, TipoOperacao
from ..dominio.regras import ErroDominio
from .portas import sem_progresso


@dataclass
class ResultadoGeracao:
    op_id: int
    itens: list = field(default_factory=list)
    erros: list = field(default_factory=list)
    sem_pdf: int = 0


class GerarFolhas:
    def __init__(self, servidores, repositorio_folhas, gerador, armazenamento, auditoria):
        self.servidores = servidores
        self.folhas = repositorio_folhas
        self.gerador = gerador
        self.armazenamento = armazenamento
        self.auditoria = auditoria

    def executar(self, competencia, planilha=None, salvar_como_base=False, progresso=sem_progresso):
        """
        Lê a planilha (ou a planilha base, se planilha=None), cadastra/atualiza os servidores e gera a
        folha de cada um para o mês. Abre a operação de auditoria. Levanta PlanilhaInvalida.
        """
        if planilha is None:
            info = self.servidores.planilha_base()
            if not info:
                raise ErroDominio("Nenhuma planilha base definida. Defina uma em Servidores.")
            planilha, origem = info.caminho, f"Planilha base do sistema ({info.nome})"
        else:
            origem = f"Planilha enviada: {planilha}"
        if not self.armazenamento.existe(self.armazenamento.modelo_folha):
            raise ErroDominio(f"O modelo da folha não foi encontrado: {self.armazenamento.modelo_folha}")

        progresso(0, 0, "Lendo a planilha…")
        importacao = self.servidores.importar_planilha(planilha)
        if salvar_como_base:
            self.servidores.guardar_como_base(planilha)

        op_id = self.auditoria.iniciar(TipoOperacao.GERACAO, competencia, origem, self.armazenamento.hash(planilha))
        self.auditoria.evento(op_id, f"Planilha lida ({os.path.basename(planilha)}): {importacao.mensagem}"
                              + (" Guardada como planilha base." if salvar_como_base else ""))

        servidores = [self.servidores.obter(i) for i in importacao.ids]
        arquivos, erros = self.gerador.gerar_lote(servidores, competencia, progresso)
        resultado = ResultadoGeracao(op_id=op_id, erros=erros)
        for s in servidores:
            if s.id in arquivos:
                docx, pdf = arquivos[s.id]
                self.folhas.registrar_gerada(s.id, competencia, docx, pdf)
                arquivo = pdf or docx
                resultado.sem_pdf += 0 if pdf else 1
                identificacao = "Gerada (PDF)" if pdf else "Gerada (Word)"
            else:
                arquivo, identificacao = None, "Erro na geração"
            resultado.itens.append(ItemOperacao.de_servidor(
                s, arquivo=arquivo, arquivo_hash=self.armazenamento.hash(arquivo), identificacao=identificacao))

        geradas = len(servidores) - len(erros)
        self.auditoria.evento(op_id, f"Folhas geradas a partir do modelo institucional: {geradas} de {len(servidores)}"
                              + (f" ({resultado.sem_pdf} só em Word, sem conversor PDF)" if resultado.sem_pdf else "")
                              + f". Pasta: {self.armazenamento.pasta_geradas(competencia)}")
        for erro in erros:
            self.auditoria.evento(op_id, f"Erro ao gerar folha — {erro}")
        self.auditoria.salvar_itens(op_id, resultado.itens)
        return resultado

    def regerar(self, op_id, competencia, item):
        """Gera de novo a folha de um servidor (ex.: depois de corrigir seus dados na conferência)."""
        servidor = self.servidores.obter(item.servidor_id)
        arquivos, erros = self.gerador.gerar_lote([servidor], competencia, sem_progresso)
        if servidor.id not in arquivos:
            raise ErroDominio(erros[0] if erros else "Não foi possível gerar a folha.")
        docx, pdf = arquivos[servidor.id]
        self.folhas.registrar_gerada(servidor.id, competencia, docx, pdf)
        item.atualizar_servidor(servidor)
        item.arquivo = pdf or docx
        item.arquivo_hash = self.armazenamento.hash(item.arquivo)
        self.auditoria.evento(op_id, f"Dados de {servidor.nome} (matrícula {servidor.matricula}) corrigidos na "
                                     f"conferência; folha de {rotulo_competencia(competencia)} gerada novamente.")
        return item
