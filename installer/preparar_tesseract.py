"""
Copia o Tesseract OCR instalado neste computador para installer/Tesseract-OCR, que o instalador
(DIGEP_Setup.iss) leva junto. Assim o OCR funciona nos computadores da DIGEP sem instalar nada.

Leva só o necessário: tesseract.exe, as DLLs que ele usa e os idiomas por, eng e osd (orientação da página).
Um idioma que não esteja instalado neste computador (o instalador do Tesseract só traz o inglês por padrão)
é baixado do repositório oficial do Tesseract.

Uso:  python installer/preparar_tesseract.py [pasta_do_tesseract] [--instalar | --baixar]

  --instalar   se o Tesseract não estiver neste computador, instala-o antes pelo winget
  --baixar     não usa o Tesseract deste computador: baixa o instalador oficial e extrai os arquivos
               dele com o 7-Zip, sem instalar nada (funciona também no Linux)
"""
import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "Tesseract-OCR")
IDIOMAS = ("por", "eng", "osd")
URL_IDIOMA = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/{}.traineddata"
PACOTE_WINGET = "UB-Mannheim.TesseractOCR"
# Instalador oficial para Windows, publicado pelo projeto Tesseract (usado por --baixar).
URL_INSTALADOR = ("https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/"
                  "tesseract-ocr-w64-setup-5.5.3.20260724.exe")
SHA256_INSTALADOR = "bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4"


def pastas_candidatas(informada=None):
    if informada:
        yield informada
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        yield os.path.join(base, "Tesseract-OCR")
    yield os.path.expanduser(r"~\scoop\apps\tesseract\current")
    no_path = shutil.which("tesseract")
    if no_path:
        yield os.path.dirname(no_path)


def procurar_tesseract(informada=None):
    for pasta in pastas_candidatas(informada):
        if os.path.isfile(os.path.join(pasta, "tesseract.exe")) and glob.glob(os.path.join(pasta, "libtesseract*.dll")):
            return pasta
    return None


def achar_tesseract(informada=None, instalar=False):
    pasta = procurar_tesseract(informada)
    if pasta is None and instalar:
        if not shutil.which("winget"):
            sys.exit("O winget não está disponível neste computador. Instale o Tesseract manualmente: "
                     "https://github.com/UB-Mannheim/tesseract/wiki")
        print(f"Tesseract não encontrado: instalando {PACOTE_WINGET} pelo winget...")
        subprocess.run(["winget", "install", "--id", PACOTE_WINGET, "--exact", "--silent",
                        "--accept-package-agreements", "--accept-source-agreements"])
        pasta = procurar_tesseract(informada)
    if pasta is None:
        sys.exit("Tesseract não encontrado. Rode de novo com --instalar (instala pelo winget), instale-o "
                 "manualmente (https://github.com/UB-Mannheim/tesseract/wiki) ou informe a pasta: "
                 "python installer/preparar_tesseract.py <pasta>")
    return pasta


def achar_7zip():
    for nome in ("7z", "7zz", "7za"):
        if shutil.which(nome):
            return shutil.which(nome)
    for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        exe = os.path.join(base, "7-Zip", "7z.exe")
        if base and os.path.isfile(exe):
            return exe
    sys.exit("7-Zip não encontrado (necessário para --baixar). Instale-o: https://www.7-zip.org "
             "(no Linux: sudo apt install 7zip).")


def baixar_tesseract(pasta_temporaria):
    """Baixa o instalador oficial, confere o SHA-256 e extrai os arquivos, sem instalar. Devolve a pasta extraída."""
    sete_zip = achar_7zip()
    instalador = os.path.join(pasta_temporaria, "tesseract-setup.exe")
    print(f"Baixando o Tesseract de {URL_INSTALADOR}")
    try:
        with urllib.request.urlopen(URL_INSTALADOR, timeout=300) as resposta, open(instalador, "wb") as arquivo:
            shutil.copyfileobj(resposta, arquivo)
    except OSError as erro:
        sys.exit(f"Não foi possível baixar o Tesseract ({erro}).")
    with open(instalador, "rb") as arquivo:
        sha = hashlib.sha256(arquivo.read()).hexdigest()
    if sha != SHA256_INSTALADOR:
        sys.exit(f"O instalador do Tesseract baixado não confere (SHA-256 {sha}).")
    extraido = os.path.join(pasta_temporaria, "extraido")
    saida = subprocess.run([sete_zip, "x", "-y", f"-o{extraido}", instalador], capture_output=True, text=True)
    if saida.returncode != 0 or not procurar_tesseract(extraido):
        sys.exit(f"Não foi possível extrair o instalador do Tesseract:\n{saida.stdout}\n{saida.stderr}")
    return extraido


def achar_idiomas(pasta_tesseract):
    candidatas = [os.environ.get("TESSDATA_PREFIX", ""), os.path.join(pasta_tesseract, "tessdata"),
                  os.path.expanduser(r"~\scoop\apps\tesseract-languages\current")]
    sys.path.insert(0, os.path.dirname(AQUI))
    from folha_ponto.infraestrutura.leitor_folhas import _tessdata_do_registro
    candidatas.append(_tessdata_do_registro())
    achados = {}
    for idioma in IDIOMAS:
        arquivos = (os.path.join(pasta, f"{idioma}.traineddata") for pasta in filter(None, candidatas))
        achados[idioma] = next((a for a in arquivos if os.path.isfile(a)), None)  # None: será baixado
    return achados


def baixar_idioma(idioma, destino):
    url = URL_IDIOMA.format(idioma)
    print(f"Idioma '{idioma}' não está instalado neste computador: baixando de {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as resposta:
            dados = resposta.read()
    except OSError as erro:
        sys.exit(f"Não foi possível baixar o idioma '{idioma}' ({erro}). Baixe {url} manualmente e "
                 "coloque o arquivo na pasta tessdata do Tesseract.")
    if len(dados) < 100_000:  # página de erro no lugar do arquivo
        sys.exit(f"O arquivo baixado para o idioma '{idioma}' veio incompleto ({len(dados)} bytes).")
    with open(destino, "wb") as arquivo:
        arquivo.write(dados)


def dlls_necessarias(pasta):
    """DLLs da própria pasta que o tesseract.exe carrega, direta ou indiretamente (as das ferramentas de
    treinamento ficam de fora). Sem o pefile (vem com o PyInstaller), leva todas."""
    locais = {f.lower(): f for f in os.listdir(pasta) if f.lower().endswith(".dll")}
    try:
        import pefile
    except ImportError:
        return sorted(locais.values())
    vistas, fila = set(), ["tesseract.exe"]
    while fila:
        pe = pefile.PE(os.path.join(pasta, fila.pop()), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        for importada in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            nome = importada.dll.decode().lower()
            if nome in locais and nome not in vistas:
                vistas.add(nome)
                fila.append(locais[nome])
    return sorted(locais[n] for n in vistas)


def main():
    parser = argparse.ArgumentParser(description="Prepara o Tesseract OCR que o instalador do DIGEP leva junto.")
    parser.add_argument("pasta", nargs="?", help="pasta onde o Tesseract está instalado (opcional)")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--instalar", action="store_true",
                      help="instala o Tesseract pelo winget se ele não estiver neste computador")
    modo.add_argument("--baixar", action="store_true",
                      help="baixa o instalador oficial do Tesseract e extrai os arquivos, sem instalar nada")
    opcoes = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporaria:
        if opcoes.baixar:
            origem = baixar_tesseract(temporaria)
        else:
            origem = achar_tesseract(opcoes.pasta, opcoes.instalar)
        preparar(origem)


def testar_copia():
    """Roda a cópia isolada: sem PATH nem TESSDATA_PREFIX de outra instalação. Fora do Windows usa o Wine;
    devolve False se não houver como rodar o teste."""
    comando = [os.path.join(DESTINO, "tesseract.exe"), "--list-langs"]
    ambiente = {k: v for k, v in os.environ.items() if k.upper() != "TESSDATA_PREFIX"}
    if os.name == "nt":
        ambiente = {k: v for k, v in ambiente.items() if k.upper() != "PATH"}
        ambiente["PATH"] = os.environ.get("SystemRoot", r"C:\Windows") + r"\System32"
    elif shutil.which("wine"):
        comando.insert(0, shutil.which("wine"))
    else:
        return False
    saida = subprocess.run(comando, capture_output=True, text=True, env=ambiente, cwd=DESTINO)
    listados = set(saida.stdout.split()[-len(IDIOMAS):]) if saida.returncode == 0 else set()
    if listados != set(IDIOMAS):
        sys.exit(f"A cópia do Tesseract não funcionou sozinha:\n{saida.stdout}\n{saida.stderr}")
    return True


def preparar(origem):
    idiomas = achar_idiomas(origem)
    shutil.rmtree(DESTINO, ignore_errors=True)
    os.makedirs(os.path.join(DESTINO, "tessdata"))
    dlls = dlls_necessarias(origem)
    for nome in ["tesseract.exe", *dlls]:
        shutil.copy2(os.path.join(origem, nome), DESTINO)
    for idioma, arquivo in idiomas.items():
        destino = os.path.join(DESTINO, "tessdata", f"{idioma}.traineddata")
        if arquivo:
            shutil.copy2(arquivo, destino)
        else:
            baixar_idioma(idioma, destino)

    testado = testar_copia()

    tamanho = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DESTINO) for f in fs)
    print(f"Tesseract copiado de {origem}")
    print(f"  {len(dlls)} DLLs, idiomas {', '.join(IDIOMAS)} — {tamanho / 2**20:.0f} MB em {DESTINO}")
    if testado:
        print("  Teste isolado: OK (lê os idiomas sem depender da instalação deste computador)")
    else:
        print("  Teste isolado: NÃO EXECUTADO (sem Windows nem Wine para rodar o tesseract.exe)")


if __name__ == "__main__":
    main()
