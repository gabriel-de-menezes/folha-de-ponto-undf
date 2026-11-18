"""
Gera o instalador do DIGEP (installer/output/DIGEP_Folha_de_Ponto_Setup.exe) em um comando só. O instalador
leva tudo o que o sistema usa, para funcionar num Windows recém-instalado (sem Python, Office nem internet):

  1. compila o executável a partir do código atual (no Windows), num ambiente Python próprio
     (installer/.venv-build) com as bibliotecas do requirements.txt;
  2. garante o Tesseract OCR em installer/Tesseract-OCR (baixa o oficial se faltar);
  3. garante o LibreOffice portátil em installer/LibreOffice (baixa o oficial se faltar): converte as folhas
     em PDF quando o computador não tem Microsoft Word;
  4. compila installer/DIGEP_Setup.iss com o Inno Setup (instala-o pelo winget se faltar).

Precisa só do Python 3.11+ e de internet. No Windows, basta dar dois cliques em installer\\gerar_instalador.bat.

Uso:  python installer/gerar_instalador.py [--sem-recompilar] [--docker]

  --sem-recompilar  usa o dist/DIGEP_Folha_de_Ponto.exe já existente (fora do Windows é sempre assim)
  --docker          compila o instalador com o Inno Setup de um contêiner Docker (para gerar no Linux/macOS)
"""
import argparse
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
EXE = os.path.join(RAIZ, "dist", "DIGEP_Folha_de_Ponto.exe")
TESSERACT = os.path.join(AQUI, "Tesseract-OCR")
LIBREOFFICE = os.path.join(AQUI, "LibreOffice", "program", "soffice.exe")
VENV = os.path.join(AQUI, ".venv-build")
SAIDA = os.path.join(AQUI, "output", "DIGEP_Folha_de_Ponto_Setup.exe")
IMAGEM_DOCKER = "amake/innosetup:innosetup6"


def rodar(comando, **opcoes):
    print(">", " ".join(comando))
    if subprocess.run(comando, **opcoes).returncode != 0:
        sys.exit(f"Falhou: {' '.join(comando)}")


def python_de_build():
    """Ambiente Python só para compilar o .exe: não depende do que estiver instalado no Python do computador."""
    python = os.path.join(VENV, "Scripts", "python.exe")
    if not os.path.isfile(python):
        rodar([sys.executable, "-m", "venv", VENV])
        rodar([python, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    return python


def garantir_exe(recompilar):
    if os.name != "nt":
        recompilar = False  # o PyInstaller não gera .exe a partir do Linux/macOS
        print("Fora do Windows: usando o dist/DIGEP_Folha_de_Ponto.exe do repositório, sem recompilar.")
    if recompilar:
        rodar([python_de_build(), "build_exe.py"], cwd=RAIZ)
    if not os.path.isfile(EXE):
        sys.exit(f"Executável não encontrado: {EXE}")


def garantir_tesseract():
    if os.path.isfile(os.path.join(TESSERACT, "tesseract.exe")):
        return
    rodar([sys.executable, os.path.join(AQUI, "preparar_tesseract.py"), "--baixar"])


def garantir_libreoffice():
    if os.path.isfile(LIBREOFFICE):
        return
    rodar([sys.executable, os.path.join(AQUI, "preparar_libreoffice.py")])


def achar_iscc():
    for nome in ("ISCC", "iscc"):
        if shutil.which(nome):
            return shutil.which(nome)
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        exe = os.path.join(base, "Inno Setup 6", "ISCC.exe")
        if os.path.isfile(exe):
            return exe
    return None


def compilar(docker):
    if docker:
        rodar(["docker", "run", "--rm", "-v", f"{RAIZ}:/work", IMAGEM_DOCKER, "installer/DIGEP_Setup.iss"])
        return
    iscc = achar_iscc()
    if not iscc and os.name == "nt" and shutil.which("winget"):
        print("Inno Setup não encontrado: instalando pelo winget...")
        subprocess.run(["winget", "install", "--id", "JRSoftware.InnoSetup", "--exact", "--silent",
                        "--accept-package-agreements", "--accept-source-agreements"])
        iscc = achar_iscc()
    if not iscc:
        sys.exit("Inno Setup não encontrado. No Windows, instale-o (https://jrsoftware.org/isdl.php) e rode de novo. "
                 "No Linux/macOS: rode de novo com --docker.")
    rodar([iscc, os.path.join(AQUI, "DIGEP_Setup.iss")])


def main():
    parser = argparse.ArgumentParser(description="Gera o instalador do DIGEP.")
    parser.add_argument("--sem-recompilar", action="store_true", help="usa o dist/DIGEP_Folha_de_Ponto.exe existente")
    parser.add_argument("--recompilar", action="store_true", help=argparse.SUPPRESS)  # padrão; mantido por compatibilidade
    parser.add_argument("--docker", action="store_true", help="compila com o Inno Setup de um contêiner Docker")
    opcoes = parser.parse_args()
    garantir_exe(not opcoes.sem_recompilar)
    garantir_tesseract()
    garantir_libreoffice()
    compilar(opcoes.docker)
    if not os.path.isfile(SAIDA):
        sys.exit(f"O Inno Setup terminou, mas o instalador não apareceu em {SAIDA}")
    print(f"\nInstalador pronto: {SAIDA} ({os.path.getsize(SAIDA) / 2**20:.0f} MB)")


if __name__ == "__main__":
    main()
