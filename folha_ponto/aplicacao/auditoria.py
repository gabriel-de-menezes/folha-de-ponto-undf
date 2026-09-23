"""Caso de uso de auditoria: registro das operações e relatório em PDF."""
import os

from ..dominio.competencia import rotulo_competencia
from ..dominio.entidades import Operacao, TipoOperacao, codigo_operacao


class ServicoAuditoria:
    def __init__(self, repositorio, gerador_relatorio, armazenamento, ambiente):
        self.repositorio = repositorio
        self.gerador = gerador_relatorio
        self.armazenamento = armazenamento
        self.ambiente = ambiente

    def iniciar(self, tipo, competencia, origem="", origem_hash=""):
        op = Operacao(id=0, tipo=tipo, competencia=competencia, iniciado_em=self.ambiente.agora(),
                      usuario=self.ambiente.usuario(), computador=self.ambiente.computador(),
                      origem=origem, origem_hash=origem_hash)
        op_id = self.repositorio.criar(op)
        self.evento(op_id, f"Operação iniciada: {TipoOperacao.descrever(tipo)} — {rotulo_competencia(competencia)}.")
        return op_id

    def evento(self, op_id, descricao):
        if op_id:
            self.repositorio.registrar_evento(op_id, self.ambiente.agora(), descricao)

    def atualizar(self, op_id, **campos):
        self.repositorio.atualizar(op_id, **campos)

    def salvar_itens(self, op_id, itens):
        self.repositorio.salvar_itens(op_id, itens)

    def finalizar(self, op_id, status, itens=None):
        """Conclui a operação e (re)gera o relatório. Retorna o caminho do PDF."""
        if itens is not None:
            self.salvar_itens(op_id, itens)
        self.repositorio.atualizar(op_id, status=status, concluido_em=self.ambiente.agora())
        self.evento(op_id, f"Operação finalizada: {status}.")
        return self.gerar_relatorio(op_id)

    def gerar_relatorio(self, op_id):
        op = self.repositorio.obter(op_id)
        nome = f"{codigo_operacao(op_id)}_{op.tipo}_{op.competencia.replace('/', '_')}.pdf"
        destino = os.path.join(self.armazenamento.pasta_relatorios, nome)
        caminho = self.gerador.gerar(op, self.repositorio.itens(op_id), self.repositorio.eventos(op_id),
                                     self.ambiente.agora(), destino)
        self.repositorio.atualizar(op_id, relatorio=caminho)
        return caminho

    def relatorio(self, op_id, regerar=False):
        """Caminho do relatório da operação, gerando-o se ainda não existir."""
        op = self.repositorio.obter(op_id)
        if regerar or not op.relatorio or not self.armazenamento.existe(op.relatorio):
            return self.gerar_relatorio(op_id)
        return op.relatorio

    def listar(self):
        return self.repositorio.listar()
