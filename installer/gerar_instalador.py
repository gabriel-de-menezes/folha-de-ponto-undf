"""
Gera o instalador do DIGEP (installer/output/DIGEP_Folha_de_Ponto_Setup.exe) em um comando só:

  1. garante o executável em dist/ (compila com o PyInstaller se faltar, ou sempre com --recompilar);
  2. garante o Tesseract OCR em installer/Tesseract-OCR (baixa o oficial se faltar);
  3. compila installer/DIGEP_Setup.iss com o Inno Setup (instala-o pelo winget se faltar).

Só precisa do Python: não usa nenhuma biblioteca do projeto, a não ser com --recompilar.
No Windows, basta dar dois cliques em installer\\gerar_instalador.bat.

Uso:  python installer/gerar_instalador.py [--recompilar] [--docker]

  --recompilar   gera de novo o .exe a partir do código (só no Windows, com as dependências instaladas)
  --docker       compila o instalador com o Inno Setup de um contêiner Docker (para gerar no Linux/macOS)
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
SAIDA = os.path.join(AQUI, "output", "DIGEP_Folha_de_Ponto_Setup.exe")
IMAGEM_DOCKER = "amake/innosetup:innosetup6"


def rodar(comando, **opcoes):
    print(">", " ".join(comando))
    if subprocess.run(comando, **opcoes).returncode != 0:
        sys.exit(f"Falhou: {' '.join(comando)}")


def garantir_exe(recompilar):
    if recompilar or not os.path.isfile(EXE):
        if os.name != "nt":
            sys.exit("O .exe só pode ser compilado no Windows (PyInstaller não gera .exe a partir do Linux). "
                     "Use o dist/DIGEP_Folha_de_Ponto.exe do repositório ou rode este script no Windows.")
        rodar([sys.executable, "build_exe.py"], cwd=RAIZ)
    if not os.path.isfile(EXE):
        sys.exit(f"Executável não encontrado: {EXE}")


def garantir_tesseract():
    if os.path.isfile(os.path.join(TESSERACT, "tesseract.exe")):
        return
    rodar([sys.executable, os.path.join(AQUI, "preparar_tesseract.py"), "--baixar"])


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
    parser.add_argument("--recompilar", action="store_true", help="gera de novo o .exe a partir do código")
    parser.add_argument("--docker", action="store_true", help="compila com o Inno Setup de um contêiner Docker")
    opcoes = parser.parse_args()
    garantir_exe(opcoes.recompilar)
    garantir_tesseract()
    compilar(opcoes.docker)
    if not os.path.isfile(SAIDA):
        sys.exit(f"O Inno Setup terminou, mas o instalador não apareceu em {SAIDA}")
    print(f"\nInstalador pronto: {SAIDA} ({os.path.getsize(SAIDA) / 2**20:.0f} MB)")


if __name__ == "__main__":
    main()
