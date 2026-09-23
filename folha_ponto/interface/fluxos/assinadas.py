"""Fluxo 2: importar folhas assinadas (PDF/imagem), conferir de quem é cada uma e enviar por e-mail."""
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...aplicacao.folhas_assinadas import LIMITE_ARQUIVOS
from ...dominio.competencia import rotulo_competencia
from ...dominio.entidades import MetodoIdentificacao, TipoOperacao
from .. import tema as T
from ..componentes import DialogoServidor, PainelPreview, SeletorMes, Tabela
from ..utilitarios import TIPOS_FOLHA_ASSINADA, abrir_arquivo
from .base import Fluxo


class FluxoAssinadas(Fluxo):
    TIPO = TipoOperacao.ASSINADAS
    TITULO = "Enviar folhas assinadas"
    ETAPAS = ("Mês e arquivos", "Conferir folhas", "Enviar por e-mail")

    def __init__(self, master, app):
        super().__init__(master, app)
        self.folhas = []  # FolhaAssinada do lote
        self._servidores = {}
        self._opcoes, self._mapa = [], {}

        # ---- Etapa 1 ----
        f0 = self.frames[0]
        card_mes = T.cartao(f0)
        card_mes.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card_mes, text="1. Mês de referência", font=T.fonte(16, True)).pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(card_mes, text="Mês a que as folhas assinadas se referem.", font=T.fonte(12),
                     text_color=T.SUAVE).pack(anchor="w", padx=24)
        self.seletor = SeletorMes(card_mes)
        self.seletor.pack(anchor="w", padx=24, pady=(12, 20))

        card = T.cartao(f0)
        card.pack(fill="x")
        ctk.CTkLabel(card, text="2. Folhas assinadas (PDF ou imagem)", font=T.fonte(16, True)).pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(card, text="Aceita PDF, JPG, PNG, TIFF e BMP. Nos PDFs, o sistema lê primeiro o texto da folha "
                                "(matrícula e nome); se não conseguir — e sempre no caso de imagens — usa OCR.",
                     font=T.fonte(12), text_color=T.SUAVE, wraplength=820, justify="left").pack(anchor="w", padx=24)
        T.botao_primario(card, f"Selecionar arquivos (até {LIMITE_ARQUIVOS})", self._selecionar_arquivos, height=64,
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
            ("nome", "Servidor", 180), ("matricula", "Matrícula", 80, "center"), ("arquivo", "Arquivo", 140),
            ("ident", "Identificação", 100, "center"), ("obs", "Observação", 120),
        ], altura=8, ao_selecionar=self._ver, ao_duplo_clique=self._abrir, menu=self._menu)
        self.tab.pack(side="left", fill="both", expand=True, padx=(0, 12))
        a = self.painel.acoes
        ctk.CTkLabel(a, text="Esta folha pertence a (digite para filtrar)", font=T.fonte(12), text_color=T.SUAVE).pack(anchor="w")
        self.combo = T.combo(a, values=[])
        self.combo.pack(fill="x", pady=(2, 8))
        self.combo.bind("<KeyRelease>", self._filtrar)
        self.combo.bind("<Return>", lambda e: self._atribuir())
        self.btn_atribuir = T.botao_primario(a, "Confirmar servidor", self._atribuir, height=36)
        self.btn_atribuir.pack(fill="x")
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
                self.lbl_ocr.configure(text="⚠ OCR (Tesseract) não instalado: imagens e PDFs escaneados sem texto não serão "
                                            "identificados automaticamente — você poderá indicar o servidor na conferência.",
                                       text_color=T.AVISO)
        elif etapa == 1:
            self.btn_avancar.configure(command=self._avancar_envio)
            self._preencher()

    def itens_auditoria(self):
        return self.servicos.folhas_assinadas.itens_auditoria(self.itens, self.folhas)

    def _selecionar_arquivos(self):
        arquivos = filedialog.askopenfilenames(title=f"Selecione as folhas assinadas (até {LIMITE_ARQUIVOS} arquivos)",
                                               filetypes=TIPOS_FOLHA_ASSINADA)
        if not arquivos:
            return
        competencia = self.seletor.get()
        self.competencia = competencia

        def fim(resultado):
            op_id, folhas = resultado
            self.folhas = folhas
            self.comecar_operacao(op_id, self.servicos.folhas_assinadas.itens(folhas))
            self.ir_para(1)

        self.app.executar_tarefa(
            "Lendo folhas assinadas",
            lambda progresso: self.servicos.folhas_assinadas.importar_lote(list(arquivos), competencia, progresso), fim)

    # ---- conferência ----
    def _recalcular_itens(self):
        self.itens = self.servicos.folhas_assinadas.itens(self.folhas, self.itens)

    def _preencher(self):
        self._servidores = {s.id: s for s in self.servicos.servidores.listar()}
        linhas = []
        com_folha = sorted((f for f in self.folhas if f.servidor_id in self._servidores),
                           key=lambda f: self._servidores[f.servidor_id].nome)
        for f in com_folha:
            s = self._servidores[f.servidor_id]
            linhas.append((f"s-{s.id}", (s.nome, s.matricula, f.original, f.metodo, f.observacao),
                           "aviso" if f.observacao else ("ok" if f.metodo == MetodoIdentificacao.MANUAL else None)))
        for n, f in enumerate(self.folhas):
            if not f.servidor_id:
                linhas.append((f"a-{n}", ("⚠ Não identificado", "", f.original, f.metodo, f.observacao), "erro"))
        if self.sw_sem_folha.get():
            com = {f.servidor_id for f in self.folhas}
            linhas += [(f"s-{s.id}", (s.nome, s.matricula, "— sem folha", "", ""), "suave")
                       for s in self._servidores.values() if s.id not in com]
        self.tab.preencher(linhas, "Nenhuma folha importada.")
        sem = sum(1 for f in self.folhas if not f.servidor_id)
        self.cab.subtitulo.configure(text=f"{rotulo_competencia(self.competencia)} · {len(self.folhas)} arquivo(s) · "
                                          f"{len(com_folha)} atribuído(s) a servidores" + (f" · {sem} sem servidor" if sem else ""))

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
        if iid.startswith("a-"):
            return self.folhas[int(iid[2:])]
        return self.servicos.folhas_assinadas.folha_do_servidor(self.folhas, int(iid[2:]))

    def _ver(self, iid):
        folha = self._folha_da_linha(iid)
        if iid.startswith("s-"):
            s = self._servidores.get(int(iid[2:])) or self.servicos.servidores.obter(int(iid[2:]))
            info = f"{s.nome} · matrícula {s.matricula}\n{s.email or '⚠ sem e-mail'}"
        else:
            info = "Folha sem servidor identificado — escolha abaixo a quem ela pertence."
        if folha:
            self.painel.mostrar(folha.caminho, f"{info}\nArquivo: {folha.original} · {folha.metodo}")
            dono = self._servidores.get(folha.servidor_id)
            self.combo.configure(state="normal")
            self.combo.set(dono.rotulo() if dono else "")
            self.btn_atribuir.configure(state="normal")
            self.btn_substituir.configure(text="Substituir arquivo…", state="normal" if iid.startswith("s-") else "disabled")
        else:
            self.painel.mostrar(None, f"{info}\nEste servidor ainda não tem folha neste lote.")
            self.combo.set("")
            self.combo.configure(state="disabled")
            self.btn_atribuir.configure(state="disabled")
            self.btn_substituir.configure(text="Escolher arquivo para este servidor…", state="normal")

    def _abrir(self, iid):
        folha = self._folha_da_linha(iid)
        if folha:
            abrir_arquivo(folha.caminho)

    def _menu(self, iid):
        itens = [("Abrir arquivo", self._abrir)]
        if iid.startswith("s-"):
            itens += [("Substituir arquivo…", lambda i: self._substituir()),
                      ("Editar dados / e-mail do servidor…", lambda i: DialogoServidor(self.app, int(i[2:]), self._pos_edicao))]
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
        folha = self._folha_da_linha(iid) if iid else None
        if not folha:
            return
        servidor_id = self._servidor_do_combo()
        if not servidor_id:
            messagebox.showwarning("Conferência", "Escolha um servidor válido da lista.")
            return
        servico = self.servicos.folhas_assinadas
        if servidor_id == folha.servidor_id:
            servico.atribuir(self.op_id, self.folhas, folha, servidor_id)
            self.app.notificar("Servidor confirmado.")
            iids = self.tab.iids()
            if iid in iids and iids.index(iid) + 1 < len(iids):
                self.tab.selecionar(iids[iids.index(iid) + 1])
            return
        servidor = self._servidores[servidor_id]
        atual = servico.folha_do_servidor(self.folhas, servidor_id)
        if atual and not messagebox.askyesno(
                "Servidor já tem folha", f"{servidor.nome} já tem a folha “{atual.original}” neste lote.\n\n"
                                         "Substituir por esta? A folha anterior ficará sem servidor."):
            return
        servico.atribuir(self.op_id, self.folhas, folha, servidor_id)
        self._recalcular_itens()
        self.tab.limpar_selecao()
        self._preencher()
        self.tab.selecionar(f"s-{servidor_id}")
        self.app.notificar(f"Folha atribuída a {servidor.nome}.")

    def _substituir(self):
        iid = self.tab.selecionado()
        if not iid or not iid.startswith("s-"):
            return
        servidor = self._servidores[int(iid[2:])]
        caminho = filedialog.askopenfilename(title=f"Escolha a folha assinada de {servidor.nome}", filetypes=TIPOS_FOLHA_ASSINADA)
        if not caminho:
            return

        def fim(_):
            self._recalcular_itens()
            self._preencher()
            self.tab.selecionar(f"s-{servidor.id}")
            self.app.notificar(f"Folha de {servidor.nome} substituída.")

        self.app.executar_tarefa("Lendo o arquivo", lambda p: self.servicos.folhas_assinadas.substituir(
            self.op_id, self.folhas, servidor.id, caminho, self.competencia), fim)

    def _avancar_envio(self):
        sem = sum(1 for f in self.folhas if not f.servidor_id)
        if sem and not messagebox.askyesno("Folhas sem servidor", f"{sem} folha(s) continuam sem servidor e não serão "
                                                                  "enviadas.\n\nDeseja continuar mesmo assim?"):
            return

        def fim(itens):
            self.itens = itens
            self.ir_para(2)

        self.app.executar_tarefa("Arquivando folhas conferidas", lambda p: self.servicos.folhas_assinadas.concluir_conferencia(
            self.op_id, self.folhas, self.competencia, self.itens), fim)
