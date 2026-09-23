"""Caso de uso: enviar a cada servidor selecionado a sua folha por e-mail e encerrar a operação."""
from dataclasses import dataclass, field

from ..dominio.entidades import StatusEnvio
from ..dominio.regras import ErroDominio, montar_email
from .portas import sem_progresso


@dataclass
class ResultadoEnvio:
    enviados: int
    total: int
    erros: list = field(default_factory=list)
    relatorio: str = ""


class EnviarFolhas:
    def __init__(self, servico_email, repositorio_envios, configuracoes, auditoria, ambiente):
        self.email = servico_email
        self.envios = repositorio_envios
        self.configuracoes = configuracoes
        self.auditoria = auditoria
        self.ambiente = ambiente

    def executar(self, op_id, competencia, tipo, selecionados, itens_auditoria, progresso=sem_progresso):
        """
        Envia a folha de cada item selecionado ao e-mail do servidor, registra cada tentativa,
        finaliza a operação e gera o relatório de auditoria.
        """
        config = self.configuracoes.email()
        if not config.configurado:
            raise ErroDominio("O envio de e-mail ainda não foi configurado.")
        for item in itens_auditoria:
            item.selecionado = any(item is s for s in selecionados)
        self.auditoria.atualizar(op_id, metodo_envio=config.descricao())
        self.auditoria.evento(op_id, f"Envio confirmado para {len(selecionados)} servidor(es) via {config.descricao()}.")

        erros = []
        with self.email.abrir(config) as enviador:
            for n, item in enumerate(selecionados):
                progresso(n, len(selecionados), f"Enviando para {item.nome}")
                ok, msg = self._enviar(enviador, item, competencia, tipo, op_id)
                if not ok:
                    erros.append(f"{item.nome}: {msg}")

        enviados = len(selecionados) - len(erros)
        self.auditoria.evento(op_id, f"E-mails enviados: {enviados} de {len(selecionados)}"
                              + (f"; {len(erros)} com erro." if erros else "."))
        status = "Concluída" if not erros else ("Concluída com erros de envio" if enviados else "Falha no envio")
        relatorio = self.auditoria.finalizar(op_id, status, itens_auditoria)
        return ResultadoEnvio(enviados=enviados, total=len(selecionados), erros=erros, relatorio=relatorio)

    def _enviar(self, enviador, item, competencia, tipo, op_id):
        if not item.tem_email:
            ok, msg, destino = False, "E-mail pessoal não cadastrado.", "(sem e-mail)"
        elif not item.arquivo:
            ok, msg, destino = False, "Arquivo da folha não encontrado.", item.email
        else:
            destino = item.email.strip()
            assunto, corpo = montar_email(item.nome, competencia, tipo)
            ok, msg = enviador.enviar(destino, assunto, corpo, item.arquivo)
        status = StatusEnvio.ENVIADO if ok else StatusEnvio.ERRO
        self.envios.registrar(item.servidor_id, competencia, destino, status, msg, item.arquivo, op_id)
        item.envio_status, item.envio_detalhe, item.enviado_em = status, msg, self.ambiente.agora()
        return ok, msg

    def concluir_sem_envio(self, op_id, itens_auditoria):
        for item in itens_auditoria:
            item.selecionado = False
        return self.auditoria.finalizar(op_id, "Concluída sem envio de e-mails", itens_auditoria)
