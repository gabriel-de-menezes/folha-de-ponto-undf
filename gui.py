import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import os
from PIL import Image
import fitz

from db import init_db, get_connection, set_config
from excel_service import parse_and_import_excel
from docx_service import fill_folha_docx
from pdf_service import convert_docx_to_pdf
from ocr_service import process_scanned_file
from email_service import (
    get_smtp_config, save_smtp_config, test_smtp_connection,
    test_resend_connection, enviar_folha_para_acumulador,
)
from arquivo_service import vincular_digitalizacao, listar_folhas_arquivadas, buscar_folha_arquivada

# Configurações globais do CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def abrir_arquivo(caminho):
    if not caminho or not os.path.exists(caminho):
        messagebox.showwarning("Arquivo não encontrado", "O arquivo não foi localizado no disco.")
        return
    try:
        os.startfile(caminho)
    except Exception as e:
        messagebox.showerror("Erro ao abrir", f"Não foi possível abrir o arquivo:\n{e}")


def gerar_preview_ctkimage(caminho, max_w=340, max_h=420):
    """Gera uma miniatura (CTkImage) de PDF (1ª página) ou imagem para exibir na interface.
    Retorna None se o arquivo não existir ou não for um tipo com preview suportado (ex: .docx)."""
    if not caminho or not os.path.exists(caminho):
        return None
    ext = os.path.splitext(caminho)[1].lower()
    try:
        if ext == '.pdf':
            doc = fitz.open(caminho)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        elif ext in ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'):
            img = Image.open(caminho).convert("RGB")
        else:
            return None
        img.thumbnail((max_w, max_h))
        return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None


class AppDIGEP(ctk.CTk):
    def __init__(self):
        super().__init__()

        init_db()

        self.title("DIGEP — Sistema de Gestão de Folhas de Ponto (UnDF)")
        self.geometry("1150x760")
        self.minsize(950, 620)

        # Atributos de estado
        self.modelo_path = os.path.abspath("Modelo de folha de ponto - Exemplo.docx")
        self.var_competencia = ctk.StringVar(value="JULHO/2026")

        self.setup_ui()
        self.carregar_servidores()
        self.carregar_acumuladores()
        self.carregar_auditoria()
        self.carregar_ocr()
        self.atualizar_painel()

    def setup_ui(self):
        # Cabeçalho Principal
        self.header_frame = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1f538d")
        self.header_frame.pack(side="top", fill="x")

        self.header_title = ctk.CTkLabel(
            self.header_frame,
            text="🏛️ UnDF - Diretoria de Gestão de Pessoas (DIGEP)",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        )
        self.header_title.pack(side="left", padx=20, pady=15)

        # Tabview principal
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

        self.tab_painel = self.tabview.add("🏠 Painel")
        self.tab_servidores = self.tabview.add("📥 Servidores")
        self.tab_gerar = self.tabview.add("📄 Gerar Folhas")
        self.tab_ocr = self.tabview.add("🔍 OCR & Conferência")
        self.tab_historico = self.tabview.add("📚 Histórico")
        self.tab_email = self.tabview.add("✉️ Envio Acumuladores")
        self.tab_auditoria = self.tabview.add("📊 Auditoria de Envios")
        self.tab_config = self.tabview.add("⚙️ Configurações")

        self.setup_tab_painel()
        self.setup_tab_servidores()
        self.setup_tab_gerar()
        self.setup_tab_ocr()
        self.setup_tab_historico()
        self.setup_tab_email()
        self.setup_tab_auditoria()
        self.setup_tab_config()

    # ==================== ABA 0: PAINEL (STATUS DO FLUXO) ====================
    def setup_tab_painel(self):
        inner = ctk.CTkFrame(self.tab_painel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(inner, text="Fluxo de Trabalho Mensal", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            inner, text="Acompanhe o andamento da competência selecionada, passo a passo.",
            text_color="gray"
        ).pack(anchor="w", pady=(0, 15))

        frame_comp = ctk.CTkFrame(inner, fg_color="transparent")
        frame_comp.pack(anchor="w", pady=(0, 20))
        ctk.CTkLabel(frame_comp, text="Competência:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        ctk.CTkEntry(frame_comp, textvariable=self.var_competencia, width=160).pack(side="left")
        ctk.CTkButton(frame_comp, text="🔄 Atualizar Painel", command=self.atualizar_painel).pack(side="left", padx=10)

        frame_steps = ctk.CTkFrame(inner, fg_color="transparent")
        frame_steps.pack(fill="x", pady=(0, 20))

        passos = [
            ("1️⃣", "Subir Planilha", "📥 Servidores"),
            ("2️⃣", "Gerar Folhas", "📄 Gerar Folhas"),
            ("3️⃣", "Conferir Digitalizações", "🔍 OCR & Conferência"),
            ("4️⃣", "Enviar aos Professores", "✉️ Envio Acumuladores"),
        ]
        self.step_cards = []
        for i, (num, titulo, destino_tab) in enumerate(passos):
            frame_steps.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(frame_steps, corner_radius=10, fg_color=("gray90", "gray20"))
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")

            ctk.CTkLabel(card, text=num, font=ctk.CTkFont(size=26)).pack(pady=(15, 0))
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
            lbl_status = ctk.CTkLabel(card, text="...", font=ctk.CTkFont(size=13), text_color="gray")
            lbl_status.pack(pady=(0, 10))
            ctk.CTkButton(
                card, text="Ir para aba →", fg_color="transparent", border_width=1,
                command=lambda dt=destino_tab: self.tabview.set(dt)
            ).pack(pady=(0, 15), padx=15, fill="x")
            self.step_cards.append(lbl_status)

        ctk.CTkLabel(inner, text="📋 Atividade recente de envios", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10, 5))
        self.txt_atividade = ctk.CTkTextbox(inner, height=220)
        self.txt_atividade.pack(fill="both", expand=True)

    def atualizar_painel(self):
        if not hasattr(self, "step_cards"):
            return
        competencia = self.var_competencia.get().strip()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as c FROM servidores")
        total_servidores = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(DISTINCT servidor_id) as c FROM folhas_geradas WHERE competencia = ?", (competencia,))
        total_geradas = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM folhas_digitalizadas WHERE status_ocr = 'Pendente Validação'")
        total_pendentes = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM servidores WHERE LOWER(acumula_cargo) = 'sim'")
        total_acumuladores = cursor.fetchone()["c"]

        cursor.execute("""
            SELECT COUNT(*) as c FROM (
                SELECT servidor_id, status, ROW_NUMBER() OVER (PARTITION BY servidor_id ORDER BY id DESC) as rn
                FROM logs_envio WHERE competencia = ?
            ) WHERE rn = 1 AND status = 'Enviado'
        """, (competencia,))
        total_enviados = cursor.fetchone()["c"]

        cursor.execute("""
            SELECT s.nome, l.status, l.competencia, l.enviado_em
            FROM logs_envio l JOIN servidores s ON l.servidor_id = s.id
            ORDER BY l.id DESC LIMIT 8
        """)
        atividade = cursor.fetchall()
        conn.close()

        self.step_cards[0].configure(text=f"{total_servidores} servidor(es) cadastrado(s)")
        self.step_cards[1].configure(text=f"{total_geradas}/{total_servidores} folha(s) gerada(s)")
        self.step_cards[2].configure(text=f"{total_pendentes} pendente(s) de conferência")
        self.step_cards[3].configure(text=f"{total_enviados}/{total_acumuladores} enviado(s)")

        self.txt_atividade.delete("1.0", "end")
        if not atividade:
            self.txt_atividade.insert("end", "Nenhum envio realizado ainda.\n")
        for r in atividade:
            icone = "✅" if r["status"] == "Enviado" else "❌"
            self.txt_atividade.insert("end", f"{icone} {r['nome']} — {r['competencia']} — {r['status']} ({r['enviado_em']})\n")

    # ==================== ABA 1: SERVIDORES (EXCEL) ====================
    def setup_tab_servidores(self):
        frame_top = ctk.CTkFrame(self.tab_servidores)
        frame_top.pack(fill="x", padx=10, pady=10)

        btn_importar = ctk.CTkButton(
            frame_top,
            text="📂 Importar Planilha Excel",
            command=self.importar_excel,
            fg_color="#2fa572", hover_color="#1e7e52"
        )
        btn_importar.pack(side="left", padx=10, pady=10)

        btn_atualizar = ctk.CTkButton(frame_top, text="🔄 Atualizar Lista", command=self.carregar_servidores)
        btn_atualizar.pack(side="left", padx=10, pady=10)

        btn_editar = ctk.CTkButton(frame_top, text="✏️ Editar Servidor Selecionado", command=self.editar_servidor_selecionado)
        btn_editar.pack(side="left", padx=10, pady=10)

        lbl_dica = ctk.CTkLabel(self.tab_servidores, text="Dica: dê duplo clique em um servidor para editar seus dados manualmente.", text_color="gray")
        lbl_dica.pack(padx=10, anchor="w")

        # Tabela de Servidores (Treeview)
        style = ttk.Style()
        style.theme_use("clam")

        columns = ("id", "nome", "matricula", "cpf", "email", "carga_horaria", "acumula_cargo")
        self.tree_servidores = ttk.Treeview(self.tab_servidores, columns=columns, show="headings", height=15)

        self.tree_servidores.heading("id", text="ID")
        self.tree_servidores.heading("nome", text="Nome do Servidor")
        self.tree_servidores.heading("matricula", text="Matrícula")
        self.tree_servidores.heading("cpf", text="CPF")
        self.tree_servidores.heading("email", text="E-mail Pessoal")
        self.tree_servidores.heading("carga_horaria", text="Carga Horária")
        self.tree_servidores.heading("acumula_cargo", text="Acumula Cargo?")

        self.tree_servidores.column("id", width=40, anchor="center")
        self.tree_servidores.column("nome", width=230)
        self.tree_servidores.column("matricula", width=100, anchor="center")
        self.tree_servidores.column("cpf", width=110, anchor="center")
        self.tree_servidores.column("email", width=190)
        self.tree_servidores.column("carga_horaria", width=90, anchor="center")
        self.tree_servidores.column("acumula_cargo", width=100, anchor="center")

        self.tree_servidores.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree_servidores.bind("<Double-1>", lambda e: self.editar_servidor_selecionado())

    def importar_excel(self):
        filepath = filedialog.askopenfilename(
            title="Selecione a Planilha de Servidores/Professores",
            filetypes=[("Planilhas Excel", "*.xlsx *.xls")]
        )
        if filepath:
            count, msg = parse_and_import_excel(filepath)
            messagebox.showinfo("Importação Excel", msg)
            self.carregar_servidores()
            self.carregar_acumuladores()
            self.atualizar_painel()

    def carregar_servidores(self):
        for item in self.tree_servidores.get_children():
            self.tree_servidores.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, matricula, cpf, email, carga_horaria, acumula_cargo FROM servidores ORDER BY nome")
        for row in cursor.fetchall():
            self.tree_servidores.insert("", "end", values=tuple(row))
        conn.close()

    def editar_servidor_selecionado(self):
        sel = self.tree_servidores.selection()
        if not sel:
            messagebox.showinfo("Editar Servidor", "Selecione um servidor na lista primeiro.")
            return
        valores = self.tree_servidores.item(sel[0], "values")
        servidor_id = valores[0]
        self.abrir_dialogo_editar_servidor(servidor_id)

    def abrir_dialogo_editar_servidor(self, servidor_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servidores WHERE id = ?", (servidor_id,))
        s = cursor.fetchone()
        conn.close()
        if not s:
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Editar Servidor — {s['nome']}")
        win.geometry("420x420")
        win.grab_set()

        campos = {}

        def add_field(label, key, valor, row):
            ctk.CTkLabel(win, text=label).grid(row=row, column=0, padx=10, pady=8, sticky="w")
            entry = ctk.CTkEntry(win, width=230)
            entry.insert(0, valor or "")
            entry.grid(row=row, column=1, padx=10, pady=8)
            campos[key] = entry

        add_field("Nome:", "nome", s["nome"], 0)
        add_field("Matrícula:", "matricula", s["matricula"], 1)
        add_field("CPF:", "cpf", s["cpf"], 2)
        add_field("E-mail pessoal:", "email", s["email"], 3)
        add_field("Carga Horária:", "carga_horaria", s["carga_horaria"], 4)

        ctk.CTkLabel(win, text="Acumula Cargo?:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        var_acumula = ctk.StringVar(value=s["acumula_cargo"] or "Não")
        combo_acumula = ctk.CTkComboBox(win, values=["Sim", "Não"], variable=var_acumula, width=230)
        combo_acumula.grid(row=5, column=1, padx=10, pady=8)

        def salvar():
            conn2 = get_connection()
            c2 = conn2.cursor()
            c2.execute("""
                UPDATE servidores SET nome=?, matricula=?, cpf=?, email=?, carga_horaria=?, acumula_cargo=?
                WHERE id=?
            """, (
                campos["nome"].get().strip(), campos["matricula"].get().strip(), campos["cpf"].get().strip(),
                campos["email"].get().strip(), campos["carga_horaria"].get().strip(), var_acumula.get(),
                servidor_id
            ))
            conn2.commit()
            conn2.close()
            win.destroy()
            self.carregar_servidores()
            self.carregar_acumuladores()

        btn_salvar = ctk.CTkButton(win, text="💾 Salvar", command=salvar, fg_color="#2fa572", hover_color="#1e7e52")
        btn_salvar.grid(row=6, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    # ==================== ABA 2: GERAR FOLHAS DE PONTO ====================
    def setup_tab_gerar(self):
        frame_config = ctk.CTkFrame(self.tab_gerar)
        frame_config.pack(fill="x", padx=10, pady=10)

        lbl_comp = ctk.CTkLabel(frame_config, text="Competência (Mês/Ano):", font=ctk.CTkFont(weight="bold"))
        lbl_comp.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.entry_competencia = ctk.CTkEntry(frame_config, textvariable=self.var_competencia, width=200)
        self.entry_competencia.grid(row=0, column=1, padx=10, pady=10)

        lbl_mod = ctk.CTkLabel(frame_config, text="Modelo .docx:", font=ctk.CTkFont(weight="bold"))
        lbl_mod.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.lbl_modelo_path = ctk.CTkLabel(frame_config, text=os.path.basename(self.modelo_path) + " (padrão institucional)", text_color="gray")
        self.lbl_modelo_path.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="w")

        btn_gerar_todas = ctk.CTkButton(
            self.tab_gerar,
            text="🚀 Gerar Folhas de Ponto para Todos os Servidores",
            command=self.gerar_folhas_todas,
            height=40, font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1f538d", hover_color="#14375e"
        )
        btn_gerar_todas.pack(fill="x", padx=10, pady=15)

        self.txt_log_gerar = ctk.CTkTextbox(self.tab_gerar, height=250)
        self.txt_log_gerar.pack(fill="both", expand=True, padx=10, pady=10)

    def gerar_folhas_todas(self):
        competencia = self.var_competencia.get().strip()
        if not competencia:
            messagebox.showwarning("Atenção", "Informe a competência (ex: JULHO/2026).")
            return

        if not os.path.exists(self.modelo_path):
            messagebox.showerror("Erro", "O modelo .docx não foi encontrado.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servidores")
        servidores = cursor.fetchall()
        conn.close()

        if not servidores:
            messagebox.showwarning("Atenção", "Nenhum servidor cadastrado no banco de dados.")
            return

        self.txt_log_gerar.delete("1.0", "end")
        self.txt_log_gerar.insert("end", f"=== INICIANDO GERAÇÃO DE FOLHAS ({competencia}) ===\n\n")

        pasta_saida = os.path.abspath(os.path.join("Folhas_Geradas", competencia.replace('/', '_')))
        os.makedirs(pasta_saida, exist_ok=True)

        sucesso_count = 0
        for s in servidores:
            s_dict = dict(s)
            nome_clean = "".join(c for c in s_dict['nome'] if c.isalnum() or c in (' ', '_')).rstrip()
            nome_arquivo = f"Folha_{s_dict['matricula']}_{nome_clean}.docx"
            out_docx = os.path.join(pasta_saida, nome_arquivo)
            out_pdf = out_docx.replace('.docx', '.pdf')

            try:
                fill_folha_docx(self.modelo_path, s_dict, competencia, out_docx)
                pdf_ok, pdf_msg = convert_docx_to_pdf(out_docx, out_pdf)

                caminho_final = out_pdf if pdf_ok else out_docx

                conn = get_connection()
                c_cur = conn.cursor()
                c_cur.execute("""
                    INSERT INTO folhas_geradas (servidor_id, competencia, caminho_docx, caminho_pdf)
                    VALUES (?, ?, ?, ?)
                """, (s_dict['id'], competencia, out_docx, out_pdf if pdf_ok else None))
                conn.commit()
                conn.close()

                sucesso_count += 1
                self.txt_log_gerar.insert("end", f"✓ [{s_dict['matricula']}] {s_dict['nome']} -> {os.path.basename(caminho_final)}\n")
            except Exception as e:
                self.txt_log_gerar.insert("end", f"❌ Erro ao gerar para [{s_dict['matricula']}] {s_dict['nome']}: {e}\n")

        self.txt_log_gerar.insert("end", f"\n=== CONCLUÍDO: {sucesso_count}/{len(servidores)} folhas geradas em '{pasta_saida}' ===\n")
        self.atualizar_painel()

    # ==================== ABA 3: OCR & CONFERÊNCIA ====================
    def setup_tab_ocr(self):
        self.ocr_doc_atual = None
        self._ocr_mapa_servidor = {}
        self._ocr_preview_img = None

        frame_top = ctk.CTkFrame(self.tab_ocr)
        frame_top.pack(fill="x", padx=10, pady=10)

        btn_upload = ctk.CTkButton(
            frame_top,
            text="📥 Upload em Lote de Digitalizações (PDF/Imagens)",
            command=self.upload_digitalizacoes,
            fg_color="#2fa572", hover_color="#1e7e52"
        )
        btn_upload.pack(side="left", padx=10, pady=10)

        btn_atualizar_ocr = ctk.CTkButton(frame_top, text="🔄 Atualizar Lista", command=self.carregar_ocr)
        btn_atualizar_ocr.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            self.tab_ocr,
            text="Clique em uma folha na lista à esquerda para visualizar e conferir o servidor/competência à direita.",
            text_color="gray"
        ).pack(padx=10, anchor="w")

        frame_body = ctk.CTkFrame(self.tab_ocr, fg_color="transparent")
        frame_body.pack(fill="both", expand=True, padx=10, pady=10)

        # ---- Lista (esquerda) ----
        frame_lista = ctk.CTkFrame(frame_body)
        frame_lista.pack(side="left", fill="both", expand=True, padx=(0, 10))

        columns = ("id", "caminho", "servidor", "competencia", "status")
        self.tree_ocr = ttk.Treeview(frame_lista, columns=columns, show="headings", height=18)

        self.tree_ocr.heading("id", text="ID")
        self.tree_ocr.heading("caminho", text="Arquivo")
        self.tree_ocr.heading("servidor", text="Servidor Sugerido")
        self.tree_ocr.heading("competencia", text="Competência")
        self.tree_ocr.heading("status", text="Status")

        self.tree_ocr.column("id", width=40, anchor="center")
        self.tree_ocr.column("caminho", width=200)
        self.tree_ocr.column("servidor", width=190)
        self.tree_ocr.column("competencia", width=100, anchor="center")
        self.tree_ocr.column("status", width=130, anchor="center")

        self.tree_ocr.pack(fill="both", expand=True)
        self.tree_ocr.bind("<<TreeviewSelect>>", lambda e: self.selecionar_ocr())

        # ---- Preview + Conferência (direita) ----
        frame_preview = ctk.CTkFrame(frame_body, width=360)
        frame_preview.pack(side="left", fill="y")
        frame_preview.pack_propagate(False)

        self.lbl_preview_ocr = ctk.CTkLabel(
            frame_preview, text="Selecione uma folha\npara visualizar", text_color="gray", justify="center"
        )
        self.lbl_preview_ocr.pack(padx=10, pady=10, fill="x")

        self.lbl_preview_ocr_arquivo = ctk.CTkLabel(frame_preview, text="", font=ctk.CTkFont(weight="bold"), wraplength=330, justify="left")
        self.lbl_preview_ocr_arquivo.pack(padx=10, pady=(0, 10), anchor="w")

        ctk.CTkLabel(frame_preview, text="Servidor correspondente:").pack(padx=10, anchor="w")
        self.var_ocr_servidor = ctk.StringVar(value="")
        self.combo_ocr_servidor = ctk.CTkComboBox(frame_preview, values=[], variable=self.var_ocr_servidor, width=330)
        self.combo_ocr_servidor.pack(padx=10, pady=5)

        ctk.CTkLabel(frame_preview, text="Competência (Mês/Ano):").pack(padx=10, anchor="w")
        self.entry_ocr_competencia = ctk.CTkEntry(frame_preview, width=330)
        self.entry_ocr_competencia.pack(padx=10, pady=5)

        btn_validar = ctk.CTkButton(
            frame_preview, text="✅ Validar e Arquivar", command=self.validar_ocr_atual,
            fg_color="#2fa572", hover_color="#1e7e52"
        )
        btn_validar.pack(padx=10, pady=(15, 5), fill="x")

        btn_abrir_ocr = ctk.CTkButton(
            frame_preview, text="👁️ Abrir Arquivo Original", command=self.abrir_arquivo_ocr_selecionado,
            fg_color="gray40", hover_color="gray30"
        )
        btn_abrir_ocr.pack(padx=10, pady=5, fill="x")

    def upload_digitalizacoes(self):
        files = filedialog.askopenfilenames(
            title="Selecione os arquivos digitalizados",
            filetypes=[("Arquivos Suportados", "*.pdf *.png *.jpg *.jpeg *.tif *.tiff")]
        )
        if files:
            identificados = 0
            for f in files:
                resultado = process_scanned_file(f)
                if resultado.get("servidor_id"):
                    identificados += 1
            messagebox.showinfo(
                "OCR",
                f"{len(files)} arquivo(s) processado(s) por OCR.\n"
                f"{identificados} identificado(s) automaticamente.\n"
                f"{len(files) - identificados} precisam de conferência/validação manual."
            )
            self.carregar_ocr()
            self.atualizar_painel()

    def carregar_ocr(self):
        for item in self.tree_ocr.get_children():
            self.tree_ocr.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id, f.caminho_arquivo, s.nome, f.competencia, f.status_ocr
            FROM folhas_digitalizadas f
            LEFT JOIN servidores s ON f.servidor_id = s.id
            ORDER BY f.id DESC
        """)
        for row in cursor.fetchall():
            row_list = list(row)
            row_list[1] = os.path.basename(row_list[1])
            if not row_list[2]:
                row_list[2] = "⚠️ Não Identificado (Pendente)"
            self.tree_ocr.insert("", "end", values=tuple(row_list))
        conn.close()

    def selecionar_ocr(self):
        sel = self.tree_ocr.selection()
        if not sel:
            return
        doc_id = self.tree_ocr.item(sel[0], "values")[0]
        self.ocr_doc_atual = doc_id

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM folhas_digitalizadas WHERE id = ?", (doc_id,))
        doc = cursor.fetchone()
        cursor.execute("SELECT id, nome, matricula FROM servidores ORDER BY nome")
        servidores = cursor.fetchall()
        conn.close()
        if not doc:
            return

        opcoes = [f"{s['matricula']} - {s['nome']}" for s in servidores]
        self._ocr_mapa_servidor = {opc: s['id'] for opc, s in zip(opcoes, servidores)}
        self.combo_ocr_servidor.configure(values=opcoes)
        self.var_ocr_servidor.set("")
        for opc, sid in self._ocr_mapa_servidor.items():
            if sid == doc["servidor_id"]:
                self.var_ocr_servidor.set(opc)
                break

        self.entry_ocr_competencia.delete(0, "end")
        self.entry_ocr_competencia.insert(0, doc["competencia"] or self.var_competencia.get())

        self.lbl_preview_ocr_arquivo.configure(text=os.path.basename(doc["caminho_arquivo"]))

        img = gerar_preview_ctkimage(doc["caminho_arquivo"])
        self._ocr_preview_img = img
        if img:
            self.lbl_preview_ocr.configure(image=img, text="")
        else:
            self.lbl_preview_ocr.configure(image=None, text="(Sem preview disponível\npara este tipo de arquivo)")

    def validar_ocr_atual(self):
        if not self.ocr_doc_atual:
            messagebox.showinfo("Conferência", "Selecione uma folha na lista à esquerda.")
            return
        if not self._ocr_mapa_servidor:
            messagebox.showwarning("Conferência", "Nenhum servidor cadastrado. Importe a planilha primeiro.")
            return
        opcao_sel = self.var_ocr_servidor.get()
        if opcao_sel not in self._ocr_mapa_servidor:
            messagebox.showwarning("Conferência", "Selecione um servidor válido na lista.")
            return
        competencia = self.entry_ocr_competencia.get().strip()
        if not competencia:
            messagebox.showwarning("Conferência", "Informe a competência.")
            return
        vincular_digitalizacao(self.ocr_doc_atual, self._ocr_mapa_servidor[opcao_sel], competencia, status="Validado")
        self.carregar_ocr()
        self.atualizar_painel()
        messagebox.showinfo("Conferência", "Folha validada e arquivada com sucesso.")

    def abrir_arquivo_ocr_selecionado(self):
        sel = self.tree_ocr.selection()
        if not sel:
            messagebox.showinfo("Abrir Arquivo", "Selecione uma folha digitalizada na lista.")
            return
        doc_id = self.tree_ocr.item(sel[0], "values")[0]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT caminho_arquivo FROM folhas_digitalizadas WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            abrir_arquivo(row["caminho_arquivo"])

    # ==================== ABA 4: HISTÓRICO DE FOLHAS ====================
    def setup_tab_historico(self):
        self._hist_preview_img = None

        frame_filtros = ctk.CTkFrame(self.tab_historico)
        frame_filtros.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_filtros, text="Buscar por nome/matrícula:").pack(side="left", padx=(10, 5), pady=10)
        self.entry_filtro_nome = ctk.CTkEntry(frame_filtros, width=220)
        self.entry_filtro_nome.pack(side="left", padx=5, pady=10)
        self.entry_filtro_nome.bind("<KeyRelease>", lambda e: self.buscar_folhas_arquivadas())

        ctk.CTkLabel(frame_filtros, text="Competência:").pack(side="left", padx=(15, 5), pady=10)
        self.entry_filtro_competencia = ctk.CTkEntry(frame_filtros, width=140)
        self.entry_filtro_competencia.pack(side="left", padx=5, pady=10)
        self.entry_filtro_competencia.bind("<KeyRelease>", lambda e: self.buscar_folhas_arquivadas())

        btn_limpar = ctk.CTkButton(frame_filtros, text="Limpar filtros", command=self.limpar_filtros_consulta, fg_color="gray40", hover_color="gray30")
        btn_limpar.pack(side="left", padx=10, pady=10)

        frame_body = ctk.CTkFrame(self.tab_historico, fg_color="transparent")
        frame_body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ---- Lista (esquerda) ----
        frame_lista = ctk.CTkFrame(frame_body)
        frame_lista.pack(side="left", fill="both", expand=True, padx=(0, 10))

        columns = ("id", "origem", "nome", "matricula", "competencia", "status")
        self.tree_consulta = ttk.Treeview(frame_lista, columns=columns, show="headings", height=18)

        self.tree_consulta.heading("id", text="ID")
        self.tree_consulta.heading("origem", text="Origem")
        self.tree_consulta.heading("nome", text="Servidor")
        self.tree_consulta.heading("matricula", text="Matrícula")
        self.tree_consulta.heading("competencia", text="Competência")
        self.tree_consulta.heading("status", text="Status")

        self.tree_consulta.column("id", width=40, anchor="center")
        self.tree_consulta.column("origem", width=90, anchor="center")
        self.tree_consulta.column("nome", width=200)
        self.tree_consulta.column("matricula", width=100, anchor="center")
        self.tree_consulta.column("competencia", width=110, anchor="center")
        self.tree_consulta.column("status", width=100, anchor="center")

        self.tree_consulta.pack(fill="both", expand=True)
        self.tree_consulta.bind("<<TreeviewSelect>>", lambda e: self.selecionar_historico())

        # ---- Preview (direita) ----
        frame_preview = ctk.CTkFrame(frame_body, width=360)
        frame_preview.pack(side="left", fill="y")
        frame_preview.pack_propagate(False)

        self.lbl_preview_hist = ctk.CTkLabel(
            frame_preview, text="Selecione uma folha\npara visualizar", text_color="gray", justify="center"
        )
        self.lbl_preview_hist.pack(padx=10, pady=10, fill="x")

        self.lbl_preview_hist_info = ctk.CTkLabel(frame_preview, text="", wraplength=330, justify="left")
        self.lbl_preview_hist_info.pack(padx=10, pady=(0, 10), anchor="w")

        btn_abrir = ctk.CTkButton(
            frame_preview, text="📂 Abrir / Baixar Arquivo", command=self.abrir_folha_consulta_selecionada,
            fg_color="#2fa572", hover_color="#1e7e52"
        )
        btn_abrir.pack(padx=10, pady=10, fill="x")

        self.buscar_folhas_arquivadas()

    def limpar_filtros_consulta(self):
        self.entry_filtro_nome.delete(0, "end")
        self.entry_filtro_competencia.delete(0, "end")
        self.buscar_folhas_arquivadas()

    def buscar_folhas_arquivadas(self):
        for item in self.tree_consulta.get_children():
            self.tree_consulta.delete(item)

        termo = self.entry_filtro_nome.get()
        competencia = self.entry_filtro_competencia.get()

        resultados = list(listar_folhas_arquivadas(termo, "", competencia))
        if termo:
            resultados += list(listar_folhas_arquivadas("", termo, competencia))

        vistos = set()
        for row in resultados:
            chave = (row["origem"], row["id"])
            if chave in vistos:
                continue
            vistos.add(chave)
            self.tree_consulta.insert("", "end", values=(
                row["id"], row["origem"], row["nome"], row["matricula"], row["competencia"], row["status"]
            ), tags=(row["caminho"] or "",))

    def selecionar_historico(self):
        sel = self.tree_consulta.selection()
        if not sel:
            return
        item = self.tree_consulta.item(sel[0])
        valores = item["values"]
        tags = item.get("tags")
        caminho = tags[0] if tags else None

        self.lbl_preview_hist_info.configure(
            text=f"{valores[2]}\nMatrícula: {valores[3]}\nCompetência: {valores[4]} — {valores[5]}\n"
                 f"Arquivo: {os.path.basename(caminho) if caminho else '—'}"
        )

        img = gerar_preview_ctkimage(caminho) if caminho else None
        self._hist_preview_img = img
        if img:
            self.lbl_preview_hist.configure(image=img, text="")
        else:
            self.lbl_preview_hist.configure(image=None, text="(Sem preview disponível —\nabra o arquivo para visualizar)")

    def abrir_folha_consulta_selecionada(self):
        sel = self.tree_consulta.selection()
        if not sel:
            messagebox.showinfo("Abrir Folha", "Selecione uma folha arquivada na lista.")
            return
        item = self.tree_consulta.item(sel[0])
        tags = item.get("tags")
        caminho = tags[0] if tags else None
        abrir_arquivo(caminho)

    # ==================== ABA 5: ENVIO ACUMULADORES ====================
    def setup_tab_email(self):
        frame_opts = ctk.CTkFrame(self.tab_email)
        frame_opts.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_opts, text="Competência:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_comp_email = ctk.CTkEntry(frame_opts, textvariable=self.var_competencia, width=160)
        entry_comp_email.grid(row=0, column=1, padx=10, pady=10)

        lbl_metodo = ctk.CTkLabel(frame_opts, text="Método de Envio:", font=ctk.CTkFont(weight="bold"))
        lbl_metodo.grid(row=0, column=2, padx=10, pady=10)

        cfg = get_smtp_config()
        self.var_metodo = ctk.StringVar(value=cfg.get("metodo_envio", "Resend"))
        rb_resend = ctk.CTkRadioButton(frame_opts, text="API Resend (principal)", variable=self.var_metodo, value="Resend")
        rb_resend.grid(row=0, column=3, padx=10, pady=10)

        rb_smtp = ctk.CTkRadioButton(frame_opts, text="Servidor SMTP (Gmail/Office365/UnDF)", variable=self.var_metodo, value="SMTP")
        rb_smtp.grid(row=0, column=4, padx=10, pady=10)

        rb_outlook = ctk.CTkRadioButton(frame_opts, text="MS Outlook Desktop (Windows)", variable=self.var_metodo, value="Outlook")
        rb_outlook.grid(row=0, column=5, padx=10, pady=10)

        frame_botoes = ctk.CTkFrame(self.tab_email)
        frame_botoes.pack(fill="x", padx=10)

        btn_enviar_acum = ctk.CTkButton(
            frame_botoes,
            text="📧 Enviar Folhas para Todos os Acumuladores",
            command=self.enviar_emails_acumuladores,
            height=40, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2fa572", hover_color="#1e7e52"
        )
        btn_enviar_acum.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=10)

        btn_reenviar = ctk.CTkButton(
            frame_botoes,
            text="🔁 Reenviar para Selecionado",
            command=self.reenviar_email_selecionado,
            height=40, fg_color="#c9822b", hover_color="#a6691f"
        )
        btn_reenviar.pack(side="left", fill="x", expand=True, padx=(5, 0), pady=10)

        # Tabela de Acumuladores
        columns = ("id", "nome", "matricula", "email", "status_envio", "ultimo_envio")
        self.tree_acumuladores = ttk.Treeview(self.tab_email, columns=columns, show="headings", height=12)

        self.tree_acumuladores.heading("id", text="ID")
        self.tree_acumuladores.heading("nome", text="Servidor (Acumulador)")
        self.tree_acumuladores.heading("matricula", text="Matrícula")
        self.tree_acumuladores.heading("email", text="E-mail Pessoal")
        self.tree_acumuladores.heading("status_envio", text="Status (competência atual)")
        self.tree_acumuladores.heading("ultimo_envio", text="Último Envio")

        self.tree_acumuladores.column("id", width=40, anchor="center")
        self.tree_acumuladores.column("nome", width=230)
        self.tree_acumuladores.column("matricula", width=110, anchor="center")
        self.tree_acumuladores.column("email", width=200)
        self.tree_acumuladores.column("status_envio", width=170, anchor="center")
        self.tree_acumuladores.column("ultimo_envio", width=150, anchor="center")

        self.tree_acumuladores.pack(fill="both", expand=True, padx=10, pady=10)

    def carregar_acumuladores(self):
        for item in self.tree_acumuladores.get_children():
            self.tree_acumuladores.delete(item)

        competencia = self.var_competencia.get().strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.nome, s.matricula, s.email,
                   COALESCE(l.status, 'Pendente') as status_envio,
                   COALESCE(l.enviado_em, '') as ultimo_envio
            FROM servidores s
            LEFT JOIN (
                SELECT servidor_id, status, enviado_em,
                       ROW_NUMBER() OVER (PARTITION BY servidor_id ORDER BY id DESC) as rn
                FROM logs_envio
                WHERE competencia = ?
            ) l ON s.id = l.servidor_id AND l.rn = 1
            WHERE LOWER(s.acumula_cargo) = 'sim'
            ORDER BY s.nome
        """, (competencia,))
        for row in cursor.fetchall():
            self.tree_acumuladores.insert("", "end", values=tuple(row))
        conn.close()

    def enviar_emails_acumuladores(self):
        competencia = self.var_competencia.get().strip()
        metodo = self.var_metodo.get()
        set_config("metodo_envio", metodo)

        if not competencia:
            messagebox.showwarning("Atenção", "Informe a competência.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servidores WHERE LOWER(acumula_cargo) = 'sim'")
        acumuladores = cursor.fetchall()
        conn.close()

        if not acumuladores:
            messagebox.showinfo("Envio", "Nenhum servidor com acúmulo de cargo encontrado.")
            return

        cfg = get_smtp_config()
        sucesso_count = 0
        erros = []
        for s in acumuladores:
            s_dict = dict(s)
            ok, msg = enviar_folha_para_acumulador(s_dict, competencia, metodo=metodo, smtp_config=cfg)
            if ok:
                sucesso_count += 1
            else:
                erros.append(f"{s_dict['nome']}: {msg}")

        resumo = f"{sucesso_count}/{len(acumuladores)} e-mails enviados com sucesso."
        if erros:
            resumo += "\n\nErros:\n" + "\n".join(erros[:10])
        messagebox.showinfo("Envio de E-mails", resumo)
        self.carregar_acumuladores()
        self.carregar_auditoria()
        self.atualizar_painel()

    def reenviar_email_selecionado(self):
        sel = self.tree_acumuladores.selection()
        if not sel:
            messagebox.showinfo("Reenviar", "Selecione um servidor na lista.")
            return

        competencia = self.var_competencia.get().strip()
        metodo = self.var_metodo.get()
        set_config("metodo_envio", metodo)

        servidor_id = self.tree_acumuladores.item(sel[0], "values")[0]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servidores WHERE id = ?", (servidor_id,))
        s = cursor.fetchone()
        conn.close()
        if not s:
            return

        cfg = get_smtp_config()
        ok, msg = enviar_folha_para_acumulador(dict(s), competencia, metodo=metodo, smtp_config=cfg)
        if ok:
            messagebox.showinfo("Reenviar", f"E-mail reenviado com sucesso para {s['nome']}.")
        else:
            messagebox.showerror("Reenviar", f"Falha ao reenviar para {s['nome']}:\n{msg}")

        self.carregar_acumuladores()
        self.carregar_auditoria()
        self.atualizar_painel()

    # ==================== ABA 6: AUDITORIA ====================
    def setup_tab_auditoria(self):
        lbl_hist = ctk.CTkLabel(self.tab_auditoria, text="📋 Histórico de Auditoria & Envio de Folhas", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_hist.pack(padx=10, pady=10, anchor="w")

        frame_top = ctk.CTkFrame(self.tab_auditoria)
        frame_top.pack(fill="x", padx=10)
        btn_atualizar = ctk.CTkButton(frame_top, text="🔄 Atualizar", command=self.carregar_auditoria)
        btn_atualizar.pack(side="left", padx=10, pady=5)

        columns = ("id", "servidor", "destinatario", "competencia", "status", "data", "detalhes")
        self.tree_auditoria = ttk.Treeview(self.tab_auditoria, columns=columns, show="headings", height=15)

        self.tree_auditoria.heading("id", text="ID")
        self.tree_auditoria.heading("servidor", text="Servidor")
        self.tree_auditoria.heading("destinatario", text="Destinatário")
        self.tree_auditoria.heading("competencia", text="Competência")
        self.tree_auditoria.heading("status", text="Status Envio")
        self.tree_auditoria.heading("data", text="Data/Hora")
        self.tree_auditoria.heading("detalhes", text="Detalhes")

        self.tree_auditoria.column("id", width=40, anchor="center")
        self.tree_auditoria.column("servidor", width=190)
        self.tree_auditoria.column("destinatario", width=170)
        self.tree_auditoria.column("competencia", width=100, anchor="center")
        self.tree_auditoria.column("status", width=90, anchor="center")
        self.tree_auditoria.column("data", width=140, anchor="center")
        self.tree_auditoria.column("detalhes", width=250)

        self.tree_auditoria.pack(fill="both", expand=True, padx=10, pady=10)

    def carregar_auditoria(self):
        for item in self.tree_auditoria.get_children():
            self.tree_auditoria.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.id, s.nome, l.destinatario, l.competencia, l.status, l.enviado_em, l.detalhes_erro
            FROM logs_envio l
            JOIN servidores s ON l.servidor_id = s.id
            ORDER BY l.id DESC
        """)
        for row in cursor.fetchall():
            self.tree_auditoria.insert("", "end", values=tuple(row))
        conn.close()

    # ==================== ABA 7: CONFIGURAÇÕES (Resend / SMTP) ====================
    def setup_tab_config(self):
        cfg = get_smtp_config()

        # ---- Seção API Resend (método principal) ----
        frame_resend = ctk.CTkFrame(self.tab_config)
        frame_resend.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            frame_resend, text="Envio via API Resend (principal)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 20), sticky="w")

        ctk.CTkLabel(frame_resend, text="API Key (resend.com):").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.entry_resend_key = ctk.CTkEntry(frame_resend, width=320, show="*")
        self.entry_resend_key.insert(0, cfg.get("resend_api_key", ""))
        self.entry_resend_key.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_resend, text="E-mail do remetente:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.entry_resend_email = ctk.CTkEntry(frame_resend, width=320)
        self.entry_resend_email.insert(0, cfg.get("resend_remetente_email", "onboarding@resend.dev"))
        self.entry_resend_email.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_resend, text="Nome do remetente:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.entry_resend_nome = ctk.CTkEntry(frame_resend, width=320)
        self.entry_resend_nome.insert(0, cfg.get("resend_remetente_nome", "DIGEP - UnDF"))
        self.entry_resend_nome.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        lbl_dica_resend = ctk.CTkLabel(
            frame_resend,
            text=(
                "Dica: crie uma conta gratuita em resend.com, gere uma API Key e verifique um domínio\n"
                "(ou use o domínio de teste onboarding@resend.dev — nesse caso, a Resend só entrega\n"
                "e-mails para o endereço cadastrado na sua própria conta Resend, até verificar um domínio).\n"
                "Não precisa de usuário/senha de e-mail — apenas a API Key."
            ),
            text_color="gray", justify="left"
        )
        lbl_dica_resend.grid(row=4, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

        frame_botoes_resend = ctk.CTkFrame(self.tab_config)
        frame_botoes_resend.pack(fill="x", padx=20)

        btn_testar_resend = ctk.CTkButton(
            frame_botoes_resend, text="🔌 Testar API Key Resend",
            command=self.testar_conexao_resend, fg_color="#1f538d", hover_color="#14375e"
        )
        btn_testar_resend.pack(side="left", padx=(0, 10), pady=10)

        btn_salvar = ctk.CTkButton(frame_botoes_resend, text="💾 Salvar Configuração", command=self.salvar_config_smtp, fg_color="#2fa572", hover_color="#1e7e52")
        btn_salvar.pack(side="left", pady=10)

        self.lbl_status_resend = ctk.CTkLabel(self.tab_config, text="", text_color="gray")
        self.lbl_status_resend.pack(padx=20, pady=(0, 10), anchor="w")

        # ---- Seção SMTP (alternativa) ----
        frame = ctk.CTkFrame(self.tab_config)
        frame.pack(fill="x", padx=20, pady=(10, 20))

        ctk.CTkLabel(frame, text="Envio via SMTP (alternativa)", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=(5, 20), sticky="w"
        )

        ctk.CTkLabel(frame, text="Servidor SMTP (host):").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.entry_smtp_host = ctk.CTkEntry(frame, width=280)
        self.entry_smtp_host.insert(0, cfg.get("smtp_host", ""))
        self.entry_smtp_host.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame, text="Porta:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.entry_smtp_port = ctk.CTkEntry(frame, width=280)
        self.entry_smtp_port.insert(0, cfg.get("smtp_port", "587"))
        self.entry_smtp_port.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame, text="Usuário / E-mail de envio:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.entry_smtp_user = ctk.CTkEntry(frame, width=280)
        self.entry_smtp_user.insert(0, cfg.get("smtp_username", ""))
        self.entry_smtp_user.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame, text="Senha / Senha de aplicativo:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.entry_smtp_pass = ctk.CTkEntry(frame, width=280, show="*")
        self.entry_smtp_pass.insert(0, cfg.get("smtp_password", ""))
        self.entry_smtp_pass.grid(row=4, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame, text="Nome do remetente:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.entry_smtp_remetente = ctk.CTkEntry(frame, width=280)
        self.entry_smtp_remetente.insert(0, cfg.get("smtp_remetente_nome", "DIGEP - UnDF"))
        self.entry_smtp_remetente.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        self.var_use_tls = ctk.BooleanVar(value=str(cfg.get("smtp_use_tls", "1")).lower() in ("1", "true", "sim"))
        chk_tls = ctk.CTkCheckBox(frame, text="Usar STARTTLS (recomendado para porta 587)", variable=self.var_use_tls)
        chk_tls.grid(row=6, column=0, columnspan=2, padx=10, pady=8, sticky="w")

        lbl_dica = ctk.CTkLabel(
            frame,
            text=(
                "Dica: para Gmail/Office365, gere uma 'senha de aplicativo' — não use a senha normal da conta.\n"
                "Gmail: smtp.gmail.com, porta 587, STARTTLS.  Office365: smtp.office365.com, porta 587, STARTTLS."
            ),
            text_color="gray", justify="left"
        )
        lbl_dica.grid(row=7, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

        frame_botoes = ctk.CTkFrame(self.tab_config)
        frame_botoes.pack(fill="x", padx=20)

        btn_testar = ctk.CTkButton(frame_botoes, text="🔌 Testar Conexão SMTP", command=self.testar_conexao_smtp, fg_color="#1f538d", hover_color="#14375e")
        btn_testar.pack(side="left", padx=(0, 10), pady=10)

        self.lbl_status_smtp = ctk.CTkLabel(self.tab_config, text="", text_color="gray")
        self.lbl_status_smtp.pack(padx=20, pady=(0, 10), anchor="w")

    def _config_smtp_do_formulario(self):
        return {
            "smtp_host": self.entry_smtp_host.get().strip(),
            "smtp_port": self.entry_smtp_port.get().strip() or "587",
            "smtp_username": self.entry_smtp_user.get().strip(),
            "smtp_password": self.entry_smtp_pass.get(),
            "smtp_remetente_nome": self.entry_smtp_remetente.get().strip() or "DIGEP - UnDF",
            "smtp_use_tls": "1" if self.var_use_tls.get() else "0",
            "resend_api_key": self.entry_resend_key.get().strip(),
            "resend_remetente_email": self.entry_resend_email.get().strip(),
            "resend_remetente_nome": self.entry_resend_nome.get().strip() or "DIGEP - UnDF",
        }

    def testar_conexao_smtp(self):
        cfg = self._config_smtp_do_formulario()
        self.lbl_status_smtp.configure(text="Testando conexão...", text_color="gray")
        self.update_idletasks()
        ok, msg = test_smtp_connection(cfg)
        cor = "#2fa572" if ok else "#c0392b"
        self.lbl_status_smtp.configure(text=msg, text_color=cor)

    def testar_conexao_resend(self):
        cfg = self._config_smtp_do_formulario()
        self.lbl_status_resend.configure(text="Testando API Key...", text_color="gray")
        self.update_idletasks()
        ok, msg = test_resend_connection(cfg)
        cor = "#2fa572" if ok else "#c0392b"
        self.lbl_status_resend.configure(text=msg, text_color=cor)

    def salvar_config_smtp(self):
        cfg = self._config_smtp_do_formulario()
        cfg["metodo_envio"] = getattr(self, "var_metodo", ctk.StringVar(value="Resend")).get()
        save_smtp_config(cfg)
        messagebox.showinfo("Configurações", "Configuração de e-mail salva com sucesso.")


if __name__ == "__main__":
    app = AppDIGEP()
    app.mainloop()
