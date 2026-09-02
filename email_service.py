import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from db import get_connection

def send_email_smtp(smtp_config, to_email, subject, body, attachment_path=None):
    """
    Envia e-mail via servidor SMTP.
    smtp_config = {
        'host': 'smtp.gmail.com',
        'port': 587,
        'username': 'user@example.com',
        'password': 'password',
        'use_tls': True
    }
    """
    msg = MIMEMultipart()
    msg['From'] = smtp_config['username']
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
            
    try:
        server = smtplib.SMTP(smtp_config['host'], int(smtp_config['port']), timeout=15)
        if smtp_config.get('use_tls', True):
            server.starttls()
        server.login(smtp_config['username'], smtp_config['password'])
        server.send_message(msg)
        server.quit()
        return True, "E-mail enviado via SMTP com sucesso."
    except Exception as e:
        return False, f"Falha no envio SMTP: {e}"

def send_email_outlook(to_email, subject, body, attachment_path=None):
    """
    Envia e-mail utilizando o aplicativo Microsoft Outlook Desktop instalado no Windows.
    """
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0) # 0 = olMailItem
        mail.To = to_email
        mail.Subject = subject
        mail.Body = body
        
        if attachment_path and os.path.exists(attachment_path):
            mail.Attachments.Add(os.path.abspath(attachment_path))
            
        mail.Send()
        return True, "E-mail enviado via MS Outlook com sucesso."
    except Exception as e:
        return False, f"Falha no envio via MS Outlook: {e}"

def registrar_envio(servidor_id, competencia, destinatario, status, detalhes_erro=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs_envio (servidor_id, competencia, destinatario, status, detalhes_erro)
        VALUES (?, ?, ?, ?, ?)
    """, (servidor_id, competencia, destinatario, status, detalhes_erro))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Módulo de e-mail carregado.")
