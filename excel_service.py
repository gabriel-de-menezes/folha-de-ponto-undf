import openpyxl
import sqlite3
from db import get_connection, init_db

def parse_and_import_excel(filepath):
    """
    Lê a planilha Excel de professores/servidores e importa os dados mapeados para o banco de dados.
    Apenas os campos presentes no Excel (Nome, Matrícula, CPF, E-mail, Carga Horária, Acumula Cargo)
    são atualizados; os demais mantêm o padrão do modelo docx.
    """
    init_db()
    
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return 0, "Planilha vazia."
    
    header = [str(cell).strip().lower() if cell is not None else '' for cell in rows[0]]
    
    # Mapeamento dinâmico de colunas
    col_map = {}
    for idx, col_name in enumerate(header):
        if 'nome' in col_name:
            col_map['nome'] = idx
        elif 'matr' in col_name:
            col_map['matricula'] = idx
        elif 'cpf' in col_name:
            col_map['cpf'] = idx
        elif 'mail' in col_name or 'e-mail' in col_name:
            col_map['email'] = idx
        elif 'carga' in col_name:
            col_map['carga_horaria'] = idx
        elif 'acumul' in col_name:
            col_map['acumula_cargo'] = idx

    conn = get_connection()
    cursor = conn.cursor()
    imported_count = 0
    
    for r_idx, row in enumerate(rows[1:], start=1):
        if not any(row):
            continue
            
        def get_val(key):
            if key in col_map and col_map[key] < len(row):
                val = row[col_map[key]]
                return str(val).strip() if val is not None else ""
            return ""

        nome = get_val('nome')
        matricula = get_val('matricula')
        cpf = get_val('cpf')
        email = get_val('email')
        carga_horaria = get_val('carga_horaria')
        acumula_cargo = get_val('acumula_cargo') or 'Não'

        # Normaliza Acumula cargo para 'Sim' ou 'Não'
        if acumula_cargo.lower() in ['sim', 's', 'true', '1']:
            acumula_cargo = 'Sim'
        else:
            acumula_cargo = 'Não'

        # Se for linha de exemplo com nome/matrícula vazios, atribui valores de teste padrão
        if not nome and not matricula:
            nome = f"PROFESSOR EXEMPLO {r_idx}"
            matricula = f"1728910{r_idx}"
            email = f"professor{r_idx}@undf.edu.br"

        # Inserção ou atualização no SQLite (UPSERT)
        cursor.execute("""
            INSERT INTO servidores (nome, matricula, cpf, email, carga_horaria, acumula_cargo)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(matricula) DO UPDATE SET
                nome=excluded.nome,
                cpf=excluded.cpf,
                email=excluded.email,
                carga_horaria=excluded.carga_horaria,
                acumula_cargo=excluded.acumula_cargo
        """, (nome, matricula, cpf, email, carga_horaria, acumula_cargo))
        imported_count += 1

    conn.commit()
    conn.close()
    return imported_count, f"{imported_count} servidores importados/atualizados com sucesso."

if __name__ == "__main__":
    count, msg = parse_and_import_excel(r"Planilha de professores - exemplo.xlsx")
    print(msg)
