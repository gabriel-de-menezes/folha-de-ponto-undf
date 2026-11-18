"""
Simula, num Windows comum, uma edição "N" (sem Media Foundation) para o LibreOffice instalado: coloca as DLLs
substitutas (gerar_media_foundation.py) na pasta dele e confere que

  1. o Windows carrega a substituta, e não o mfplat.dll do sistema, quando o LibreOffice abre;
  2. as funções respondem E_NOTIMPL;
  3. o LibreOffice converte a folha de ponto em PDF usando só as substitutas.

No fim tira as substitutas (a não ser que já estivessem lá, como numa edição "N" de verdade).
Só roda no Windows.  Uso:  python installer/testar_media_foundation.py <pasta_instalada_do_DIGEP>
"""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from gerar_media_foundation import E_NOTIMPL, EXPORTACOES, gerar  # noqa: E402

MODELO = os.path.join(os.path.dirname(AQUI), "recursos", "Modelo de folha de ponto - Exemplo.docx")


def carregar_mergedlo(programa):
    """Roda num processo à parte (a DLL carregada não pode ser apagada depois): abre o mergedlo.dll como o
    LibreOffice abre — procurando as dependências primeiro na pasta dele — e mostra de onde veio cada mf*.dll."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LoadLibraryExW.restype = ctypes.c_void_p
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    kernel32.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    os.add_dll_directory(programa)
    if not kernel32.LoadLibraryExW(os.path.join(programa, "mergedlo.dll"), None, 0x8):  # ALTERED_SEARCH_PATH
        sys.exit(f"mergedlo.dll não carregou (erro {ctypes.get_last_error()})")
    for nome in EXPORTACOES:
        modulo = kernel32.GetModuleHandleW(nome)
        caminho = ctypes.create_unicode_buffer(1024)
        kernel32.GetModuleFileNameW(modulo, caminho, 1024)
        print(f"{nome}={caminho.value}")


def main():
    if os.name != "nt":
        sys.exit("Este teste só roda no Windows.")
    if len(sys.argv) > 2 and sys.argv[1] == "--carregar":
        carregar_mergedlo(sys.argv[2])
        return
    programa = os.path.join(sys.argv[1], "LibreOffice", "program")
    ja_havia = all(os.path.exists(os.path.join(programa, n)) for n in EXPORTACOES)
    colocadas = [] if ja_havia else gerar(programa)
    try:
        # 1. a substituta é a que carrega
        saida = subprocess.run([sys.executable, os.path.abspath(__file__), "--carregar", programa],
                               capture_output=True, text=True, timeout=120)
        print(saida.stdout, saida.stderr)
        carregadas = dict(linha.split("=", 1) for linha in saida.stdout.splitlines() if "=" in linha)
        for nome in EXPORTACOES:
            esperado = os.path.normcase(os.path.join(programa, nome))
            if os.path.normcase(carregadas.get(nome, "")) != esperado:
                sys.exit(f"{nome}: o LibreOffice carregou '{carregadas.get(nome)}', e não a substituta {esperado}")

        # 2. as funções respondem E_NOTIMPL
        for nome, funcoes in EXPORTACOES.items():
            dll = ctypes.WinDLL(os.path.join(programa, nome))
            for funcao in funcoes:
                resposta = getattr(dll, funcao)() & 0xFFFFFFFF
                if resposta != E_NOTIMPL:
                    sys.exit(f"{nome}!{funcao} respondeu {resposta:#x}, esperado E_NOTIMPL")
            del dll

        # 3. o LibreOffice converte a folha com as substitutas
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
            docx = os.path.join(pasta, "folha.docx")
            shutil.copy2(MODELO, docx)
            perfil = Path(pasta, "perfil").as_uri()
            subprocess.run([os.path.join(programa, "soffice.exe"), f"-env:UserInstallation={perfil}", "--headless",
                            "--norestore", "--convert-to", "pdf", "--outdir", pasta, docx],
                           capture_output=True, text=True, timeout=300)
            pdf = os.path.join(pasta, "folha.pdf")
            if not os.path.isfile(pdf) or os.path.getsize(pdf) < 1000:
                sys.exit("O LibreOffice não converteu a folha em PDF com as substitutas do Media Foundation")
            print(f"PDF gerado com as substitutas: {os.path.getsize(pdf)} bytes")
        print('OK: sem Media Foundation (edição "N"), o LibreOffice abre com as substitutas e gera o PDF.')
    finally:
        for caminho in colocadas:
            try:
                os.remove(caminho)
            except OSError:
                pass


if __name__ == "__main__":
    main()
