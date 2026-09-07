import sqlite3
import os

DB_NAME = "folha_ponto.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Servidores
    cursor.execute("""
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
    )
    """)
    
    # Tabela de Folhas Geradas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS folhas_geradas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        servidor_id INTEGER NOT NULL,
        competencia TEXT NOT NULL,
        caminho_docx TEXT,
        caminho_pdf TEXT,
        gerado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (servidor_id) REFERENCES servidores(id)
    )
    """)
    
    # Tabela de Folhas Digitalizadas / Assinadas (OCR Upload)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS folhas_digitalizadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caminho_arquivo TEXT NOT NULL,
        servidor_id INTEGER,
        competencia TEXT,
        status_ocr TEXT DEFAULT 'Pendente', -- Processado, Erro, Validado
        texto_extraido TEXT,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (servidor_id) REFERENCES servidores(id)
    )
    """)
    
    # Tabela de Envio de E-mails
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs_envio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        servidor_id INTEGER NOT NULL,
        competencia TEXT NOT NULL,
        destinatario TEXT NOT NULL,
        status TEXT NOT NULL, -- Pendente, Enviado, Erro
        detalhes_erro TEXT,
        anexo TEXT,
        enviado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (servidor_id) REFERENCES servidores(id)
    )
    """)

    # Tabela de Configurações (SMTP, remetente etc.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )
    """)

    conn.commit()

    # Migração leve: adiciona colunas novas em bancos já existentes
    _garantir_coluna(cursor, "folhas_digitalizadas", "atualizado_em", "DATETIME")
    _garantir_coluna(cursor, "logs_envio", "anexo", "TEXT")
    conn.commit()
    conn.close()


def _garantir_coluna(cursor, tabela, coluna, tipo):
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = [row[1] for row in cursor.fetchall()]
    if coluna not in colunas_existentes:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def get_config(chave, padrao=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    conn.close()
    if row and row["valor"] is not None:
        return row["valor"]
    return padrao


def set_config(chave, valor):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
    """, (chave, valor))
    conn.commit()
    conn.close()


def get_all_config(defaults=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chave, valor FROM configuracoes")
    dados = {row["chave"]: row["valor"] for row in cursor.fetchall()}
    conn.close()
    if defaults:
        for k, v in defaults.items():
            dados.setdefault(k, v)
    return dados


if __name__ == "__main__":
    init_db()
    print("Banco de dados SQLite inicializado com sucesso!")
