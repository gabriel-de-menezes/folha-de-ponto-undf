"""Utilitários para a competência (mês/ano) no formato canônico "MÊS/AAAA" (ex: JULHO/2026)."""
import re
import unicodedata
from datetime import date

MESES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
]


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


# Prefixo de 3 letras (sem acento) -> índice do mês. Ex: "MAR" -> 3
_PREFIXOS = {_sem_acento(m)[:3]: i + 1 for i, m in enumerate(MESES)}


def montar_competencia(mes_idx, ano):
    """mes_idx de 1 a 12."""
    return f"{MESES[mes_idx - 1]}/{int(ano)}"


def competencia_atual():
    hoje = date.today()
    return montar_competencia(hoje.month, hoje.year)


def separar_competencia(competencia):
    """Retorna (mes_idx, ano) ou (None, None) se não for reconhecida."""
    normalizada = normalizar_competencia(competencia)
    m = re.fullmatch(r"(\w+)/(\d{4})", normalizada or "")
    if not m:
        return None, None
    return MESES.index(m.group(1)) + 1, int(m.group(2))


def normalizar_competencia(texto):
    """
    Converte variações como "jul/2026", "Julho 2026", "07/2026", "7-2026", "MARCO/2026"
    para o formato canônico "JULHO/2026". Se não reconhecer, devolve o texto em maiúsculas.
    """
    if not texto:
        return ""
    bruto = str(texto).strip().upper()
    limpo = _sem_acento(bruto)

    m = re.search(r"\b([A-Z]{3,9})\s*[/\s\-.]*\s*(20\d{2})\b", limpo)
    if m and m.group(1)[:3] in _PREFIXOS:
        return montar_competencia(_PREFIXOS[m.group(1)[:3]], m.group(2))

    m = re.search(r"\b(\d{1,2})\s*[/\-.]\s*(20\d{2})\b", limpo)
    if m and 1 <= int(m.group(1)) <= 12:
        return montar_competencia(int(m.group(1)), m.group(2))

    return bruto


def rotulo_competencia(competencia):
    """"JULHO/2026" -> "Julho/2026" (para exibição)."""
    mes, ano = separar_competencia(competencia)
    if not mes:
        return competencia
    return f"{MESES[mes - 1].capitalize()}/{ano}"
