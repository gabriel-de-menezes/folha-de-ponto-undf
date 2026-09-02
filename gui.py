import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sqlite3

from db import init_db, get_connection
from excel_service import parse_and_import_excel
from docx_service import fill_folha_docx
from pdf_service import convert_docx_to_pdf
from ocr_service import process_scanned_file
from email_service import send_email_smtp, send_email_outlook, registrar_envio

# Configurações globais do CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class AppDIGEP(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        init_db()
        
        self.title("DIGEP — Sistema de Gestão de Folhas de Ponto (UnDF)")
        self.geometry("1100x720")
        self.minsize(900, 600)
        
        # Atributos de estado
        self.modelo_path = os.path.abspath("Modelo de folha de ponto - Exemplo.docx")
        
        self.setup_ui()
        self.carregar_servidores()
        self.carregar_acumuladores()
        self.carregar_auditoria()

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
        
        self.tab_servidores = self.tabview.add("📥 Servidores (Excel)")
        self.tab_gerar = self.tabview.add("📄 Gerar Folhas de Ponto")
        self.tab_ocr = self.tabview.add("🔍 OCR & Digitalizações")
        self.tab_email = self.tabview.add("✉️ Envio Acumuladores")
        self.tab_auditoria = self.tabview.add("📊 Consultas & Auditoria")

        self.setup_tab_servidores()
        self.setup_tab_gerar()
        self.setup_tab_ocr()
        self.setup_tab_email()
        self.setup_tab_auditoria()

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
        self.tree_servidores.column("nome", width=250)
        self.tree_servidores.column("matricula", width=110, anchor="center")
        self.tree_servidores.column("cpf", width=120, anchor="center")
        self.tree_servidores.column("email", width=200)
        self.tree_servidores.column("carga_horaria", width=100, anchor="center")
        self.tree_servidores.column("acumula_cargo", width=110, anchor="center")
        
        self.tree_servidores.pack(fill="both", expand=True, padx=10, pady=10)

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

    def carregar_servidores(self):
        for item in self.tree_servidores.get_children():
            self.tree_servidores.delete(item)
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, matricula, cpf, email, carga_horaria, acumula_cargo FROM servidores ORDER BY nome")
        for row in cursor.fetchall():
            self.tree_servidores.insert("", "end", values=tuple(row))
        conn.close()

    # ==================== ABA 2: GERAR FOLHAS DE PONTO ====================
    def setup_tab_gerar(self):
        frame_config = ctk.CTkFrame(self.tab_gerar)
        frame_config.pack(fill="x", padx=10, pady=10)
        
        lbl_comp = ctk.CTkLabel(frame_config, text="Competência (Mês/Ano):", font=ctk.CTkFont(weight="bold"))
        lbl_comp.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.entry_competencia = ctk.CTkEntry(frame_config, placeholder_text="Ex: JULHO/2026", width=200)
        self.entry_competencia.insert(0, "JULHO/2026")
        self.entry_competencia.grid(row=0, column=1, padx=10, pady=10)

        lbl_mod = ctk.CTkLabel(frame_config, text="Modelo .docx:", font=ctk.CTkFont(weight="bold"))
        lbl_mod.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.lbl_modelo_path = ctk.CTkLabel(frame_config, text=os.path.basename(self.modelo_path), text_color="gray")
        self.lbl_modelo_path.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        btn_sel_modelo = ctk.CTkButton(frame_config, text="Escolher Modelo .docx", command=self.selecionar_modelo)
        btn_sel_modelo.grid(row=1, column=2, padx=10, pady=10)

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

    def selecionar_modelo(self):
        f = filedialog.askopenfilename(title="Selecione o modelo .docx", filetypes=[("Documentos Word", "*.docx")])
        if f:
            self.modelo_path = f
            self.lbl_modelo_path.configure(text=os.path.basename(f))

    def gerar_folhas_todas(self):
        competencia = self.entry_competencia.get().strip()
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
                
                # Salva registro no SQLite
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
        self.carregar_auditoria()

    # ==================== ABA 3: OCR & DIGITALIZAÇÕES ====================
    def setup_tab_ocr(self):
        frame_top = ctk.CTkFrame(self.tab_ocr)
        frame_top.pack(fill="x", padx=10, pady=10)
        
        btn_upload = ctk.CTkButton(
            frame_top, 
            text="📥 Upload em Lote de Digitalizações (PDF/Imagens)", 
            command=self.upload_digitalizacoes,
            fg_color="#2fa572", hover_color="#1e7e52"
        )
        btn_upload.pack(side="left", padx=10, pady=10)

        # Tabela de Folhas Digitalizadas
        columns = ("id", "caminho", "servidor", "competencia", "status")
        self.tree_ocr = ttk.Treeview(self.tab_ocr, columns=columns, show="headings", height=14)
        
        self.tree_ocr.heading("id", text="ID")
        self.tree_ocr.heading("caminho", text="Arquivo")
        self.tree_ocr.heading("servidor", text="Servidor Associado")
        self.tree_ocr.heading("competencia", text="Competência")
        self.tree_ocr.heading("status", text="Status OCR")

        self.tree_ocr.column("id", width=40, anchor="center")
        self.tree_ocr.column("caminho", width=300)
        self.tree_ocr.column("servidor", width=250)
        self.tree_ocr.column("competencia", width=120, anchor="center")
        self.tree_ocr.column("status", width=140, anchor="center")

        self.tree_ocr.pack(fill="both", expand=True, padx=10, pady=10)

    def upload_digitalizacoes(self):
        files = filedialog.askopenfilenames(
            title="Selecione os arquivos digitalizados",
            filetypes=[("Arquivos Suportados", "*.pdf *.png *.jpg *.jpeg *.tif *.tiff")]
        )
        if files:
            for f in files:
                process_scanned_file(f)
            messagebox.showinfo("OCR", f"{len(files)} arquivos digitalizados processados por OCR com sucesso.")
            self.carregar_ocr()

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

    # ==================== ABA 4: ENVIO ACUMULADORES ====================
    def setup_tab_email(self):
        frame_opts = ctk.CTkFrame(self.tab_email)
        frame_opts.pack(fill="x", padx=10, pady=10)
        
        lbl_metodo = ctk.CTkLabel(frame_opts, text="Método de Envio:", font=ctk.CTkFont(weight="bold"))
        lbl_metodo.grid(row=0, column=0, padx=10, pady=10)
        
        self.var_metodo = ctk.StringVar(value="Outlook")
        rb_outlook = ctk.CTkRadioButton(frame_opts, text="MS Outlook Desktop (Windows)", variable=self.var_metodo, value="Outlook")
        rb_outlook.grid(row=0, column=1, padx=10, pady=10)
        
        rb_smtp = ctk.CTkRadioButton(frame_opts, text="Servidor SMTP (Gmail/Office365/UnDF)", variable=self.var_metodo, value="SMTP")
        rb_smtp.grid(row=0, column=2, padx=10, pady=10)

        btn_enviar_acum = ctk.CTkButton(
            self.tab_email, 
            text="📧 Enviar Folhas de Ponto para Servidores Acumuladores",
            command=self.enviar_emails_acumuladores,
            height=40, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2fa572", hover_color="#1e7e52"
        )
        btn_enviar_acum.pack(fill="x", padx=10, pady=10)

        # Tabela de Acumuladores
        columns = ("id", "nome", "matricula", "email", "status_envio")
        self.tree_acumuladores = ttk.Treeview(self.tab_email, columns=columns, show="headings", height=12)
        
        self.tree_acumuladores.heading("id", text="ID")
        self.tree_acumuladores.heading("nome", text="Servidor (Acumulador)")
        self.tree_acumuladores.heading("matricula", text="Matrícula")
        self.tree_acumuladores.heading("email", text="E-mail Pessoal")
        self.tree_acumuladores.heading("status_envio", text="Status Envio")

        self.tree_acumuladores.column("id", width=40, anchor="center")
        self.tree_acumuladores.column("nome", width=250)
        self.tree_acumuladores.column("matricula", width=120, anchor="center")
        self.tree_acumuladores.column("email", width=220)
        self.tree_acumuladores.column("status_envio", width=150, anchor="center")

        self.tree_acumuladores.pack(fill="both", expand=True, padx=10, pady=10)

    def carregar_acumuladores(self):
        for item in self.tree_acumuladores.get_children():
            self.tree_acumuladores.delete(item)
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.nome, s.matricula, s.email, 
                   COALESCE(l.status, 'Pendente') as status_envio
            FROM servidores s
            LEFT JOIN logs_envio l ON s.id = l.servidor_id
            WHERE LOWER(s.acumula_cargo) = 'sim'
        """)
        for row in cursor.fetchall():
            self.tree_acumuladores.insert("", "end", values=tuple(row))
        conn.close()

    def enviar_emails_acumuladores(self):
        competencia = self.entry_competencia.get().strip()
        metodo = self.var_metodo.get()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servidores WHERE LOWER(acumula_cargo) = 'sim'")
        acumuladores = cursor.fetchall()
        conn.close()

        if not acumuladores:
            messagebox.showinfo("Envio", "Nenhum servidor com acúmulo de cargo encontrado.")
            return

        sucesso_count = 0
        for s in acumuladores:
            s_dict = dict(s)
            destinatario = s_dict['email']
            
            if not destinatario:
                registrar_envio(s_dict['id'], competencia, "Sem E-mail", "Erro", "E-mail não cadastrado.")
                continue

            # Busca o arquivo de folha gerado
            conn = get_connection()
            c_cur = conn.cursor()
            c_cur.execute("""
                SELECT caminho_pdf, caminho_docx FROM folhas_geradas 
                WHERE servidor_id = ? AND competencia = ? 
                ORDER BY id DESC LIMIT 1
            """, (s_dict['id'], competencia))
            folha = c_cur.fetchone()
            conn.close()

            anexo = None
            if folha:
                anexo = folha['caminho_pdf'] or folha['caminho_docx']

            assunto = f"Folha de Ponto - UnDF ({competencia}) - {s_dict['nome']}"
            corpo = f"Prezado(a) Prof.(a) {s_dict['nome']},\n\nSegue em anexo a sua folha de ponto referente à competência {competencia} para fins de comprovação de acúmulo de cargo.\n\nAtenciosamente,\nDiretoria de Gestão de Pessoas - DIGEP/UnDF"

            if metodo == "Outlook":
                ok, msg = send_email_outlook(destinatario, assunto, corpo, anexo)
            else:
                ok, msg = False, "Configuração SMTP requerida."

            status = "Enviado" if ok else "Erro"
            registrar_envio(s_dict['id'], competencia, destinatario, status, msg)
            if ok:
                sucesso_count += 1

        messagebox.showinfo("Envio de E-mails", f"{sucesso_count}/{len(acumuladores)} e-mails processados.")
        self.carregar_acumuladores()
        self.carregar_auditoria()

    # ==================== ABA 5: CONSULTAS & AUDITORIA ====================
    def setup_tab_auditoria(self):
        lbl_hist = ctk.CTkLabel(self.tab_auditoria, text="📋 Histórico de Auditoria & Envio de Folhas", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_hist.pack(padx=10, pady=10, anchor="w")

        columns = ("id", "servidor", "destinatario", "competencia", "status", "data")
        self.tree_auditoria = ttk.Treeview(self.tab_auditoria, columns=columns, show="headings", height=15)
        
        self.tree_auditoria.heading("id", text="ID")
        self.tree_auditoria.heading("servidor", text="Servidor")
        self.tree_auditoria.heading("destinatario", text="Destinatário")
        self.tree_auditoria.heading("competencia", text="Competência")
        self.tree_auditoria.heading("status", text="Status Envio")
        self.tree_auditoria.heading("data", text="Data/Hora")

        self.tree_auditoria.column("id", width=40, anchor="center")
        self.tree_auditoria.column("servidor", width=220)
        self.tree_auditoria.column("destinatario", width=200)
        self.tree_auditoria.column("competencia", width=120, anchor="center")
        self.tree_auditoria.column("status", width=120, anchor="center")
        self.tree_auditoria.column("data", width=160, anchor="center")

        self.tree_auditoria.pack(fill="both", expand=True, padx=10, pady=10)

    def carregar_auditoria(self):
        for item in self.tree_auditoria.get_children():
            self.tree_auditoria.delete(item)
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.id, s.nome, l.destinatario, l.competencia, l.status, l.enviado_em
            FROM logs_envio l
            JOIN servidores s ON l.servidor_id = s.id
            ORDER BY l.id DESC
        """)
        for row in cursor.fetchall():
            self.tree_auditoria.insert("", "end", values=tuple(row))
        conn.close()

if __name__ == "__main__":
    app = AppDIGEP()
    app.mainloop()
