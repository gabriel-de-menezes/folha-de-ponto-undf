import customtkinter as ctk

from ...dominio.entidades import ConfiguracaoEmail
from .. import tema as T
from ..utilitarios import abrir_pasta
from .base import Pagina

APARENCIAS = {"System": "Sistema", "Light": "Claro", "Dark": "Escuro"}


class PaginaConfiguracoes(Pagina):
    nav = "config"

    CAMPOS_SMTP = [("host", "Servidor (host)", False), ("porta", "Porta", False), ("usuario", "Usuário / e-mail", False),
                   ("senha", "Senha de aplicativo", True), ("remetente_nome", "Nome do remetente", False)]

    def __init__(self, master, app):
        super().__init__(master, app)
        T.titulo_pagina(self, "Configurações", "Ficam salvas apenas neste computador.").pack(fill="x", pady=(0, 12))
        rolagem = ctk.CTkScrollableFrame(self, fg_color="transparent")
        rolagem.pack(fill="both", expand=True)
        cfg = self.servicos.configuracoes.email()
        armazenamento = self.servicos.armazenamento

        # ---- E-mail ----
        card = T.cartao(rolagem)
        card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card, text="Envio de e-mail", font=T.fonte(16, True)).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(card, text="Escolha como os e-mails serão enviados aos servidores.", font=T.fonte(12),
                     text_color=T.SUAVE).pack(anchor="w", padx=20)
        self.seg_metodo = ctk.CTkSegmentedButton(card, values=list(ConfiguracaoEmail.METODOS.values()),
                                                 command=self._trocar_metodo, selected_color=T.PRIMARIA,
                                                 selected_hover_color=T.PRIMARIA_HOVER, height=34, font=T.fonte(13))
        self.seg_metodo.pack(anchor="w", padx=20, pady=12)

        self.frames, self.campos = {}, {}
        f = ctk.CTkFrame(card, fg_color="transparent")
        f.grid_columnconfigure(1, weight=1)
        for linha, (chave, rotulo, secreto) in enumerate(self.CAMPOS_SMTP):
            ctk.CTkLabel(f, text=rotulo, font=T.fonte(12), text_color=T.SUAVE).grid(row=linha, column=0, padx=(20, 12), pady=5, sticky="w")
            e = T.entrada(f, show="•" if secreto else "")
            e.insert(0, getattr(cfg, chave))
            e.grid(row=linha, column=1, padx=(0, 20), pady=5, sticky="ew")
            self.campos[chave] = e
        self.var_tls = ctk.BooleanVar(value=cfg.usar_tls)
        ctk.CTkCheckBox(f, text="Usar STARTTLS (porta 587)", variable=self.var_tls, font=T.fonte(12),
                        fg_color=T.PRIMARIA).grid(row=5, column=1, padx=(0, 20), pady=5, sticky="w")
        ctk.CTkLabel(f, text="Gmail: smtp.gmail.com · porta 587 · STARTTLS · usuário = seu e-mail · senha = senha de app "
                             "(Conta Google → Segurança → Verificação em duas etapas → Senhas de app).\n"
                             "Office 365 / Outlook.com: smtp.office365.com · porta 587 · STARTTLS.\n"
                             "Servidor institucional: peça host, porta e credenciais à equipe de TI.",
                     font=T.fonte(12), text_color=T.SUAVE, justify="left", wraplength=820).grid(
            row=6, column=0, columnspan=2, padx=20, pady=(8, 0), sticky="w")
        self.frames["SMTP"] = f

        f2 = ctk.CTkFrame(card, fg_color="transparent")
        ctk.CTkLabel(f2, text="Usa o Microsoft Outlook instalado e configurado neste computador. Os e-mails saem da conta "
                              "padrão do Outlook e ficam em “Itens enviados”.", font=T.fonte(12), text_color=T.SUAVE,
                     justify="left", wraplength=820).pack(anchor="w", padx=20)
        self.frames["Outlook"] = f2

        self._rodape_email = ctk.CTkFrame(card, fg_color="transparent")
        self._rodape_email.pack(fill="x", padx=20, pady=16, side="bottom")
        T.botao_primario(self._rodape_email, "Salvar", self.salvar, width=120).pack(side="right")
        T.botao_secundario(self._rodape_email, "Testar conexão", self.testar, width=140).pack(side="right", padx=8)
        self.lbl_status = ctk.CTkLabel(self._rodape_email, text="", font=T.fonte(12), wraplength=480, justify="left")
        self.lbl_status.pack(side="left")

        self.seg_metodo.set(ConfiguracaoEmail.METODOS[cfg.metodo])
        self._trocar_metodo(self.seg_metodo.get())

        # ---- Aparência ----
        card2 = T.cartao(rolagem)
        card2.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card2, text="Aparência", font=T.fonte(16, True)).pack(anchor="w", padx=20, pady=(16, 8))
        self.seg_tema = ctk.CTkSegmentedButton(card2, values=list(APARENCIAS.values()), command=self._mudar_aparencia,
                                               selected_color=T.PRIMARIA, selected_hover_color=T.PRIMARIA_HOVER, height=34)
        self.seg_tema.set(APARENCIAS.get(self.servicos.configuracoes.aparencia(), "Sistema"))
        self.seg_tema.pack(anchor="w", padx=20, pady=(0, 16))

        # ---- Arquivos ----
        card3 = T.cartao(rolagem)
        card3.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card3, text="Arquivos", font=T.fonte(16, True)).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(card3, text=f"Modelo da folha: {armazenamento.modelo_folha}\nPasta de dados: {armazenamento.pasta_app}",
                     font=T.fonte(12), text_color=T.SUAVE, justify="left", anchor="w", wraplength=820).pack(anchor="w", fill="x", padx=20)
        T.link(card3, "Abrir pasta de dados", lambda: abrir_pasta(armazenamento.pasta_app)).pack(anchor="w", padx=14, pady=(4, 16))

    def _mudar_aparencia(self, rotulo):
        modo = {v: k for k, v in APARENCIAS.items()}[rotulo]
        self.servicos.configuracoes.definir_aparencia(modo)
        self.app.aplicar_aparencia(modo)

    def _metodo(self):
        return {v: k for k, v in ConfiguracaoEmail.METODOS.items()}[self.seg_metodo.get()]

    def _trocar_metodo(self, _valor):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[self._metodo()].pack(fill="x", before=self._rodape_email)
        self.lbl_status.configure(text="")

    def _config_do_formulario(self):
        valores = {k: (e.get() if k == "senha" else e.get().strip()) for k, e in self.campos.items()}
        valores["porta"] = valores["porta"] or "587"
        return ConfiguracaoEmail(metodo=self._metodo(), usar_tls=self.var_tls.get(), **valores)

    def salvar(self):
        self.servicos.configuracoes.salvar_email(self._config_do_formulario())
        self.lbl_status.configure(text="✓ Configuração salva.", text_color=T.SUCESSO)
        self.app.notificar("Configuração de e-mail salva.")

    def testar(self):
        cfg = self._config_do_formulario()
        self.lbl_status.configure(text="Testando…", text_color=T.SUAVE)

        def fim(resultado):
            ok, msg = resultado
            self.lbl_status.configure(text=("✓ " if ok else "✕ ") + msg, text_color=T.SUCESSO if ok else T.PERIGO)

        self.app.executar_tarefa("Testando conexão…", lambda p: self.servicos.configuracoes.testar_email(cfg), fim)
