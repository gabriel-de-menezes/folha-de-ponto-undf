
import subprocess
import sys
import os

def build():
    print("=== INICIANDO BUILD DO EXECUTAVEL (.EXE) VIA PYINSTALLER ===")

    # O PyInstaller só empacota o que está instalado: garante todas as bibliotecas nas versões do requirements.txt
    if subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"]).returncode != 0:
        print("\n[ERRO] Nao foi possivel instalar as dependencias do requirements.txt.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name=DIGEP_Folha_de_Ponto",
        "--add-data=recursos/Modelo de folha de ponto - Exemplo.docx;recursos",
        "--add-data=recursos/Planilha de professores - exemplo.xlsx;recursos",
        "--collect-data=customtkinter",
        "--collect-data=docx",
        "--hidden-import=pythoncom",
        "--hidden-import=win32com.client",
        "--collect-submodules=folha_ponto",
        "main.py"
    ]
    
    print("Executando comando:", " ".join(cmd))
    res = subprocess.run(cmd)
    
    if res.returncode == 0:
        exe_path = os.path.abspath(r"dist\DIGEP_Folha_de_Ponto.exe")
        print("\n=======================================================")
        print(f"[OK] BUILD CONCLUIDO COM SUCESSO!")
        print(f"Executavel gerado em: {exe_path}")
        print("=======================================================")
    else:
        print("\n[ERRO] ERRO DURANTE A COMPILACAO DO EXECUTAVEL.")
        sys.exit(1)

if __name__ == "__main__":
    build()
