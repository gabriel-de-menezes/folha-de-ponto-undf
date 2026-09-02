import subprocess
import sys
import os

def build():
    print("=== INICIANDO BUILD DO EXECUTAVEL (.EXE) VIA PYINSTALLER ===")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name=DIGEP_Folha_de_Ponto",
        "--add-data=Modelo de folha de ponto - Exemplo.docx;.",
        "--add-data=Planilha de professores - exemplo.xlsx;.",
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

if __name__ == "__main__":
    build()
