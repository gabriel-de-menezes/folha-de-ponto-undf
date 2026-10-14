import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...dominio.regras import ErroDominio
from .. import tema as T
from ..componentes import DialogoDataEspecial, Tabela
from ..utilitarios import TIPOS_PLANILHA
from .base import Pagina

TODOS = "Todos os anos"
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


class PaginaCalendario(Pagina):
    nav = "calendario"

    def __init__(self, master, app):
        super().__init__(master, app)
        cab = T.titulo_pagina(self, "Calendário acadêmico",
                              "Feriados, recessos e pontos facultativos inseridos automaticamente nas folhas geradas.")
        cab.pack(fill="x", pady=(0, 12))
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))
        self.opt_ano = ctk.CTkOptionMenu(barra, values=[TODOS], command=lambda v: self.atualizar(), height=36, width=160,
                                         fg_color=T.PRIMARIA, button_color=T.PRIMARIA_HOVER)
        self.opt_ano.pack(side="left")
        T.botao_secundario(barra, "Remover selecionada", self.remover, width=170).pack(side="right")
        T.botao_secundario(barra, "Importar planilha…", self.importar, width=170).pack(side="right", padx=8)
        T.botao_primario(barra, "＋ Nova data", lambda: DialogoDataEspecial(app, None, self.atualizar), width=140).pack(side="right")
        self.tabela = Tabela(self, app, [
            ("data", "Data", 120, "center"), ("dia", "Dia da semana", 140, "center"), ("esp", "Especificação", 560),
        ], altura=12, ao_duplo_clique=self._editar, menu=lambda i: [("Editar…", self._editar),
                                                                   ("Remover…", lambda x: self.remover(x))])
        self.tabela.pack(fill="both", expand=True)
        ctk.CTkLabel(self, text="A planilha deve ter as colunas “Data” e “Especificação”. Datas já cadastradas são "
                                "atualizadas. Dois cliques em uma linha para editar.",
                     font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w", pady=(6, 0))
        self._datas = {}

    def atualizar(self):
        anos = [str(a) for a in self.servicos.calendario.anos()]
        self.opt_ano.configure(values=[TODOS] + anos)
        if self.opt_ano.get() not in [TODOS] + anos:
            self.opt_ano.set(TODOS)
        ano = None if self.opt_ano.get() == TODOS else int(self.opt_ano.get())
        datas = self.servicos.calendario.listar(ano)
        self._datas = {d.data.isoformat(): d for d in datas}
        self.tabela.preencher([(d.data.isoformat(), (d.data_br, DIAS[d.data.weekday()], d.especificacao), None)
                               for d in datas], "Nenhuma data cadastrada. Importe a planilha do calendário ou use “Nova data”.")

    def importar(self):
        caminho = filedialog.askopenfilename(title="Selecione a planilha do calendário acadêmico", filetypes=TIPOS_PLANILHA)
        if not caminho:
            return
        try:
            resumo = self.servicos.calendario.analisar_planilha(caminho)
        except ErroDominio as e:
            messagebox.showwarning("Planilha rejeitada", str(e))
            return
        detalhes = "\n\nIgnorados:\n• " + "\n• ".join(resumo.ignoradas[:8]) if resumo.ignoradas else ""
        if not messagebox.askyesno(
                "Confirmar importação",
                f"Resumo da planilha “{os.path.basename(caminho)}”:\n\n• {resumo.novos} nova(s) data(s)\n"
                f"• {resumo.atualizados} atualizada(s)\n• {resumo.sem_alteracao} sem alteração\n"
                f"• {len(resumo.ignoradas)} ignorada(s){detalhes}\n\nConfirmar a gravação?"):
            return
        self.servicos.calendario.confirmar_importacao(resumo)
        self.app.notificar(f"Calendário atualizado. {resumo.mensagem}")
        self.atualizar()

    def _editar(self, iid):
        if iid in self._datas:
            DialogoDataEspecial(self.app, self._datas[iid], self.atualizar)

    def remover(self, iid=None):
        iid = iid or self.tabela.selecionado()
        d = self._datas.get(iid)
        if not d:
            messagebox.showinfo("Remover data", "Selecione uma data na lista.")
            return
        if messagebox.askyesno("Remover data", f"Remover {d.data_br} — {d.especificacao}?"):
            self.servicos.calendario.remover(d.data)
            self.atualizar()
