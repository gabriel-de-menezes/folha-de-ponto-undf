"""Raiz de composição: cria os adaptadores concretos e injeta nos casos de uso."""
from dataclasses import dataclass

from ..aplicacao.auditoria import ServicoAuditoria
from ..aplicacao.configuracoes import ServicoConfiguracoes
from ..aplicacao.consultas import Consultas
from ..aplicacao.envio import EnviarFolhas
from ..aplicacao.folhas_assinadas import FolhasAssinadas
from ..aplicacao.gerar_folhas import GerarFolhas
from ..aplicacao.servidores import ServicoServidores
from .ambiente import AmbienteLocal
from .armazenamento import ArmazenamentoLocal
from .envio_email import ServicoEmailPadrao
from .folha_docx import GeradorFolhasDocx
from .leitor_folhas import LeitorFolhasTesseract
from .planilha_excel import LeitorPlanilhaExcel
from .relatorio_pdf import GeradorRelatorioPDF
from .sqlite.banco import Banco
from .sqlite.repositorios import (
    RepositorioConfiguracoesSQLite, RepositorioEnviosSQLite, RepositorioFolhasSQLite, RepositorioOperacoesSQLite,
    RepositorioServidoresSQLite,
)


@dataclass
class Servicos:
    """Tudo o que a interface pode usar — apenas casos de uso da camada de aplicação."""
    servidores: ServicoServidores
    gerar_folhas: GerarFolhas
    folhas_assinadas: FolhasAssinadas
    envio: EnviarFolhas
    auditoria: ServicoAuditoria
    configuracoes: ServicoConfiguracoes
    consultas: Consultas
    armazenamento: ArmazenamentoLocal


def montar_servicos(pasta_app=None, servico_email=None, gerador_folhas=None, leitor_folhas=None):
    """Monta a aplicação. Os parâmetros opcionais permitem substituir adaptadores (ex.: em testes)."""
    armazenamento = ArmazenamentoLocal(pasta_app)
    banco = Banco(armazenamento.banco)
    banco.inicializar()
    ambiente = AmbienteLocal()

    repo_servidores = RepositorioServidoresSQLite(banco)
    repo_folhas = RepositorioFolhasSQLite(banco)
    repo_operacoes = RepositorioOperacoesSQLite(banco)
    repo_envios = RepositorioEnviosSQLite(banco)
    repo_config = RepositorioConfiguracoesSQLite(banco)
    servico_email = servico_email or ServicoEmailPadrao()

    auditoria = ServicoAuditoria(repo_operacoes, GeradorRelatorioPDF(), armazenamento, ambiente)
    configuracoes = ServicoConfiguracoes(repo_config, servico_email)
    servidores = ServicoServidores(repo_servidores, LeitorPlanilhaExcel(), armazenamento, repo_config, ambiente)
    return Servicos(
        servidores=servidores,
        gerar_folhas=GerarFolhas(servidores, repo_folhas, gerador_folhas or GeradorFolhasDocx(armazenamento),
                                 armazenamento, auditoria),
        folhas_assinadas=FolhasAssinadas(repo_servidores, repo_folhas, leitor_folhas or LeitorFolhasTesseract(),
                                         armazenamento, auditoria),
        envio=EnviarFolhas(servico_email, repo_envios, configuracoes, auditoria, ambiente),
        auditoria=auditoria,
        configuracoes=configuracoes,
        consultas=Consultas(repo_folhas, repo_envios),
        armazenamento=armazenamento,
    )
