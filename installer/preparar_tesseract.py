"""
Copia o Tesseract OCR instalado neste computador para installer/Tesseract-OCR, que o instalador
(DIGEP_Setup.iss) leva junto. Assim o OCR funciona nos computadores da DIGEP sem instalar nada.

Leva só o necessário: tesseract.exe, as DLLs que ele usa e os idiomas por, eng e osd (orientação da página).

Uso:  python installer/preparar_tesseract.py [pasta_do_tesseract]
"""
import glob
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "Tesseract-OCR")
IDIOMAS = ("por", "eng", "osd")


def pastas_candidatas():
    if len(sys.argv) > 1:
        yield sys.argv[1]
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        yield os.path.join(base, "Tesseract-OCR")
    yield os.path.expanduser(r"~\scoop\apps\tesseract\current")
    no_path = shutil.which("tesseract")
    if no_path:
        yield os.path.dirname(no_path)


def achar_tesseract():
    for pasta in pastas_candidatas():
        if os.path.isfile(os.path.join(pasta, "tesseract.exe")) and glob.glob(os.path.join(pasta, "libtesseract*.dll")):
            return pasta
    sys.exit("Tesseract não encontrado. Instale-o (https://github.com/UB-Mannheim/tesseract/wiki) "
             "ou informe a pasta: python installer/preparar_tesseract.py <pasta>")


def achar_idiomas(pasta_tesseract):
    candidatas = [os.environ.get("TESSDATA_PREFIX", ""), os.path.join(pasta_tesseract, "tessdata"),
                  os.path.expanduser(r"~\scoop\apps\tesseract-languages\current")]
    sys.path.insert(0, os.path.dirname(AQUI))
    from folha_ponto.infraestrutura.leitor_folhas import _tessdata_do_registro
    candidatas.append(_tessdata_do_registro())
    achados = {}
    for idioma in IDIOMAS:
        for pasta in filter(None, candidatas):
            arquivo = os.path.join(pasta, f"{idioma}.traineddata")
            if os.path.isfile(arquivo):
                achados[idioma] = arquivo
                break
        else:
            sys.exit(f"Idioma '{idioma}' não encontrado (procurado em: {', '.join(filter(None, candidatas))}).")
    return achados


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
    origem = achar_tesseract()
    idiomas = achar_idiomas(origem)
    shutil.rmtree(DESTINO, ignore_errors=True)
    os.makedirs(os.path.join(DESTINO, "tessdata"))
    dlls = dlls_necessarias(origem)
    for nome in ["tesseract.exe", *dlls]:
        shutil.copy2(os.path.join(origem, nome), DESTINO)
    for idioma, arquivo in idiomas.items():
        shutil.copy2(arquivo, os.path.join(DESTINO, "tessdata", f"{idioma}.traineddata"))

    # confere a cópia isolada: sem PATH nem TESSDATA_PREFIX de outra instalação
    ambiente = {k: v for k, v in os.environ.items() if k.upper() not in ("PATH", "TESSDATA_PREFIX")}
    ambiente["PATH"] = os.environ.get("SystemRoot", r"C:\Windows") + r"\System32"
    saida = subprocess.run([os.path.join(DESTINO, "tesseract.exe"), "--list-langs"], capture_output=True,
                           text=True, env=ambiente, cwd=DESTINO)
    listados = set(saida.stdout.split()[-len(IDIOMAS):]) if saida.returncode == 0 else set()
    if listados != set(IDIOMAS):
        sys.exit(f"A cópia do Tesseract não funcionou sozinha:\n{saida.stdout}\n{saida.stderr}")

    tamanho = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DESTINO) for f in fs)
    print(f"Tesseract copiado de {origem}")
    print(f"  {len(dlls)} DLLs, idiomas {', '.join(IDIOMAS)} — {tamanho / 2**20:.0f} MB em {DESTINO}")
    print("  Teste isolado: OK (lê os idiomas sem depender da instalação deste computador)")


if __name__ == "__main__":
    main()
