import docx
import os
import re

def fill_folha_docx(modelo_path, servidor_data, competencia, output_path):
    """
    Preenche o modelo .docx com os dados do servidor e a competência (mês/ano).
    
    servidor_data = {
        'nome': 'ALEXANDRE NATA VICENTE',
        'matricula': '17289106',
        'carga_horaria': '40h',
        'ua': '1',
        'cargo': 'PROF-M20 - Professor - Magistério Superior',
        'padrao': 'PM-1Q',
        'funcao': '',
        'exercicio': 'CEINTER - CENTRO INTERDISCIPLINAR'
    }
    """
    doc = docx.Document(modelo_path)
    
    nome = servidor_data.get('nome', '') or ''
    matricula = servidor_data.get('matricula', '') or ''
    carga_horaria = servidor_data.get('carga_horaria', '') or ''
    ua = servidor_data.get('ua', '1')
    cargo = servidor_data.get('cargo', 'PROF-M20 - Professor - Magistério Superior')
    padrao = servidor_data.get('padrao', 'PM-1Q')
    funcao = servidor_data.get('funcao', '')
    exercicio = servidor_data.get('exercicio', 'CEINTER - CENTRO INTERDISCIPLINAR')
    
    # Percorre tabelas e parágrafos do documento
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    text = p.text
                    
                    # 1. Substituir Referência / Competência
                    if 'REFERÊNCIA:' in text or 'REFERENCIA:' in text:
                        p.text = f"REGISTRO DE FREQUÊNCIA           REFERÊNCIA:  {competencia.upper()} "
                    
                    # 2. Substituir Matrícula e UA
                    elif 'MATRÍCULA:' in text or 'MATRICULA:' in text:
                        p.text = f"UA:  {ua}                     MATRÍCULA: {matricula} "
                    
                    # 3. Substituir Nome do Servidor
                    elif 'NOME DO SERVIDOR:' in text:
                        p.text = f"NOME DO SERVIDOR: {nome.upper()} "
                    
                    # 4. Substituir Cargo, Padrão, Função e Carga Horária
                    elif 'CARGO:' in text:
                        p.text = f"CARGO:  {cargo}              PADRÃO: {padrao}\nFUNÇÃO: {funcao}                                                              CARGA HORÁRIA:  {carga_horaria}"
                    
                    # 5. Substituir Exercício
                    elif 'EXERCÍCIO:' in text or 'EXERCICIO:' in text:
                        p.text = f"EXERCÍCIO: {exercicio} "

    # Garante que a pasta de destino exista
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path

if __name__ == "__main__":
    test_servidor = {
        'nome': 'JOAO PORTELLA',
        'matricula': '99988877',
        'carga_horaria': '40h'
    }
    out = fill_folha_docx(
        r"Modelo de folha de ponto - Exemplo.docx",
        test_servidor,
        "AGOSTO/2026",
        r"output_test\Folha_JOAO_PORTELLA_AGOSTO_2026.docx"
    )
    print("Documento gerado em:", out)
