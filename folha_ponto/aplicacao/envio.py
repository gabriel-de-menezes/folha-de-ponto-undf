"""Caso de uso: enviar a cada servidor selecionado a sua folha por e-mail e encerrar a operação."""
from dataclasses import dataclass, field

from ..dominio.entidades import ItemOperacao, StatusEnvio, TipoOperacao
from ..dominio.regras import ErroDominio, montar_email
from .portas import sem_progresso


@dataclass
class ResultadoEnvio:
    enviados: int
    total: int
    erros: list = field(default_factory=list)
    relatorio: str = ""


class EnviarFolhas:
    def __init__(self, servico_email, repositorio_envios, configuracoes, auditoria, ambiente, repositorio_servidores=None):
        self.servidores = repositorio_servidores
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
                ok, msg = self._enviar(enviador, item, item.competencia or competencia, tipo, op_id)
                if not ok:
                    erros.append(f"{item.nome}: {msg}")

        enviados = len(selecionados) - len(erros)
        self.auditoria.evento(op_id, f"E-mails enviados: {enviados} de {len(selecionados)}"
                              + (f"; {len(erros)} com erro." if erros else "."))
        status = "Concluída" if not erros else ("Concluída com erros de envio" if enviados else "Falha no envio")
        relatorio = self.auditoria.finalizar(op_id, status, itens_auditoria)
        return ResultadoEnvio(enviados=enviados, total=len(selecionados), erros=erros, relatorio=relatorio)

    # ---------- seleção por grupos ----------
    def situacoes(self, itens, competencia=""):
        """{id(item): "Enviado" | "Erro" | "Pendente"} conforme o histórico de envios do servidor no mês."""
        historico = self.envios.situacao_por_servidor_mes()
        return {id(i): historico.get((i.servidor_id, i.competencia or competencia), StatusEnvio.PENDENTE) for i in itens}

    def selecionar(self, itens, grupo, competencia=""):
        """Itens de um grupo: "todos", "pendentes" (sem envio com sucesso) ou "erros" (último envio falhou)."""
        situacao = self.situacoes(itens, competencia)
        if grupo == "todos":
            return [i for i in itens if i.pode_enviar]
        alvo = {"pendentes": (StatusEnvio.PENDENTE, StatusEnvio.ERRO), "erros": (StatusEnvio.ERRO,)}[grupo]
        return [i for i in itens if i.pode_enviar and situacao[id(i)] in alvo]

    def reenviar_erros(self, registros, progresso=sem_progresso):
        """Reenvia os e-mails do histórico que falharam (e ainda não foram entregues depois). Abre uma operação própria."""
        historico = self.envios.situacao_por_servidor_mes()
        vistos, itens = set(), []
        for r in registros:
            chave = (r.servidor_id, r.competencia)
            if r.status != StatusEnvio.ERRO or historico.get(chave) == StatusEnvio.ENVIADO or chave in vistos:
                continue
            vistos.add(chave)
            atual = self.servidores.obter(r.servidor_id) if self.servidores else None  # e-mail pode ter sido corrigido
            email = atual.email if atual else (r.destinatario if "@" in (r.destinatario or "") else "")
            itens.append(ItemOperacao(servidor_id=r.servidor_id, nome=r.nome, matricula=r.matricula, cpf=r.cpf,
                                      email=email, competencia=r.competencia, arquivo=r.anexo, identificacao="Reenvio",
                                      observacao=f"Erro anterior: {r.detalhes}"[:200]))
        if not itens:
            raise ErroDominio("Não há envios com erro para reenviar.")
        op_id = self.auditoria.iniciar(TipoOperacao.REENVIO, itens[0].competencia if len({i.competencia for i in itens}) == 1
                                       else "VÁRIOS MESES", f"{len(itens)} envio(s) com erro")
        self.auditoria.salvar_itens(op_id, itens)
        resultado = self.executar(op_id, "", TipoOperacao.REENVIO, itens, itens, progresso)
        return op_id, resultado

    def _enviar(self, enviador, item, competencia, tipo, op_id):
        if not item.tem_email:
            ok, msg, destino = False, "E-mail pessoal não cadastrado.", "(sem e-mail)"
        elif not item.arquivo:
            ok, msg, destino = False, "Arquivo da folha não encontrado.", item.email
        else:
            destino = item.email.strip()
            if tipo == TipoOperacao.REENVIO:  # o texto depende de a folha ser assinada ou gerada
                tipo = TipoOperacao.ASSINADAS if "Folhas_Digitalizadas" in item.arquivo else TipoOperacao.GERACAO
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
