"""
Confere que tudo o que o instalador leva roda num Windows 10/11 recém-instalado: percorre os .exe/.dll/.pyd
do programa (inclusive os embutidos no .exe do PyInstaller), do Tesseract e do LibreOffice e lista toda DLL
importada que não esteja no próprio pacote nem faça parte do Windows.

Uma DLL de fora dessa lista (por exemplo, o runtime do Visual C++ ou do .NET) existiria na máquina de quem
compilou, mas não num Windows novo — e o programa não abriria lá.

Uso:  python installer/conferir_dependencias.py [pasta_instalada]
      (sem pasta: confere dist/DIGEP_Folha_de_Ponto.exe, installer/Tesseract-OCR e installer/LibreOffice)
Precisa do pefile e do PyInstaller (vêm com o requirements.txt).
"""
import os
import sys
import tempfile

import pefile
from PyInstaller.archive.readers import CArchiveReader

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
EXE = "DIGEP_Folha_de_Ponto.exe"
BINARIOS = (".exe", ".dll", ".pyd", ".bin", ".com")

# DLLs que fazem parte de toda instalação do Windows 10/11 (inclusive a Universal CRT, api-ms-win-*).
WINDOWS = {
    "advapi32", "authz", "bcrypt", "cabinet", "cfgmgr32", "clbcatq", "comctl32", "comdlg32", "credui",
    "crypt32", "cryptbase", "cryptnet", "cryptui", "d2d1", "d3d10", "d3d10_1", "d3d11", "d3d12", "d3d9",
    "d3dcompiler_47", "dbghelp", "dcomp", "dhcpcsvc", "dnsapi", "dwmapi", "dwrite", "dxgi", "esent",
    "fltlib", "gdi32", "gdiplus", "glu32", "hid", "httpapi", "imagehlp", "imm32", "iphlpapi", "kernel32",
    "kernelbase", "ktmw32", "mpr", "msacm32", "mscms", "msi", "msimg32", "msvcrt", "mswsock", "ncrypt",
    "netapi32", "normaliz", "ntdll", "ntdsapi", "odbc32", "ole32", "oleacc", "oleaut32", "oledlg",
    "opengl32", "pdh", "powrprof", "propsys", "psapi", "rasapi32", "rpcrt4", "rstrtmgr", "secur32",
    "setupapi", "shcore", "shell32", "shlwapi", "sspicli", "ucrtbase", "urlmon", "user32", "userenv",
    "usp10", "uxtheme", "version", "wer", "winhttp", "wininet", "winmm", "winspool.drv", "wintrust",
    "wldap32", "ws2_32", "wsock32", "wtsapi32", "xmllite", "comsvcs", "dsound", "dinput8", "msdmo",
    "mfplat", "mfplay", "mfreadwrite",  # Media Foundation: falta só nas edições "N" (ver README)
    "winhttp", "websocket", "windowscodecs", "wevtapi", "ntmarta", "sxs", "tdh", "virtdisk", "wsnmp32",
    "activeds",  # Active Directory Service Interfaces
    "fontsub",   # subconjunto de fontes (exportação PDF)
    "mscoree",   # carregador do .NET Framework 4.8, que é componente do Windows 10/11
}
# Binários empacotados que o DIGEP nunca carrega: o que eles importam não importa.
NAO_USADOS = {
    "win32ui.pyd",     # Pythonwin (IDE do pywin32); o DIGEP usa só win32com/pythoncom
    "officebean.dll",  # ponte Java do LibreOffice; a conversão para PDF não usa Java
}
EDICAO_N = {"mfplat", "mfplay", "mfreadwrite"}


def do_windows(nome):
    nome = nome.lower()
    base = nome[:-4] if nome.endswith(".dll") else nome
    return base in WINDOWS or nome.startswith(("api-ms-win-", "ext-ms-win-"))


def importacoes(caminho):
    try:
        pe = pefile.PE(caminho, fast_load=True)
    except pefile.PEFormatError:
        return set()
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                           pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
    nomes = {i.dll.decode(errors="replace").lower() for i in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])}
    nomes |= {i.dll.decode(errors="replace").lower() for i in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", [])}
    return nomes


def conferir_pasta(rotulo, pasta):
    """Confere os binários de uma pasta. Cada binário pode usar as DLLs da própria pasta e das pastas acima
    (o LibreOffice e o Tesseract carregam DLLs da pasta do executável)."""
    arquivos = [os.path.join(r, f) for r, _, fs in os.walk(pasta) for f in fs if f.lower().endswith(BINARIOS)]
    if not arquivos:
        return [f"{rotulo}: nenhum binário encontrado em {pasta}"]
    do_pacote = {os.path.basename(a).lower() for a in arquivos}
    faltando = {}
    for arquivo in arquivos:
        if os.path.basename(arquivo).lower() in NAO_USADOS:
            continue
        for dll in importacoes(arquivo):
            if dll not in do_pacote and not do_windows(dll):
                faltando.setdefault(dll, []).append(os.path.relpath(arquivo, pasta))
    print(f"{rotulo}: {len(arquivos)} binários conferidos")
    return [f"{rotulo}: {dll} (usada por {', '.join(sorted(usos)[:3])})" for dll, usos in sorted(faltando.items())]


def conferir_exe(caminho):
    """Extrai os binários embutidos pelo PyInstaller e confere como uma pasta."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
        arquivo = CArchiveReader(caminho)
        for nome in arquivo.toc:
            if nome.lower().endswith(BINARIOS):
                destino = os.path.join(pasta, nome.replace("\\", os.sep))
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with open(destino, "wb") as f:
                    f.write(arquivo.extract(nome))
        with open(os.path.join(pasta, EXE), "wb") as f, open(caminho, "rb") as original:
            f.write(original.read())
        return conferir_pasta("Programa (.exe)", pasta)


def main():
    if len(sys.argv) > 1:
        instalado = sys.argv[1]
        alvos = (os.path.join(instalado, EXE), os.path.join(instalado, "Tesseract-OCR"),
                 os.path.join(instalado, "LibreOffice"))
    else:
        alvos = (os.path.join(RAIZ, "dist", EXE), os.path.join(AQUI, "Tesseract-OCR"), os.path.join(AQUI, "LibreOffice"))
    problemas = conferir_exe(alvos[0]) + conferir_pasta("Tesseract", alvos[1]) + conferir_pasta("LibreOffice", alvos[2])
    if problemas:
        print("\nDLLs que não vêm no pacote nem no Windows (o programa falharia num Windows novo):")
        print("\n".join("  " + p for p in problemas))
        sys.exit(1)
    print(f"\nOK: tudo o que o instalador leva usa só DLLs do próprio pacote ou do Windows 10/11 "
          f"(Media Foundation — {', '.join(sorted(EDICAO_N))} — falta só nas edições \"N\").")


if __name__ == "__main__":
    main()
