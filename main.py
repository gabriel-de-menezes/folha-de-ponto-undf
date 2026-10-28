"""Ponto de entrada: monta os serviços (raiz de composição) e abre a interface."""
import os
import sqlite3
import sys

from folha_ponto.infraestrutura.armazenamento import pasta_padrao_app
from folha_ponto.infraestrutura.container import montar_servicos
from folha_ponto.interface.app import AppDIGEP


def mensagem_falha_ao_abrir(erro, pasta):
    """Texto para o usuário quando o sistema não consegue abrir (no .exe não há console para mostrar o erro)."""
    if isinstance(erro, (PermissionError, sqlite3.OperationalError)):
        return (f"O DIGEP não tem permissão para gravar na pasta onde está instalado:\n\n{pasta}\n\n"
                "O banco de dados e as folhas ficam nessa pasta. Peça à equipe de TI permissão de escrita nela, "
                "ou reinstale o DIGEP escolhendo “Instalar somente para mim”.")
    return f"O DIGEP não conseguiu abrir.\n\nPasta do sistema: {pasta}\nErro: {erro}"


def verificar(argumentos):
    """--verificar [arquivo] [--silencioso]: testa as dependências e grava o relatório (padrão: verificacao.txt
    na pasta do sistema). Sai com código 1 se algo obrigatório falhar."""
    from folha_ponto.infraestrutura.verificacao import relatorio, verificar_instalacao
    resultados = verificar_instalacao()
    texto = relatorio(resultados)
    extras = [a for a in argumentos if not a.startswith("--")]
    destino = extras[0] if extras else os.path.join(pasta_padrao_app(), "verificacao.txt")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    if "--silencioso" not in argumentos:
        import tkinter as tk
        from tkinter import messagebox
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showinfo("DIGEP — Verificação da instalação", texto.split("\n\n---")[0], parent=raiz)
        raiz.destroy()
    raise SystemExit(1 if any(r[0] == "FALHA" for r in resultados) else 0)


def main():
    if "--verificar" in sys.argv:
        verificar(sys.argv[sys.argv.index("--verificar") + 1:])
    try:
        app = AppDIGEP(montar_servicos())
    except Exception as erro:
        import tkinter as tk
        from tkinter import messagebox
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("DIGEP — Folhas de Ponto", mensagem_falha_ao_abrir(erro, pasta_padrao_app()), parent=raiz)
        raiz.destroy()
        raise SystemExit(1)
    app.mainloop()


if __name__ == "__main__":
    main()
