"""Leitura da planilha de servidores (.xlsx)."""
import openpyxl

from ..dominio.regras import PlanilhaInvalida

# Campos do modelo da folha que só são atualizados se a planilha tiver a coluna
CAMPOS_OPCIONAIS = ("ua", "cargo", "padrao", "funcao", "exercicio")


def _mapear_colunas(cabecalho):
    """Reconhece as colunas pelo nome (ex.: "Matrícula", "E-mail", "Acumula cargo (Sim/Não)")."""
    mapa = {}
    for idx, nome in enumerate(cabecalho):
        if "acumul" in nome:
            mapa.setdefault("acumula_cargo", idx)
        elif "nome" in nome:
            mapa.setdefault("nome", idx)
        elif "matr" in nome:
            mapa.setdefault("matricula", idx)
        elif "cpf" in nome:
            mapa.setdefault("cpf", idx)
        elif "mail" in nome:
            mapa.setdefault("email", idx)
        elif "carga" in nome:
            mapa.setdefault("carga_horaria", idx)
        elif "cargo" in nome:
            mapa.setdefault("cargo", idx)
        elif "padr" in nome:
            mapa.setdefault("padrao", idx)
        elif "fun" in nome:
            mapa.setdefault("funcao", idx)
        elif "exerc" in nome or "lota" in nome:
            mapa.setdefault("exercicio", idx)
        elif nome in ("ua", "u.a.", "unidade administrativa"):
            mapa.setdefault("ua", idx)
    return mapa


def _linhas(caminho):
    try:
        wb = openpyxl.load_workbook(caminho, data_only=True, read_only=True)
        linhas = list(wb.active.iter_rows(values_only=True))
        wb.close()
    except Exception as e:
        raise PlanilhaInvalida(f"Não foi possível ler a planilha: {e}")
    if not linhas:
        raise PlanilhaInvalida("Planilha vazia.")
    mapa = _mapear_colunas([str(c).strip().lower() if c is not None else "" for c in linhas[0]])
    if "nome" not in mapa or "matricula" not in mapa:
        raise PlanilhaInvalida("A planilha precisa ter as colunas “Nome” e “Matrícula” na primeira linha.")
    return linhas[1:], mapa


def _valor(linha, mapa, chave):
    if chave in mapa and mapa[chave] < len(linha):
        valor = linha[mapa[chave]]
        if isinstance(valor, float) and valor.is_integer():
            valor = int(valor)  # matrícula/CPF lidos como número (ex: 17289106.0)
        return str(valor).strip() if valor is not None else ""
    return ""


class LeitorPlanilhaExcel:
    def ler(self, caminho):
        """-> (registros, ignoradas). Cada registro traz só os campos presentes na planilha."""
        linhas, mapa = _linhas(caminho)
        registros, ignoradas = [], []
        for n, linha in enumerate(linhas, start=2):
            nome, matricula = _valor(linha, mapa, "nome"), _valor(linha, mapa, "matricula")
            if not nome and not matricula:
                continue  # linha vazia ou só com anotações
            if not nome or not matricula:
                ignoradas.append(f"linha {n} (sem {'nome' if not nome else 'matrícula'})")
                continue
            acumula = _valor(linha, mapa, "acumula_cargo").lower() in ("sim", "s", "true", "1", "x")
            dados = {"nome": nome, "matricula": matricula, "cpf": _valor(linha, mapa, "cpf"),
                     "email": _valor(linha, mapa, "email"), "carga_horaria": _valor(linha, mapa, "carga_horaria"),
                     "acumula_cargo": "Sim" if acumula else "Não"}
            for campo in CAMPOS_OPCIONAIS:
                if _valor(linha, mapa, campo):
                    dados[campo] = _valor(linha, mapa, campo)
            registros.append(dados)
        return registros, ignoradas

    def contar(self, caminho):
        try:
            return len(self.ler(caminho)[0])
        except PlanilhaInvalida:
            return 0
