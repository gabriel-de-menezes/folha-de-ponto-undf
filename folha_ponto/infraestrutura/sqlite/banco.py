"""Conexão SQLite, schema e migrações (compatível com bancos criados pelas versões anteriores)."""
import sqlite3
import unicodedata
from datetime import datetime, timezone

from ...dominio.competencia import normalizar_competencia

SCHEMA = """
CREATE TABLE IF NOT EXISTS servidores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    matricula TEXT UNIQUE NOT NULL,
    cpf TEXT,
    email TEXT,
    carga_horaria TEXT,
    acumula_cargo TEXT DEFAULT 'Não',
    ua TEXT DEFAULT '1',
    cargo TEXT DEFAULT 'PROF-M20 - Professor - Magistério Superior',
    padrao TEXT DEFAULT 'PM-1Q',
    funcao TEXT DEFAULT '',
    exercicio TEXT DEFAULT 'CEINTER - CENTRO INTERDISCIPLINAR',
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS folhas_geradas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    servidor_id INTEGER NOT NULL REFERENCES servidores(id),
    competencia TEXT NOT NULL,
    caminho_docx TEXT,
    caminho_pdf TEXT,
    gerado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS folhas_digitalizadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caminho_arquivo TEXT NOT NULL,
    servidor_id INTEGER REFERENCES servidores(id),
    competencia TEXT,
    status_ocr TEXT DEFAULT 'Pendente',   -- Processado, Pendente Validação, Validado
    texto_extraido TEXT,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS logs_envio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    servidor_id INTEGER NOT NULL REFERENCES servidores(id),
    competencia TEXT NOT NULL,
    destinatario TEXT NOT NULL,
    status TEXT NOT NULL,                 -- Enviado, Erro
    detalhes_erro TEXT,
    anexo TEXT,
    enviado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS operacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    competencia TEXT NOT NULL,
    iniciado_em TEXT NOT NULL,
    concluido_em TEXT,
    status TEXT NOT NULL DEFAULT 'Em andamento',
    usuario TEXT,
    computador TEXT,
    origem TEXT,
    origem_hash TEXT,
    metodo_envio TEXT,
    relatorio TEXT
);
CREATE TABLE IF NOT EXISTS operacao_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operacao_id INTEGER NOT NULL REFERENCES operacoes(id),
    servidor_id INTEGER,
    nome TEXT, matricula TEXT, cpf TEXT, email TEXT,
    arquivo TEXT, arquivo_hash TEXT,
    identificacao TEXT, observacao TEXT,
    selecionado INTEGER DEFAULT 0,
    envio_status TEXT, envio_detalhe TEXT, enviado_em TEXT
);
CREATE TABLE IF NOT EXISTS operacao_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operacao_id INTEGER NOT NULL REFERENCES operacoes(id),
    momento TEXT NOT NULL,
    descricao TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT
);
"""

# Colunas adicionadas depois da primeira versão (bancos antigos recebem via ALTER TABLE)
COLUNAS_NOVAS = [
    ("folhas_digitalizadas", "atualizado_em", "DATETIME"),
    ("folhas_digitalizadas", "hash_arquivo", "TEXT"),
    ("folhas_digitalizadas", "metodo_identificacao", "TEXT"),
    ("logs_envio", "anexo", "TEXT"),
    ("logs_envio", "operacao_id", "INTEGER"),
]


def _sem_acento(texto):
    if texto is None:
        return None
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn").lower()


def utc_para_local(valor):
    """Colunas com CURRENT_TIMESTAMP do SQLite estão em UTC; converte para o horário local."""
    if not valor:
        return ""
    try:
        dt = datetime.strptime(str(valor)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(valor)


class Banco:
    def __init__(self, caminho):
        self.caminho = caminho

    def conectar(self):
        conn = sqlite3.connect(self.caminho, timeout=15)
        conn.row_factory = sqlite3.Row
        # Busca sem acento/maiúsculas: SEM_ACENTO(nome) LIKE SEM_ACENTO(?)
        conn.create_function("SEM_ACENTO", 1, _sem_acento, deterministic=True)
        return conn

    def inicializar(self):
        conn = self.conectar()
        try:
            conn.executescript(SCHEMA)
            for tabela, coluna, tipo in COLUNAS_NOVAS:
                existentes = [r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")]
                if coluna not in existentes:
                    conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
            # Competências antigas ("JUL/2026", "07/2026") -> "JULHO/2026"
            for tabela in ("folhas_geradas", "folhas_digitalizadas", "logs_envio"):
                for (valor,) in conn.execute(f"SELECT DISTINCT competencia FROM {tabela} WHERE competencia IS NOT NULL").fetchall():
                    novo = normalizar_competencia(valor)
                    if novo and novo != valor:
                        conn.execute(f"UPDATE {tabela} SET competencia = ? WHERE competencia = ?", (novo, valor))
            # Uma folha gerada por servidor/competência
            conn.execute("""DELETE FROM folhas_geradas WHERE id NOT IN (
                                SELECT MAX(id) FROM folhas_geradas GROUP BY servidor_id, competencia)""")
            # O envio via Resend foi removido: quem usava passa a usar SMTP
            conn.execute("UPDATE configuracoes SET valor = 'SMTP' WHERE chave = 'metodo_envio' AND valor = 'Resend'")
            conn.commit()
        finally:
            conn.close()
