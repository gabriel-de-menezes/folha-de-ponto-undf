import os
import shutil

def convert_docx_to_pdf(docx_path, pdf_path):
    """
    Converte um arquivo .docx para .pdf no Windows.
    Primeiro tenta usar a COM API do Microsoft Word (win32com).
    Se o Word não estiver disponível, tenta usar a CLI do LibreOffice (soffice).
    Se nenhum conversor de PDF estiver instalado, mantém o arquivo .docx gerado.
    """
    abs_docx = os.path.abspath(docx_path)
    abs_pdf = os.path.abspath(pdf_path)
    
    os.makedirs(os.path.dirname(abs_pdf), exist_ok=True)
    
    # Tentativa 1: MS Word COM
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(abs_docx)
            doc.SaveAs(abs_pdf, FileFormat=17) # 17 = wdFormatPDF
            doc.Close()
            word.Quit()
            if os.path.exists(abs_pdf):
                return True, abs_pdf
        except Exception as e:
            try:
                word.Quit()
            except:
                pass
    except Exception:
        pass

    # Tentativa 2: LibreOffice CLI (soffice)
    soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice_path:
        try:
            import subprocess
            out_dir = os.path.dirname(abs_pdf)
            res = subprocess.run([soffice_path, '--headless', '--convert-to', 'pdf', abs_docx, '--outdir', out_dir], capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(abs_pdf):
                return True, abs_pdf
        except Exception:
            pass

    # Fallback: Se não conseguir converter em PDF, o arquivo .docx original foi preservado.
    return False, f"O arquivo .docx foi gerado com sucesso. Para exportação direta em PDF, instale o Microsoft Word ou LibreOffice no sistema."

if __name__ == "__main__":
    docx_in = r"output_test\Folha_JOAO_PORTELLA_AGOSTO_2026.docx"
    pdf_out = r"output_test\Folha_JOAO_PORTELLA_AGOSTO_2026.pdf"
    success, msg = convert_docx_to_pdf(docx_in, pdf_out)
    print("Resultado:", success, "| Mensagem:", msg)
