"""Janela principal: menu lateral, navegação entre páginas, notificações e tarefas em segundo plano."""
import queue
import threading
import traceback
from tkinter import messagebox

import customtkinter as ctk

from ..dominio.regras import ErroDominio
from . import tema as T
from .fluxos.assinadas import FluxoAssinadas
from .fluxos.gerar import FluxoGerar
from .paginas.arquivo import PaginaArquivo
from .paginas.auditoria import PaginaAuditoria
from .paginas.configuracoes import PaginaConfiguracoes
from .paginas.inicio import PaginaInicio
from .paginas.servidores import PaginaServidores
from .utilitarios import abrir_arquivo

PAGINAS = dict(inicio=PaginaInicio, servidores=PaginaServidores, arquivo=PaginaArquivo, auditoria=PaginaAuditoria,
               config=PaginaConfiguracoes, fluxo_gerar=FluxoGerar, fluxo_assinadas=FluxoAssinadas)
MENU = [("inicio", "⌂   Início"), ("servidores", "👥  Servidores"), ("arquivo", "🗂  Arquivo de folhas"),
        ("auditoria", "🛡  Auditoria")]
FLUXOS = ("fluxo_gerar", "fluxo_assinadas")


class AppDIGEP(ctk.CTk):
    def __init__(self, servicos):
        self.servicos = servicos
        ctk.set_appearance_mode(servicos.configuracoes.aparencia())
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("DIGEP — Folhas de Ponto (UnDF)")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=T.FUNDO)

        self.tabelas = []
        self.cores_tabela = T.aplicar_estilo_tabelas()
        self._modo_atual = ctk.get_appearance_mode()
        self._tarefa_ativa = False
        self._after_notificacao = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._montar_menu_lateral()
        self._montar_area_principal()
        self.paginas = {chave: classe(self.container, self) for chave, classe in PAGINAS.items()}
        self.pagina_atual = None
        self.mostrar("inicio")
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.after(2000, self._verificar_aparencia)

    # ---------- layout ----------
    def _montar_menu_lateral(self):
        lateral = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=T.MENU_FUNDO)
        lateral.grid(row=0, column=0, sticky="nsw")
        lateral.grid_propagate(False)
        lateral.pack_propagate(False)
        ctk.CTkLabel(lateral, text="DIGEP", font=T.fonte(26, True), text_color="#FFFFFF").pack(anchor="w", padx=24, pady=(28, 0))
        ctk.CTkLabel(lateral, text="Folhas de Ponto · UnDF", font=T.fonte(12), text_color="#94A3B8").pack(anchor="w", padx=24, pady=(0, 28))
        self.botoes_nav = {}
        for chave, rotulo in MENU:
            self.botoes_nav[chave] = self._botao_nav(lateral, rotulo, chave)
            self.botoes_nav[chave].pack(fill="x", padx=12, pady=2)
        self.botoes_nav["config"] = self._botao_nav(lateral, "⚙   Configurações", "config")
        self.botoes_nav["config"].pack(fill="x", padx=12, pady=(2, 20), side="bottom")

    def _botao_nav(self, master, rotulo, chave):
        return ctk.CTkButton(master, text=rotulo, anchor="w", height=42, corner_radius=8, font=T.fonte(14),
                             fg_color="transparent", hover_color=T.MENU_HOVER, text_color="#E2E8F0",
                             command=lambda: self.mostrar(chave))

    def _montar_area_principal(self):
        principal = ctk.CTkFrame(self, fg_color="transparent")
        principal.grid(row=0, column=1, sticky="nsew")
        principal.grid_rowconfigure(0, weight=1)
        principal.grid_columnconfigure(0, weight=1)
        self.container = ctk.CTkFrame(principal, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew", padx=28, pady=(24, 8))
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        # Barra de status: mensagens e progresso das tarefas em segundo plano
        status = ctk.CTkFrame(principal, height=38, corner_radius=0, fg_color=T.CARTAO, border_width=0)
        status.grid(row=1, column=0, sticky="ew")
        self.lbl_status = ctk.CTkLabel(status, text="", font=T.fonte(12), anchor="w")
        self.lbl_status.pack(side="left", padx=28, pady=6)
        self.barra_progresso = ctk.CTkProgressBar(status, width=260, height=8, progress_color=T.PRIMARIA)
        self.lbl_progresso = ctk.CTkLabel(status, text="", font=T.fonte(12), text_color=T.SUAVE)

    # ---------- navegação ----------
    def mostrar(self, chave):
        if self._tarefa_ativa:
            self.notificar("Aguarde a tarefa atual terminar.", "aviso")
            return
        pagina = self.paginas[chave]
        for k, botao in self.botoes_nav.items():
            botao.configure(fg_color=T.MENU_ATIVO if k == pagina.nav else "transparent")
        if self.pagina_atual is not None:
            self.pagina_atual.grid_forget()
        self.pagina_atual = pagina
        pagina.grid(row=0, column=0, sticky="nsew")
        self.atualizar_pagina()

    def atualizar_pagina(self):
        if self.pagina_atual is not None:
            try:
                self.pagina_atual.atualizar()
            except Exception as e:
                traceback.print_exc()
                self.notificar(f"Erro ao atualizar a tela: {e}", "erro")

    def iniciar_fluxo(self, chave):
        self.paginas[chave].iniciar()
        self.mostrar(chave)

    def abrir_relatorio(self, op_id, regerar=False):
        try:
            abrir_arquivo(self.servicos.auditoria.relatorio(op_id, regerar))
        except Exception as e:
            messagebox.showerror("Relatório", f"Não foi possível gerar o relatório:\n{e}")

    def _fechar(self):
        if self._tarefa_ativa and not messagebox.askyesno("Sair", "Há uma tarefa em andamento. Sair mesmo assim?"):
            return
        for chave in FLUXOS:
            self.paginas[chave].encerrar_se_aberto("Interrompida (aplicativo fechado)")
        self.destroy()

    # ---------- aparência ----------
    def aplicar_aparencia(self, modo):
        ctk.set_appearance_mode(modo)
        self._reestilizar_tabelas()

    def _reestilizar_tabelas(self):
        self._modo_atual = ctk.get_appearance_mode()
        self.cores_tabela = T.aplicar_estilo_tabelas()
        for t in self.tabelas:
            t.aplicar_cores(self.cores_tabela)

    def _verificar_aparencia(self):
        # Acompanha mudanças do tema do Windows quando o modo é "Sistema"
        if ctk.get_appearance_mode() != self._modo_atual:
            self._reestilizar_tabelas()
        self.after(2000, self._verificar_aparencia)

    # ---------- feedback ----------
    def notificar(self, texto, tipo="ok"):
        cor = {"ok": T.SUCESSO, "aviso": T.AVISO, "erro": T.PERIGO}.get(tipo, T.TEXTO)
        icone = {"ok": "✓", "aviso": "⚠", "erro": "✕"}.get(tipo, "")
        self.lbl_status.configure(text=f"{icone}  {texto}", text_color=cor)
        if self._after_notificacao:
            self.after_cancel(self._after_notificacao)
        self._after_notificacao = self.after(10000, lambda: self.lbl_status.configure(text=""))

    def executar_tarefa(self, descricao, trabalho, ao_concluir):
        """Roda trabalho(progresso) numa thread para a janela não travar. progresso(i, total, texto) atualiza a
        barra de status; ao_concluir(resultado) roda de volta na thread da interface. Erros de regra de negócio
        (ErroDominio) viram um aviso com a mensagem; os demais, uma mensagem de erro inesperado."""
        if self._tarefa_ativa:
            self.notificar("Aguarde a tarefa atual terminar.", "aviso")
            return
        self._tarefa_ativa = True
        fila = queue.Queue()
        self.lbl_status.configure(text="")
        self.lbl_progresso.configure(text=descricao)
        self.lbl_progresso.pack(side="right", padx=(0, 28))
        self.barra_progresso.pack(side="right", padx=(0, 12))
        self.barra_progresso.set(0)
        self.configure(cursor="watch")

        def alvo():
            try:
                fila.put(("ok", trabalho(lambda i, total, texto="": fila.put(("progresso", i, total, texto)))))
            except Exception as e:
                if not isinstance(e, ErroDominio):
                    traceback.print_exc()
                fila.put(("erro", e))

        def acompanhar():
            try:
                while True:
                    msg = fila.get_nowait()
                    if msg[0] == "progresso":
                        _, i, total, texto = msg
                        self.barra_progresso.set(i / total if total else 0)
                        self.lbl_progresso.configure(text=f"{texto}  ({min(i + 1, total)}/{total})" if total else texto)
                        continue
                    self._tarefa_ativa = False
                    self.configure(cursor="")
                    self.barra_progresso.pack_forget()
                    self.lbl_progresso.pack_forget()
                    if msg[0] == "erro":
                        erro = msg[1]
                        if isinstance(erro, ErroDominio):
                            messagebox.showwarning(descricao, str(erro))
                        else:
                            messagebox.showerror("Erro", f"{descricao}\n\nOcorreu um erro inesperado:\n{erro}")
                    else:
                        try:
                            ao_concluir(msg[1])
                        except Exception as e:
                            traceback.print_exc()
                            messagebox.showerror("Erro", str(e))
                    return
            except queue.Empty:
                pass
            self.after(100, acompanhar)

        threading.Thread(target=alvo, daemon=True).start()
        acompanhar()
