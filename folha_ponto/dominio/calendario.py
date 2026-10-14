"""Datas especiais do calendário acadêmico (feriados, recessos, pontos facultativos)."""
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .regras import sem_acento


@dataclass
class DataEspecial:
    data: date
    especificacao: str

    @property
    def data_br(self):
        return self.data.strftime("%d/%m/%Y")


def interpretar_data(valor):
    """Aceita date/datetime, número serial do Excel e textos "DD/MM/AAAA", "D/M/AA" ou "AAAA-MM-DD".
    Retorna date ou None."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and 20000 < valor < 80000:
        return (datetime(1899, 12, 30) + timedelta(days=float(valor))).date()
    texto = str(valor or "").strip()
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})", texto)
    try:
        if m:
            ano = int(m.group(3))
            return date(ano + 2000 if ano < 100 else ano, int(m.group(2)), int(m.group(1)))
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?", texto)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return None


def rotulo_na_folha(especificacao):
    """Palavra curta que ocupa o dia na folha de ponto (as células são estreitas)."""
    texto = sem_acento(especificacao).upper()
    if "RECESSO" in texto:
        return "RECESSO"
    if "FACULTATIVO" in texto:
        return "FACULTATIVO"
    return "FERIADO"
