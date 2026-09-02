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
        enviado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (servidor_id) REFERENCES servidores(id)
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Banco de dados SQLite inicializado com sucesso!")
