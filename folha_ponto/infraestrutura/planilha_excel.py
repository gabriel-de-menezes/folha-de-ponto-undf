"""Leitura da planilha de servidores (.xlsx)."""
import openpyxl

from ..dominio.calendario import interpretar_data
from ..dominio.regras import PlanilhaInvalida, sem_acento

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


EXTENSOES = (".xls", ".xlsx")
OBRIGATORIAS = {"nome": "Nome", "matricula": "Matrícula", "cpf": "CPF", "email": "E-mail",
                "carga_horaria": "Carga Horária", "acumula_cargo": "Acumula cargo (Sim/Não)"}


def _ler_linhas(caminho):
    if caminho.lower().endswith(".xls"):
        try:
            import xlrd
        except ImportError:
            raise PlanilhaInvalida("Para ler arquivos .xls é preciso o componente xlrd. "
                                   "Salve a planilha como .xlsx e tente novamente.")
        livro = xlrd.open_workbook(caminho)
        aba = livro.sheet_by_index(0)
        return [tuple(c.value if c.ctype != xlrd.XL_CELL_EMPTY else None for c in aba.row(i)) for i in range(aba.nrows)]
    wb = openpyxl.load_workbook(caminho, data_only=True, read_only=True)
    try:
        return list(wb.active.iter_rows(values_only=True))
    finally:
        wb.close()


def _carregar(caminho):
    """Valida a extensão e devolve todas as linhas da 1ª aba."""
    if not caminho.lower().endswith(EXTENSOES):
        raise PlanilhaInvalida("Formato não aceito. Envie uma planilha Excel com extensão .xlsx ou .xls.")
    try:
        linhas = _ler_linhas(caminho)
    except PlanilhaInvalida:
        raise
    except Exception as e:
        raise PlanilhaInvalida(f"Não foi possível ler a planilha: {e}")
    if not linhas:
        raise PlanilhaInvalida("Planilha vazia.")
    return linhas


def _linhas(caminho):
    linhas = _carregar(caminho)
    mapa = _mapear_colunas([str(c).strip().lower() if c is not None else "" for c in linhas[0]])
    faltando = [rotulo for chave, rotulo in OBRIGATORIAS.items() if chave not in mapa]
    if faltando:
        raise PlanilhaInvalida("A primeira linha da planilha não está no padrão esperado. Colunas ausentes: "
                               + ", ".join(faltando) + ".\nUse o modelo disponível em “Baixar modelo da planilha”.")
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
        registros, ignoradas, vistas = [], [], set()
        for n, linha in enumerate(linhas, start=2):
            nome, matricula = _valor(linha, mapa, "nome"), _valor(linha, mapa, "matricula")
            if not nome and not matricula:
                continue  # linha vazia ou só com anotações
            if not nome or not matricula:
                ignoradas.append(f"linha {n} (sem {'nome' if not nome else 'matrícula'})")
                continue
            if matricula in vistas:
                ignoradas.append(f"linha {n} (matrícula {matricula} duplicada na planilha)")
                continue
            vistas.add(matricula)
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


class LeitorCalendarioExcel:
    """Planilha do calendário acadêmico: colunas “Data” e “Especificação”."""

    def ler(self, caminho):
        """-> (registros [(date, especificação)], ignoradas)"""
        linhas = _carregar(caminho)
        cab = [sem_acento(str(c or "")).strip().lower() for c in linhas[0]]
        col_data = next((i for i, c in enumerate(cab) if c.startswith("data")), None)
        col_esp = next((i for i, c in enumerate(cab) if c.startswith("especifica") or c.startswith("descri")), None)
        faltando = [r for r, c in (("Data", col_data), ("Especificação", col_esp)) if c is None]
        if faltando:
            raise PlanilhaInvalida("A primeira linha da planilha não está no padrão esperado. Colunas ausentes: "
                                   + ", ".join(faltando) + ".")
        registros, ignoradas, vistas = [], [], set()
        for n, linha in enumerate(linhas[1:], start=2):
            bruto = linha[col_data] if col_data < len(linha) else None
            esp = str(linha[col_esp]).strip() if col_esp < len(linha) and linha[col_esp] is not None else ""
            if bruto in (None, "") and not esp:
                continue
            data = interpretar_data(bruto)
            if not data:
                ignoradas.append(f"linha {n} (data inválida)")
            elif not esp:
                ignoradas.append(f"linha {n} (sem especificação)")
            elif data in vistas:
                ignoradas.append(f"linha {n} (data {data.strftime('%d/%m/%Y')} repetida na planilha)")
            else:
                vistas.add(data)
                registros.append((data, esp))
        return registros, ignoradas
