"""Entidades do domínio."""
from dataclasses import dataclass


class TipoOperacao:
    GERACAO = "GERACAO"      # gerar folhas a partir da planilha e enviar por e-mail
    ASSINADAS = "ASSINADAS"  # importar folhas assinadas (PDF/imagem) e enviar por e-mail

    DESCRICAO = {
        GERACAO: "Geração e envio de folhas de ponto",
        ASSINADAS: "Importação e envio de folhas assinadas",
    }

    @classmethod
    def descrever(cls, tipo):
        return cls.DESCRICAO.get(tipo, tipo)


class StatusEnvio:
    ENVIADO = "Enviado"
    ERRO = "Erro"
    NAO_SELECIONADO = "Não selecionado"


class MetodoIdentificacao:
    TEXTO = "Texto do PDF"
    OCR = "OCR"
    MANUAL = "Manual"
    NAO_IDENTIFICADO = "Não identificado"


@dataclass
class Servidor:
    nome: str
    matricula: str
    cpf: str = ""
    email: str = ""
    carga_horaria: str = ""
    acumula_cargo: str = "Não"
    ua: str = "1"
    cargo: str = "PROF-M20 - Professor - Magistério Superior"
    padrao: str = "PM-1Q"
    funcao: str = ""
    exercicio: str = "CEINTER - CENTRO INTERDISCIPLINAR"
    id: int | None = None

    CAMPOS = ("nome", "matricula", "cpf", "email", "carga_horaria", "acumula_cargo", "ua", "cargo", "padrao",
              "funcao", "exercicio")

    @property
    def acumula(self):
        return (self.acumula_cargo or "").strip().lower() == "sim"

    @property
    def tem_email(self):
        return bool((self.email or "").strip())

    def rotulo(self):
        return f"{self.nome} · {self.matricula}"


@dataclass
class ItemOperacao:
    """Um servidor (ou arquivo sem servidor) dentro de uma operação, com a folha e o resultado do envio."""
    servidor_id: int | None
    nome: str
    matricula: str = ""
    cpf: str = ""
    email: str = ""
    acumula: str = ""
    arquivo: str | None = None
    arquivo_hash: str = ""
    identificacao: str = ""
    observacao: str = ""
    selecionado: bool = True
    envio_status: str | None = None
    envio_detalhe: str = ""
    enviado_em: str | None = None

    @classmethod
    def de_servidor(cls, servidor, **campos):
        item = cls(servidor_id=servidor.id, nome=servidor.nome)
        item.atualizar_servidor(servidor)
        for chave, valor in campos.items():
            setattr(item, chave, valor)
        return item

    def atualizar_servidor(self, servidor):
        self.nome, self.matricula, self.cpf = servidor.nome, servidor.matricula, servidor.cpf
        self.email, self.acumula = servidor.email, servidor.acumula_cargo

    @property
    def tem_email(self):
        return bool((self.email or "").strip())

    @property
    def pode_enviar(self):
        return bool(self.servidor_id and self.arquivo and self.tem_email)


@dataclass
class Operacao:
    id: int
    tipo: str
    competencia: str
    iniciado_em: str
    status: str = "Em andamento"
    concluido_em: str | None = None
    usuario: str = ""
    computador: str = ""
    origem: str = ""
    origem_hash: str = ""
    metodo_envio: str = ""
    relatorio: str = ""
    qtd_itens: int = 0
    qtd_enviados: int = 0
    qtd_erros: int = 0

    @property
    def codigo(self):
        return codigo_operacao(self.id)

    @property
    def descricao_tipo(self):
        return TipoOperacao.descrever(self.tipo)

    @property
    def em_andamento(self):
        return self.status == "Em andamento"


def codigo_operacao(op_id):
    return f"OP-{int(op_id):06d}"


@dataclass
class EventoOperacao:
    momento: str
    descricao: str


@dataclass
class FolhaAssinada:
    """Arquivo (PDF ou imagem) importado no fluxo de folhas assinadas."""
    doc_id: int
    caminho: str
    hash: str
    original: str
    servidor_id: int | None = None
    metodo: str = MetodoIdentificacao.NAO_IDENTIFICADO
    competencia_lida: str = ""
    observacao: str = ""
    duplicado: bool = False


@dataclass
class FolhaArquivada:
    """Folha gerada ou assinada guardada no arquivo do sistema (consulta)."""
    id: int
    origem: str  # "Gerada" | "Digitalizada"
    nome: str
    matricula: str
    competencia: str
    caminho: str
    data_registro: str

    @property
    def chave(self):
        return f"{self.origem}-{self.id}"

    @property
    def assinada(self):
        return self.origem == "Digitalizada"


@dataclass
class RegistroEnvio:
    id: int
    servidor_id: int
    nome: str
    competencia: str
    destinatario: str
    status: str
    detalhes: str
    anexo: str | None
    enviado_em: str
    operacao_id: int | None


@dataclass
class ConfiguracaoEmail:
    metodo: str = "SMTP"  # "SMTP" | "Outlook"
    host: str = "smtp.gmail.com"
    porta: str = "587"
    usuario: str = ""
    senha: str = ""
    usar_tls: bool = True
    remetente_nome: str = "DIGEP - UnDF"

    METODOS = {"SMTP": "Servidor SMTP", "Outlook": "MS Outlook"}

    @property
    def configurado(self):
        if self.metodo == "Outlook":
            return True
        return bool(self.host and self.usuario and self.senha)

    def descricao(self):
        if self.metodo == "Outlook":
            return "MS Outlook"
        return f"SMTP {self.host} ({self.usuario})"


@dataclass
class InfoPlanilhaBase:
    caminho: str
    nome: str
    definida_em: str
    quantidade: int
