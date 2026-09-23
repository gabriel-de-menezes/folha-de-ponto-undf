"""Regras de negócio puras: identificação de folhas, textos de e-mail e formatação."""
import re
import unicodedata
from datetime import datetime

from .competencia import normalizar_competencia, rotulo_competencia
from .entidades import TipoOperacao


class ErroDominio(Exception):
    """Erro de regra de negócio, com mensagem pronta para o usuário."""


class PlanilhaInvalida(ErroDominio):
    pass


class MatriculaDuplicada(ErroDominio):
    pass


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")


def identificar_servidor(texto, servidores):
    """
    Descobre de quem é a folha a partir do texto (lido do PDF ou por OCR):
    1. matrícula isolada no texto (ignorando pontos/traços);
    2. senão, nome completo — todas as palavras com 3+ letras presentes; vence o nome mais longo.
    Também procura a competência (ex: "REFERÊNCIA: JULHO/2026"), no formato canônico.
    Retorna (servidor_id ou None, competência ou "").
    """
    texto = sem_acento(texto).upper()
    numeros = {re.sub(r"\D", "", n) for n in re.findall(r"\d[\d.\-/ ]{3,}\d", texto)} | set(re.findall(r"\d+", texto))

    encontrado = None
    for s in servidores:
        matricula = re.sub(r"\D", "", str(s.matricula or ""))
        if len(matricula) >= 4 and matricula in numeros:
            encontrado = s.id
            break

    if not encontrado:
        palavras = set(re.findall(r"[A-Z]+", texto))
        maior = 0
        for s in servidores:
            partes = [p for p in re.findall(r"[A-Z]+", sem_acento(s.nome).upper()) if len(p) >= 3]
            if len(partes) >= 2 and all(p in palavras for p in partes) and len(partes) > maior:
                encontrado, maior = s.id, len(partes)

    competencia = ""
    m = re.search(r"REFERENCIA\W*([A-Z0-9]+\s*[/\-. ]\s*20\d{2})", texto)
    candidata = normalizar_competencia(m.group(1) if m else texto)
    if re.fullmatch(r"[A-ZÇ]+/\d{4}", candidata or ""):
        competencia = candidata
    return encontrado, competencia


def resolver_conflitos(folhas):
    """Se duas folhas do lote foram identificadas para o mesmo servidor, a segunda fica sem dono
    para o usuário decidir na conferência."""
    donos = set()
    for f in folhas:
        if f.servidor_id in donos:
            f.servidor_id = None
            f.observacao = "Servidor já tem outra folha neste lote"
        elif f.servidor_id:
            donos.add(f.servidor_id)
    return folhas


def montar_email(nome, competencia, tipo):
    """Assunto e corpo do e-mail enviado ao servidor com a sua folha."""
    mes = rotulo_competencia(competencia)
    assunto = f"Folha de Ponto - UnDF ({mes}) - {nome}"
    if tipo == TipoOperacao.ASSINADAS:
        texto = f"Segue em anexo a sua folha de ponto assinada referente a {mes}, para seu arquivo e comprovação."
    else:
        texto = f"Segue em anexo a sua folha de ponto referente a {mes}, para preenchimento e assinatura."
    corpo = f"Prezado(a) {nome},\n\n{texto}\n\nAtenciosamente,\nDiretoria de Gestão de Pessoas - DIGEP/UnDF"
    return assunto, corpo


def mascarar_cpf(cpf):
    """LGPD: mostra só os 3 primeiros e os 2 últimos dígitos (111.***.***-01)."""
    digitos = "".join(c for c in (cpf or "") if c.isdigit())
    if len(digitos) != 11:
        return cpf or "—"
    return f"{digitos[:3]}.***.***-{digitos[9:]}"


def nome_arquivo_seguro(texto):
    return "".join(c for c in (texto or "") if c.isalnum() or c in (" ", "_", "-")).strip()


def data_br(valor):
    """"AAAA-MM-DD HH:MM:SS" -> "DD/MM/AAAA HH:MM"."""
    if not valor:
        return ""
    try:
        return datetime.strptime(str(valor)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(valor)
