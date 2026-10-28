"""Verificação da instalação: exercita, numa pasta temporária, cada parte que depende de algo empacotado
(bibliotecas, modelos, Tesseract) ou externo (Word). Usada por "DIGEP_Folha_de_Ponto.exe --verificar"."""
import os
import shutil
import tempfile
import traceback

import openpyxl
import pymupdf

from .armazenamento import ArmazenamentoLocal
from .container import montar_servicos
from .leitor_folhas import LeitorFolhasTesseract

COMPETENCIA = "FEVEREIRO/2026"


def _etapa(resultados, nome, funcao, obrigatoria=True):
    try:
        detalhe = funcao()
        resultados.append(("OK", nome, detalhe or ""))
    except Exception as erro:
        resultados.append(("FALHA" if obrigatoria else "AVISO", nome, f"{erro}\n{traceback.format_exc()}"))


def verificar_instalacao():
    """Devolve [(situacao, etapa, detalhe)], com situacao em OK / AVISO / FALHA."""
    resultados = []
    pasta = tempfile.mkdtemp(prefix="digep_verificacao_")
    try:
        servicos = None

        def abrir_sistema():
            nonlocal servicos
            # fora do .exe os modelos são lidos da pasta do sistema: copia os da instalação para a temporária
            instalado = ArmazenamentoLocal()
            os.makedirs(os.path.join(pasta, "recursos"))
            for modelo in (instalado.modelo_folha, instalado.modelo_planilha):
                shutil.copy2(modelo, os.path.join(pasta, "recursos"))
            servicos = montar_servicos(pasta)
        _etapa(resultados, "Banco de dados e pastas", abrir_sistema)
        if servicos is None:
            return resultados
        planilha = os.path.join(pasta, "servidores.xlsx")

        def ler_planilha():
            # o modelo distribuído só tem o cabeçalho: preenche uma linha numa cópia dele
            wb = openpyxl.load_workbook(servicos.armazenamento.modelo_planilha)
            cabecalho = [str(c.value or "").strip().lower() for c in wb.active[1]]
            valores = {"nome": "Servidor de Teste", "matrícula": "9999999", "e-mail": "teste@exemplo.br",
                       "carga horária": "40h"}
            wb.active.append([valores.get(coluna, "") for coluna in cabecalho])
            wb.save(planilha)
            resumo = servicos.servidores.analisar_planilha(planilha)
            return f"{len(resumo.todos)} servidor(es) na planilha de exemplo"
        _etapa(resultados, "Leitura de planilha (openpyxl/xlrd)", ler_planilha)

        geracao = {}

        def gerar_folhas():
            geracao["r"] = servicos.gerar_folhas.executar(COMPETENCIA, planilha)
            itens = geracao["r"].itens
            if not itens or not all(i.arquivo and os.path.exists(i.arquivo) for i in itens):
                raise RuntimeError("folhas não geradas: " + "; ".join(geracao["r"].erros or []))
            return f"{len(itens)} folha(s) geradas"
        _etapa(resultados, "Geração das folhas (python-docx)", gerar_folhas)

        def converter_pdf():
            if "r" not in geracao:
                raise RuntimeError("a geração das folhas falhou")
            if geracao["r"].sem_pdf:
                raise RuntimeError("Microsoft Word não encontrado: as folhas saem só em .docx")
            return "folhas convertidas pelo Word"
        _etapa(resultados, "Conversão para PDF (Microsoft Word)", converter_pdf, obrigatoria=False)

        def ler_com_ocr():
            leitor = LeitorFolhasTesseract()
            if not leitor.ocr_disponivel():
                raise RuntimeError("Tesseract não encontrado ou sem idiomas")
            pdf = os.path.join(pasta, "ocr.pdf")
            with pymupdf.open() as doc:
                doc.new_page().insert_text((72, 120), "FOLHA DE PONTO 2026", fontsize=28)
                doc.save(pdf)
            leituras = list(leitor.leituras_ocr(pdf, 1))
            if not any("PONTO" in t.upper() for t in leituras):
                raise RuntimeError(f"texto não reconhecido: {leituras[:1]!r}")
            return "texto reconhecido em PDF (pymupdf + Tesseract)"
        _etapa(resultados, "Leitura de folhas digitalizadas (OCR)", ler_com_ocr)

        def modulos_de_envio():
            import smtplib, ssl  # noqa: E401,F401  (envio por SMTP)
            import win32com.client  # noqa: F401    (envio pelo Outlook)
            return "smtplib, ssl e win32com carregados"
        _etapa(resultados, "Módulos de envio de e-mail", modulos_de_envio)
        return resultados
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def relatorio(resultados):
    linhas = [f"[{situacao}] {etapa}: {detalhe.splitlines()[0] if detalhe else ''}"
              for situacao, etapa, detalhe in resultados]
    falhas = [r for r in resultados if r[0] == "FALHA"]
    for situacao, etapa, detalhe in falhas:
        linhas += ["", f"--- {etapa} ---", detalhe]
    linhas += ["", "Resultado: " + ("COM FALHAS" if falhas else "OK")]
    return "\n".join(linhas)
