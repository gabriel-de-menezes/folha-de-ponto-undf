import customtkinter as ctk


class Pagina(ctk.CTkFrame):
    nav = None  # item do menu lateral destacado quando a página está aberta

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.servicos = app.servicos

    def atualizar(self):
        """Recarrega os dados da tela (chamado sempre que ela é exibida)."""
