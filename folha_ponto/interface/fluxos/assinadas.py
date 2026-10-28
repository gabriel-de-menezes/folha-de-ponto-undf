"""Fluxo 2: importar folhas assinadas (PDF/imagem), conferir de quem é cada uma e enviar por e-mail."""
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...aplicacao.folhas_assinadas import LIMITE_ARQUIVOS
from ...dominio.competencia import rotulo_competencia
from ...aplicacao.folhas_assinadas import VARIOS_MESES
from ...dominio.entidades import MetodoIdentificacao, TipoOperacao
from .. import tema as T
from ..componentes import DialogoServidor, PainelPreview, SeletorMes, Tabela
from ..utilitarios import TIPOS_FOLHA_PDF, abrir_arquivo
from .base import Fluxo


class FluxoAssinadas(Fluxo):
    TIPO = TipoOperacao.ASSINADAS
    TITULO = "Enviar folhas assinadas"
    ETAPAS = ("Arquivos", "Conferir folhas", "Enviar por e-mail")

    def __init__(self, master, app):
        super().__init__(master, app)
        self.folhas = []  # FolhaAssinada do lote
        self._servidores = {}
        self._opcoes, self._mapa = [], {}

        # ---- Etapa 1 ----
        f0 = self.frames[0]
        card = T.cartao(f0)
        card.pack(fill="x")
        ctk.CTkLabel(card, text="Folhas assinadas (PDF)", font=T.fonte(16, True)).pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(card, text="Aceita somente arquivos PDF; cada página é uma folha. Você pode enviar vários arquivos de "
                                "uma vez, de meses diferentes: o sistema lê o servidor (matrícula ou nome) e o mês de "
                                "referência escritos em cada folha, usando OCR quando o PDF for escaneado.",
                     font=T.fonte(12), text_color=T.SUAVE, wraplength=820, justify="left").pack(anchor="w", padx=24)
        T.botao_primario(card, f"Selecionar arquivos PDF (até {LIMITE_ARQUIVOS})", self._selecionar_arquivos, height=64,
                         width=340, font=T.fonte(15, True)).pack(anchor="w", padx=24, pady=(16, 8))
        self.lbl_ocr = ctk.CTkLabel(card, text="", font=T.fonte(12), text_color=T.SUAVE, wraplength=820, justify="left")
        self.lbl_ocr.pack(anchor="w", padx=24, pady=(0, 18))

        # ---- Etapa 2: conferência ----
        f1 = self.frames[1]
        barra = ctk.CTkFrame(f1, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(barra, text="Clique em cada linha para conferir a folha. Corrija o servidor ou substitua o arquivo se preciso.",
                     font=T.fonte(12), text_color=T.SUAVE).pack(side="left")
        self.sw_sem_folha = ctk.CTkSwitch(barra, text="Mostrar servidores sem folha", command=self._preencher,
                                          progress_color=T.PRIMARIA, font=T.fonte(12))
        self.sw_sem_folha.pack(side="right")
        corpo = ctk.CTkFrame(f1, fg_color="transparent")
        corpo.pack(fill="both", expand=True)
        self.painel = PainelPreview(corpo)
        self.painel.pack(side="right", fill="y")
        self.tab = Tabela(corpo, app, [
            ("nome", "Servidor", 170), ("matricula", "Matrícula", 75, "center"), ("mes", "Mês", 95, "center"),
            ("arquivo", "Arquivo / pág.", 130), ("ident", "Identificação", 90, "center"), ("obs", "Observação", 130),
        ], altura=8, ao_selecionar=self._ver, ao_duplo_clique=self._abrir, menu=self._menu)
        self.tab.pack(side="left", fill="both", expand=True, padx=(0, 12))
        a = self.painel.acoes
        # Avisos da folha (duplicada, substitui a arquivada…): a coluna Observação fica estreita na tabela
        self.lbl_obs = ctk.CTkLabel(a, text="", font=T.fonte(12, True), text_color=T.AVISO, wraplength=320,
                                    justify="left", anchor="w")
        self.lbl_titulo_servidor = ctk.CTkLabel(a, text="Esta folha pertence a (digite para filtrar)", font=T.fonte(12),
                                                text_color=T.SUAVE)
        self.lbl_titulo_servidor.pack(anchor="w")
        self.combo = T.combo(a, values=[])
        self.combo.pack(fill="x", pady=(2, 8))
        self.combo.bind("<KeyRelease>", self._filtrar)
        self.combo.bind("<Return>", lambda e: self._atribuir())
        self.btn_atribuir = T.botao_primario(a, "Confirmar servidor", self._atribuir, height=36)
        self.btn_atribuir.pack(fill="x")
        ctk.CTkLabel(a, text="Mês de referência desta folha", font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w", pady=(10, 0))
        linha_mes = ctk.CTkFrame(a, fg_color="transparent")
        linha_mes.pack(fill="x", pady=(2, 0))
        self.seletor = SeletorMes(linha_mes)
        self.seletor.opt_mes.configure(width=140)  # mês + ano + botão cabem na largura do painel
        self.seletor.opt_ano.configure(width=90)
        self.seletor.pack(side="left")
        self.btn_mes = T.botao_secundario(linha_mes, "Definir", self._definir_mes, width=76)
        self.btn_mes.pack(side="left", padx=(8, 0))
        self.btn_substituir = T.botao_secundario(a, "Substituir arquivo…", self._substituir)
        self.btn_substituir.pack(fill="x", pady=(8, 0))

    # ---- etapas ----
    def iniciar(self):
        super().iniciar()
        self.folhas = []

    def mostrar_etapa(self, etapa):
        if etapa == 0:
            if self.servicos.folhas_assinadas.ocr_disponivel():
                self.lbl_ocr.configure(text="✓ OCR disponível neste computador.", text_color=T.SUCESSO)
            else:
                self.lbl_ocr.configure(text="⚠ OCR (Tesseract) não instalado ou sem idiomas: PDFs escaneados (sem texto) não serão "
                                            "identificados automaticamente — você poderá indicar o servidor na conferência.",
                                       text_color=T.AVISO)
        elif etapa == 1:
            self.btn_avancar.configure(command=self._avancar_envio)
            self._preencher()

    def itens_auditoria(self):
        return self.servicos.folhas_assinadas.itens_auditoria(self.itens, self.folhas)

    def _selecionar_arquivos(self):
        arquivos = filedialog.askopenfilenames(title=f"Selecione as folhas assinadas em PDF (até {LIMITE_ARQUIVOS} arquivos)",
                                               filetypes=TIPOS_FOLHA_PDF)
        if not arquivos:
            return

        def fim(resultado):
            op_id, folhas = resultado
            self.folhas = folhas
            self._atualizar_competencia()
            self.comecar_operacao(op_id, self.servicos.folhas_assinadas.itens(folhas))
            self.ir_para(1)

        self.app.executar_tarefa(
            "Lendo folhas assinadas",
            lambda progresso: self.servicos.folhas_assinadas.importar_lote(list(arquivos), progresso), fim)

    def _atualizar_competencia(self):
        meses = {f.competencia for f in self.folhas if f.competencia}
        self.competencia = next(iter(meses)) if len(meses) == 1 else VARIOS_MESES

    # ---- conferência ----
    def _recalcular_itens(self):
        self._atualizar_competencia()
        self.itens = self.servicos.folhas_assinadas.itens(self.folhas, self.itens)

    @staticmethod
    def _arquivo(f):
        return f"{f.original} · pág. {f.pagina}"

    def _preencher(self):
        self._servidores = {s.id: s for s in self.servicos.servidores.listar()}
        linhas = []
        ordem = sorted(range(len(self.folhas)), key=lambda n: (
            self._servidores[self.folhas[n].servidor_id].nome if self.folhas[n].servidor_id in self._servidores else "~",
            self.folhas[n].competencia))
        for n in ordem:
            f = self.folhas[n]
            s = self._servidores.get(f.servidor_id)
            mes = rotulo_competencia(f.competencia) if f.competencia else "⚠ informar"
            if s:
                tag = "aviso" if (f.observacao or not f.competencia) else ("ok" if f.metodo == MetodoIdentificacao.MANUAL else None)
                linhas.append((f"f-{n}", (s.nome, s.matricula, mes, self._arquivo(f), f.metodo, f.observacao), tag))
            else:
                linhas.append((f"f-{n}", ("⚠ Não identificado", "", mes, self._arquivo(f), f.metodo, f.observacao), "erro"))
        if self.sw_sem_folha.get():
            referencia = self.servicos.folhas_assinadas.competencia_predominante(self.folhas)
            sem_folha = self.servicos.folhas_assinadas.servidores_sem_folha(self.folhas, referencia)
            linhas += [(f"s-{s.id}", (s.nome, s.matricula, rotulo_competencia(referencia), "— sem folha", "", ""), "suave")
                       for s in sem_folha]
        self.tab.preencher(linhas, "Nenhuma folha importada.")
        atribuidas = sum(1 for f in self.folhas if f.servidor_id in self._servidores)
        sem = len(self.folhas) - atribuidas
        sem_mes = sum(1 for f in self.folhas if not f.competencia)
        self.cab.subtitulo.configure(
            text=f"{rotulo_competencia(self.competencia)} · {len(self.folhas)} folha(s) · {atribuidas} atribuída(s) a servidores"
                 + (f" · {sem} sem servidor" if sem else "") + (f" · {sem_mes} sem mês" if sem_mes else ""))

        self._opcoes = [s.rotulo() for s in self._servidores.values()]
        self._mapa = {s.rotulo(): s.id for s in self._servidores.values()}
        self.combo.configure(values=self._opcoes[:60])
        atual = self.tab.selecionado()
        if atual:
            self._ver(atual)
        elif linhas:
            self.tab.selecionar(linhas[0][0])
        else:
            self.painel.limpar()

    def _folha_da_linha(self, iid):
        return self.folhas[int(iid[2:])] if iid and iid.startswith("f-") else None

    def _mostrar_observacao(self, texto):
        if texto:
            self.lbl_obs.configure(text=f"⚠ {texto}")
            self.lbl_obs.pack(anchor="w", fill="x", pady=(0, 8), before=self.lbl_titulo_servidor)
        else:
            self.lbl_obs.pack_forget()

    def _ver(self, iid):
        folha = self._folha_da_linha(iid)
        self._mostrar_observacao(folha.observacao if folha else "")
        if folha:
            s = self._servidores.get(folha.servidor_id)
            info = (f"{s.nome} · matrícula {s.matricula}\n{s.email or '⚠ sem e-mail'}" if s
                    else "Folha sem servidor identificado — escolha abaixo a quem ela pertence.")
            self.painel.mostrar(folha.caminho, f"{info}\n{self._arquivo(folha)} · {folha.metodo}")
            self.combo.configure(state="normal")
            self.combo.set(s.rotulo() if s else "")
            self.btn_atribuir.configure(state="normal")
            self.btn_mes.configure(state="normal")
            if folha.competencia:
                self.seletor.set(folha.competencia)
            self.btn_substituir.configure(text="Substituir arquivo…", state="normal" if s else "disabled")
        else:
            s = self._servidores.get(int(iid[2:])) if iid and iid.startswith("s-") else None
            self.painel.mostrar(None, (f"{s.nome} · matrícula {s.matricula}\n{s.email or '⚠ sem e-mail'}\n"
                                       "Este servidor ainda não tem folha neste mês." if s else ""))
            self.combo.set("")
            self.combo.configure(state="disabled")
            self.btn_atribuir.configure(state="disabled")
            self.btn_mes.configure(state="disabled")
            self.btn_substituir.configure(text="Escolher arquivo para este servidor…", state="normal" if s else "disabled")

    def _abrir(self, iid):
        folha = self._folha_da_linha(iid)
        if folha:
            abrir_arquivo(folha.caminho)

    def _menu(self, iid):
        itens = [("Abrir arquivo", self._abrir)]
        folha = self._folha_da_linha(iid)
        if folha and folha.servidor_id:
            itens += [("Substituir arquivo…", lambda i: self._substituir()),
                      ("Editar dados / e-mail do servidor…",
                       lambda i: DialogoServidor(self.app, folha.servidor_id, self._pos_edicao))]
        return itens

    def _pos_edicao(self, _servidor):
        self._recalcular_itens()
        self._preencher()

    def _filtrar(self, event):
        if event.keysym in ("Return", "Up", "Down", "Escape"):
            return
        termo = self.combo.get().strip().lower()
        valores = [o for o in self._opcoes if termo in o.lower()] if termo else self._opcoes
        self.combo.configure(values=valores[:60] or ["(nenhum servidor encontrado)"])

    def _servidor_do_combo(self):
        texto = self.combo.get().strip()
        if texto in self._mapa:
            return self._mapa[texto]
        candidatos = [o for o in self._opcoes if texto and texto.lower() in o.lower()]
        return self._mapa[candidatos[0]] if len(candidatos) == 1 else None

    def _atribuir(self):
        iid = self.tab.selecionado()
        folha = self._folha_da_linha(iid)
        if not folha:
            return
        servidor_id = self._servidor_do_combo()
        if not servidor_id:
            messagebox.showwarning("Conferência", "Escolha um servidor válido da lista.")
            return
        servico = self.servicos.folhas_assinadas
        if servidor_id == folha.servidor_id:
            self.app.notificar("Servidor confirmado.")
            iids = self.tab.iids()
            if iid in iids and iids.index(iid) + 1 < len(iids):
                self.tab.selecionar(iids[iids.index(iid) + 1])
            return
        servidor = self._servidores[servidor_id]
        atual = servico.folha_do_servidor(self.folhas, servidor_id, folha.competencia) if folha.competencia else None
        if atual and atual is not folha and not messagebox.askyesno(
                "Servidor já tem folha neste mês",
                f"{servidor.nome} já tem a folha “{self._arquivo(atual)}” em {rotulo_competencia(folha.competencia)} neste lote.\n\n"
                "Substituir por esta? A folha anterior ficará sem servidor."):
            return
        servico.atribuir(self.op_id, self.folhas, folha, servidor_id)
        self._recalcular_itens()
        self.tab.limpar_selecao()
        self._preencher()
        self.tab.selecionar(iid)
        self.app.notificar(f"Folha atribuída a {servidor.nome}.")

    def _definir_mes(self):
        iid = self.tab.selecionado()
        folha = self._folha_da_linha(iid)
        if not folha:
            return
        self.servicos.folhas_assinadas.definir_competencia(self.op_id, self.folhas, folha, self.seletor.get())
        self._recalcular_itens()
        self.tab.limpar_selecao()
        self._preencher()
        self.tab.selecionar(iid)
        self.app.notificar(f"Mês definido: {rotulo_competencia(folha.competencia)}.")

    def _substituir(self):
        iid = self.tab.selecionado()
        folha = self._folha_da_linha(iid)
        servidor_id = folha.servidor_id if folha else (int(iid[2:]) if iid and iid.startswith("s-") else None)
        if not servidor_id:
            return
        servidor = self._servidores[servidor_id]
        competencia = (folha.competencia if folha else "") or self.servicos.folhas_assinadas.competencia_predominante(self.folhas)
        caminho = filedialog.askopenfilename(title=f"Escolha a folha assinada de {servidor.nome}", filetypes=TIPOS_FOLHA_PDF)
        if not caminho:
            return

        def fim(nova):
            self._recalcular_itens()
            self._preencher()
            self.tab.selecionar(f"f-{self.folhas.index(nova)}")
            self.app.notificar(f"Folha de {servidor.nome} substituída.")

        self.app.executar_tarefa("Lendo o arquivo", lambda p: self.servicos.folhas_assinadas.substituir(
            self.op_id, self.folhas, servidor.id, caminho, competencia), fim)

    def _avancar_envio(self):
        sem_mes = [f for f in self.folhas if f.servidor_id and not f.competencia]
        if sem_mes:
            messagebox.showwarning("Mês não informado", f"{len(sem_mes)} folha(s) atribuída(s) ainda estão sem mês de "
                                                        "referência. Selecione cada uma e use “Definir”.")
            return
        sem = sum(1 for f in self.folhas if not f.servidor_id)
        if sem and not messagebox.askyesno("Folhas sem servidor", f"{sem} folha(s) continuam sem servidor e não serão "
                                                                  "enviadas.\n\nDeseja continuar mesmo assim?"):
            return
        trocas = [f for f in self.folhas if f.servidor_id and f.substitui]
        if trocas and not messagebox.askyesno(
                "Folhas já arquivadas",
                f"{len(trocas)} folha(s) substituirão versões já arquivadas do mesmo servidor e mês.\n\n"
                "A versão anterior será preservada com o sufixo _OLD_ e a data/hora. Deseja continuar?"):
            return

        def fim(itens):
            self.itens = itens
            self.ir_para(2)

        self.app.executar_tarefa("Arquivando folhas conferidas", lambda p: self.servicos.folhas_assinadas.concluir_conferencia(
            self.op_id, self.folhas, self.itens), fim)
