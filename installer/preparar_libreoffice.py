"""
Prepara o LibreOffice portátil que o instalador (DIGEP_Setup.iss) leva junto, em installer/LibreOffice.
É ele que converte as folhas geradas em PDF num computador sem Microsoft Word.

Baixa o LibreOffice Portable oficial (The Document Foundation), confere o SHA-256, extrai com o 7-Zip (sem
instalar nada) e tira o que a conversão para PDF não usa: ajuda, dicionários e telas em outros idiomas.
Só precisa do Python (sem as bibliotecas do projeto).

Uso:  python installer/preparar_libreoffice.py
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from preparar_tesseract import achar_7zip, baixar  # noqa: E402

DESTINO = os.path.join(AQUI, "LibreOffice")
VERSAO = "26.2.4"
URL = (f"https://download.documentfoundation.org/libreoffice/portable/{VERSAO}/"
       f"LibreOfficePortable_{VERSAO}_MultilingualStandard.paf.exe")
SHA256 = "4bde93374aef4409243505b20d16561a4628ac7591457dd01fc6e1ccf571ba65"
IDIOMAS_TELA = ("pt_BR", "common")  # program/resource: textos da interface


def enxugar(pasta):
    """Remove o que a conversão .docx -> .pdf não usa."""
    shutil.rmtree(os.path.join(pasta, "help"), ignore_errors=True)
    extensoes = os.path.join(pasta, "share", "extensions")
    for item in glob.glob(os.path.join(extensoes, "dict-*")) + [os.path.join(extensoes, "nlpsolver"),
                                                                os.path.join(extensoes, "wiki-publisher")]:
        shutil.rmtree(item, ignore_errors=True)
    recursos = os.path.join(pasta, "program", "resource")
    for idioma in os.listdir(recursos):
        if idioma not in IDIOMAS_TELA:
            shutil.rmtree(os.path.join(recursos, idioma), ignore_errors=True)


def testar(pasta):
    """Converte um .docx de teste. Fora do Windows não há como rodar o soffice.exe: devolve False."""
    if os.name != "nt":
        return False
    soffice = os.path.join(pasta, "program", "soffice.exe")
    raiz = os.path.dirname(AQUI)
    modelo = os.path.join(raiz, "recursos", "Modelo de folha de ponto - Exemplo.docx")
    with tempfile.TemporaryDirectory() as temporaria:
        docx = os.path.join(temporaria, "teste.docx")
        shutil.copy2(modelo, docx)
        perfil = "file:///" + os.path.join(temporaria, "perfil").replace("\\", "/")
        saida = subprocess.run([soffice, f"-env:UserInstallation={perfil}", "--headless", "--norestore",
                                "--convert-to", "pdf", "--outdir", temporaria, docx],
                               capture_output=True, text=True, timeout=300)
        if not os.path.isfile(os.path.join(temporaria, "teste.pdf")):
            sys.exit(f"O LibreOffice preparado não converteu o modelo em PDF:\n{saida.stdout}\n{saida.stderr}")
    return True


def main():
    with tempfile.TemporaryDirectory() as temporaria:
        sete_zip = achar_7zip(temporaria)
        pacote = baixar(URL, os.path.join(temporaria, "libreoffice.paf.exe"), SHA256)
        extraido = os.path.join(temporaria, "extraido")
        saida = subprocess.run([sete_zip, "x", "-y", f"-o{extraido}", pacote, "App/libreoffice/*", "-r"],
                               capture_output=True, text=True)
        origem = os.path.join(extraido, "App", "libreoffice")
        if saida.returncode != 0 or not os.path.isfile(os.path.join(origem, "program", "soffice.exe")):
            sys.exit(f"Não foi possível extrair o LibreOffice:\n{saida.stdout}\n{saida.stderr}")
        enxugar(origem)
        shutil.rmtree(DESTINO, ignore_errors=True)
        shutil.move(origem, DESTINO)

    testado = testar(DESTINO)
    tamanho = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DESTINO) for f in fs)
    print(f"LibreOffice {VERSAO} preparado — {tamanho / 2**20:.0f} MB em {DESTINO}")
    print("  Teste de conversão: " + ("OK" if testado else "NÃO EXECUTADO (só roda no Windows)"))


if __name__ == "__main__":
    main()
