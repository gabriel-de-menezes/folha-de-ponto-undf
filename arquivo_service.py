import os
from db import get_connection


def buscar_folha_arquivada(servidor_id, competencia):
    """
    Localiza o arquivo da folha de ponto arquivada para um servidor/competência.
    Prioriza a folha digitalizada (assinada, recebida via upload/OCR e validada),
    pois é o documento oficial. Se não houver digitalização, usa a folha gerada
    a partir do modelo .docx/PDF como alternativa.
    Retorna (caminho, origem) ou (None, None) se nada for encontrado.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT caminho_arquivo FROM folhas_digitalizadas
        WHERE servidor_id = ? AND competencia = ? AND status_ocr IN ('Validado', 'Processado')
        ORDER BY id DESC LIMIT 1
    """, (servidor_id, competencia))
    row = cursor.fetchone()
    if row and row["caminho_arquivo"] and os.path.exists(row["caminho_arquivo"]):
        conn.close()
        return row["caminho_arquivo"], "Digitalizada"

    cursor.execute("""
        SELECT caminho_pdf, caminho_docx FROM folhas_geradas
        WHERE servidor_id = ? AND competencia = ?
        ORDER BY id DESC LIMIT 1
    """, (servidor_id, competencia))
    row = cursor.fetchone()
    conn.close()
    if row:
        caminho = row["caminho_pdf"] or row["caminho_docx"]
        if caminho and os.path.exists(caminho):
            return caminho, "Gerada"

    return None, None


def vincular_digitalizacao(doc_id, servidor_id, competencia, status="Validado"):
    """Associa manualmente (conferência/validação) uma folha digitalizada a um servidor/competência."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE folhas_digitalizadas
        SET servidor_id = ?, competencia = ?, status_ocr = ?, atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (servidor_id, competencia, status, doc_id))
    conn.commit()
    conn.close()


def listar_folhas_arquivadas(filtro_nome="", filtro_matricula="", filtro_competencia=""):
    """
    Lista todas as folhas arquivadas (digitalizadas validadas + geradas), unificadas,
    para consulta por servidor, matrícula e/ou competência (RF07/RF08).
    """
    conn = get_connection()
    cursor = conn.cursor()

    like_nome = f"%{filtro_nome.strip()}%" if filtro_nome else "%"
    like_matricula = f"%{filtro_matricula.strip()}%" if filtro_matricula else "%"
    like_competencia = f"%{filtro_competencia.strip()}%" if filtro_competencia else "%"

    cursor.execute("""
        SELECT f.id, 'Digitalizada' as origem, s.nome, s.matricula, f.competencia,
               f.caminho_arquivo as caminho, f.status_ocr as status, f.criado_em as data_registro
        FROM folhas_digitalizadas f
        JOIN servidores s ON f.servidor_id = s.id
        WHERE f.status_ocr IN ('Validado', 'Processado')
          AND s.nome LIKE ? COLLATE NOCASE
          AND s.matricula LIKE ?
          AND f.competencia LIKE ?

        UNION ALL

        SELECT g.id, 'Gerada' as origem, s.nome, s.matricula, g.competencia,
               COALESCE(g.caminho_pdf, g.caminho_docx) as caminho, 'Arquivada' as status, g.gerado_em as data_registro
        FROM folhas_geradas g
        JOIN servidores s ON g.servidor_id = s.id
        WHERE s.nome LIKE ? COLLATE NOCASE
          AND s.matricula LIKE ?
          AND g.competencia LIKE ?

        ORDER BY data_registro DESC
    """, (like_nome, like_matricula, like_competencia, like_nome, like_matricula, like_competencia))

    resultados = cursor.fetchall()
    conn.close()
    return resultados


if __name__ == "__main__":
    print("Módulo de arquivamento/consulta carregado.")
