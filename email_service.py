import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
import os

from db import get_connection, get_all_config
from arquivo_service import buscar_folha_arquivada

SMTP_DEFAULTS = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_username": "",
    "smtp_password": "",
    "smtp_use_tls": "1",
    "smtp_remetente_nome": "DIGEP - UnDF",
    "metodo_envio": "SMTP",
}


def get_smtp_config():
    """Carrega a configuração de envio de e-mail salva no banco (aba Configurações)."""
    return get_all_config(SMTP_DEFAULTS)


def save_smtp_config(config):
    from db import set_config
    for chave, valor in config.items():
        set_config(chave, str(valor))


def _build_message(smtp_config, to_email, subject, body, attachment_path=None):
    msg = MIMEMultipart()
    remetente_nome = smtp_config.get("smtp_remetente_nome", "DIGEP - UnDF")
    remetente_email = smtp_config.get("smtp_username", "")
    msg['From'] = formataddr((remetente_nome, remetente_email))
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)

    return msg


def _connect_smtp(smtp_config):
    host = smtp_config['smtp_host']
    port = int(smtp_config.get('smtp_port') or 587)
    use_tls = str(smtp_config.get('smtp_use_tls', '1')).lower() in ('1', 'true', 'sim')

    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(host, port, timeout=15)
        if use_tls:
            server.starttls(context=ssl.create_default_context())

    username = smtp_config.get('smtp_username')
    password = smtp_config.get('smtp_password')
    if username and password:
        server.login(username, password)

    return server


def test_smtp_connection(smtp_config):
    """Testa host/porta/credenciais SMTP sem enviar nenhum e-mail (usado na aba Configurações)."""
    if not smtp_config.get('smtp_host'):
        return False, "Informe o servidor SMTP (host)."
    if not smtp_config.get('smtp_username') or not smtp_config.get('smtp_password'):
        return False, "Informe usuário e senha do SMTP."
    try:
        server = _connect_smtp(smtp_config)
        server.quit()
        return True, "Conexão SMTP realizada e autenticação validada com sucesso."
    except smtplib.SMTPAuthenticationError:
        return False, "Falha na autenticação. Verifique usuário/senha (para Gmail/Office365, use uma senha de aplicativo)."
    except Exception as e:
        return False, f"Falha ao conectar/autenticar no SMTP: {e}"


def send_email_smtp(smtp_config, to_email, subject, body, attachment_path=None):
    """Envia e-mail via servidor SMTP configurado (Gmail, Office365, servidor institucional, etc.)."""
    if not smtp_config.get('smtp_host'):
        return False, "SMTP não configurado. Acesse a aba Configurações."
    if not smtp_config.get('smtp_username') or not smtp_config.get('smtp_password'):
        return False, "Usuário/senha do SMTP não configurados. Acesse a aba Configurações."

    msg = _build_message(smtp_config, to_email, subject, body, attachment_path)

    try:
        server = _connect_smtp(smtp_config)
        server.send_message(msg)
        server.quit()
        return True, "E-mail enviado via SMTP com sucesso."
    except smtplib.SMTPAuthenticationError:
        return False, "Falha na autenticação SMTP. Verifique usuário/senha."
    except smtplib.SMTPRecipientsRefused:
        return False, f"Endereço de destino recusado pelo servidor: {to_email}"
    except Exception as e:
        return False, f"Falha no envio SMTP: {e}"


def send_email_outlook(to_email, subject, body, attachment_path=None):
    """Envia e-mail utilizando o aplicativo Microsoft Outlook Desktop instalado no Windows."""
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = to_email
        mail.Subject = subject
        mail.Body = body

        if attachment_path and os.path.exists(attachment_path):
            mail.Attachments.Add(os.path.abspath(attachment_path))

        mail.Send()
        return True, "E-mail enviado via MS Outlook com sucesso."
    except ImportError:
        return False, "Biblioteca pywin32 não instalada — MS Outlook indisponível."
    except Exception as e:
        return False, f"Falha no envio via MS Outlook: {e}"


def registrar_envio(servidor_id, competencia, destinatario, status, detalhes_erro="", anexo=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs_envio (servidor_id, competencia, destinatario, status, detalhes_erro, anexo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (servidor_id, competencia, destinatario, status, detalhes_erro, anexo))
    conn.commit()
    conn.close()


def enviar_folha_para_acumulador(servidor, competencia, metodo=None, smtp_config=None):
    """
    Função de alto nível (RF10/RF11/RF12): localiza a folha arquivada do servidor para a
    competência informada, envia para o e-mail pessoal cadastrado pelo método configurado
    e registra o resultado (pendente/enviado/erro) no histórico de auditoria.

    servidor: sqlite3.Row ou dict com pelo menos 'id', 'nome', 'email'.
    Retorna (ok: bool, mensagem: str).
    """
    servidor_id = servidor['id']
    nome = servidor['nome']
    destinatario = servidor['email']

    if not destinatario:
        registrar_envio(servidor_id, competencia, "(sem e-mail)", "Erro", "E-mail pessoal não cadastrado.")
        return False, "E-mail pessoal não cadastrado."

    anexo, origem = buscar_folha_arquivada(servidor_id, competencia)
    if not anexo:
        registrar_envio(servidor_id, competencia, destinatario, "Erro",
                         f"Nenhuma folha arquivada encontrada para a competência {competencia}.")
        return False, f"Nenhuma folha arquivada encontrada para {competencia}."

    assunto = f"Folha de Ponto - UnDF ({competencia}) - {nome}"
    corpo = (
        f"Prezado(a) {nome},\n\n"
        f"Segue em anexo a sua folha de ponto referente à competência {competencia}, "
        f"para fins de comprovação de acúmulo de cargo.\n\n"
        f"Atenciosamente,\nDiretoria de Gestão de Pessoas - DIGEP/UnDF"
    )

    cfg = smtp_config or get_smtp_config()
    metodo = metodo or cfg.get('metodo_envio', 'SMTP')

    if metodo == "Outlook":
        ok, msg = send_email_outlook(destinatario, assunto, corpo, anexo)
    else:
        ok, msg = send_email_smtp(cfg, destinatario, assunto, corpo, anexo)

    status = "Enviado" if ok else "Erro"
    registrar_envio(servidor_id, competencia, destinatario, status, msg, anexo)
    return ok, msg


if __name__ == "__main__":
    print("Módulo de e-mail carregado.")
