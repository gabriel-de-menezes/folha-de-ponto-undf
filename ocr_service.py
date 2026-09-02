import fitz # PyMuPDF
import re
import os
from PIL import Image
import pytesseract
from db import get_connection

def extract_text_from_file(file_path):
    """
    Extrai todo o texto de um arquivo PDF ou Imagem (PNG, JPG, TIFF).
    Utiliza PyMuPDF para extração direta de texto em PDF e pytesseract como OCR fallback.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    if ext == '.pdf':
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            text = f"Erro PyMuPDF: {e}"
            
        # Se o PDF for uma imagem digitalizada sem camada de texto (escaneado), tenta pytesseract
        if not text.strip():
            try:
                doc = fitz.open(file_path)
                for page in doc:
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text += pytesseract.image_to_string(img, lang='por+eng')
                doc.close()
            except Exception as e:
                text += f"\nErro pytesseract: {e}"

    elif ext in ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']:
        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang='por+eng')
        except Exception as e:
            text = f"Erro ao ler imagem: {e}"
            
    return text

def identify_server_and_competencia(extracted_text):
    """
    Analisa o texto extraído por OCR/PDF e procura por:
    - Matrícula (ex: 8 dígitos consecutivos)
    - Nome do Servidor
    - Competência (ex: JULHO/2026 ou 07/2026)
    Retorna o servidor_id correspondente (se encontrado) e a competência.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, nome, matricula FROM servidores")
    servidores = cursor.fetchall()
    
    matched_servidor_id = None
    
    # 1. Busca por matrícula exata no texto
    for s in servidores:
        if s['matricula'] and str(s['matricula']) in extracted_text:
            matched_servidor_id = s['id']
            break
            
    # 2. Se não achou por matrícula, busca por partes do nome
    if not matched_servidor_id:
        for s in servidores:
            nome = s['nome']
            if nome and len(nome) > 4:
                primeiro_ultimo = nome.split()[0] + " " + nome.split()[-1]
                if primeiro_ultimo.upper() in extracted_text.upper():
                    matched_servidor_id = s['id']
                    break

    # 3. Busca por competência (Mês/Ano)
    competencia_found = ""
    comp_match = re.search(r'(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ|JANEIRO|FEVEREIRO|MARÇO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)[/\s-]*(20\d{2})', extracted_text, re.IGNORECASE)
    if comp_match:
        competencia_found = f"{comp_match.group(1).upper()}/{comp_match.group(2)}"
    else:
        comp_num_match = re.search(r'(\d{2})[/\s-](20\d{2})', extracted_text)
        if comp_num_match:
            competencia_found = f"{comp_num_match.group(1)}/{comp_num_match.group(2)}"

    conn.close()
    return matched_servidor_id, competencia_found

def process_scanned_file(file_path):
    """
    Processa um arquivo digitalizado (upload em lote), extrai texto e associa ao servidor no banco.
    """
    text = extract_text_from_file(file_path)
    servidor_id, competencia = identify_server_and_competencia(text)
    
    status = "Processado" if servidor_id else "Pendente Validação"
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO folhas_digitalizadas (caminho_arquivo, servidor_id, competencia, status_ocr, texto_extraido)
        VALUES (?, ?, ?, ?, ?)
    """, (file_path, servidor_id, competencia, status, text[:2000]))
    
    rec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        'id': rec_id,
        'servidor_id': servidor_id,
        'competencia': competencia,
        'status': status,
        'caminho': file_path
    }

if __name__ == "__main__":
    print("Módulo de OCR carregado.")
