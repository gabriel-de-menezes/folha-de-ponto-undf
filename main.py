"""Ponto de entrada: monta os serviços (raiz de composição) e abre a interface."""
import sqlite3

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


def main():
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
