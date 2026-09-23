"""Envio de e-mail por SMTP (Gmail, Office 365, institucional) ou pelo MS Outlook instalado."""
import os
import smtplib
import ssl
from contextlib import ExitStack
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from .com_windows import com_inicializado


def montar_mensagem(config, destino, assunto, corpo, anexo=None):
    msg = MIMEMultipart()
    msg["From"] = formataddr((config.remetente_nome, config.usuario))
    msg["To"] = destino
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo, "plain", "utf-8"))
    if anexo and os.path.exists(anexo):
        with open(anexo, "rb") as f:
            parte = MIMEApplication(f.read())
        # add_header codifica corretamente nomes com acento (RFC 2231)
        parte.add_header("Content-Disposition", "attachment", filename=os.path.basename(anexo))
        msg.attach(parte)
    return msg


def conectar_smtp(config):
    porta = int(config.porta or 587)
    if porta == 465:
        servidor = smtplib.SMTP_SSL(config.host, porta, timeout=30, context=ssl.create_default_context())
    else:
        servidor = smtplib.SMTP(config.host, porta, timeout=30)
        if config.usar_tls:
            servidor.starttls(context=ssl.create_default_context())
    if config.usuario and config.senha:
        servidor.login(config.usuario, config.senha)
    return servidor


class EnviadorSMTP:
    """Reaproveita a mesma conexão para o lote inteiro (mais rápido e evita bloqueio por excesso de logins);
    reconecta uma vez se a conexão cair no meio."""

    def __init__(self, config):
        self.config = config
        self._conexao = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self._conexao is not None:
            try:
                self._conexao.quit()
            except Exception:
                pass
            self._conexao = None

    def enviar(self, destino, assunto, corpo, anexo=None):
        msg = montar_mensagem(self.config, destino, assunto, corpo, anexo)
        for tentativa in (1, 2):
            try:
                if self._conexao is None:
                    self._conexao = conectar_smtp(self.config)
                self._conexao.send_message(msg)
                return True, "E-mail enviado via SMTP."
            except smtplib.SMTPAuthenticationError:
                self._conexao = None
                return False, "Falha na autenticação SMTP. Verifique usuário/senha."
            except smtplib.SMTPRecipientsRefused:
                return False, f"Endereço de destino recusado pelo servidor: {destino}"
            except (smtplib.SMTPServerDisconnected, ConnectionError, OSError) as e:
                self._conexao = None
                if tentativa == 2:
                    return False, f"Falha no envio SMTP: {e}"
            except Exception as e:
                return False, f"Falha no envio SMTP: {e}"
        return False, "Falha no envio SMTP."


class EnviadorOutlook:
    def __init__(self, config):
        self._pilha = ExitStack()
        self._outlook = None

    def __enter__(self):
        self._pilha.enter_context(com_inicializado())
        return self

    def __exit__(self, *exc):
        self._outlook = None
        self._pilha.close()

    def enviar(self, destino, assunto, corpo, anexo=None):
        try:
            if self._outlook is None:
                import win32com.client
                self._outlook = win32com.client.Dispatch("Outlook.Application")
            mail = self._outlook.CreateItem(0)  # 0 = olMailItem
            mail.To, mail.Subject, mail.Body = destino, assunto, corpo
            if anexo and os.path.exists(anexo):
                mail.Attachments.Add(os.path.abspath(anexo))
            mail.Send()
            return True, "E-mail enviado via MS Outlook."
        except ImportError:
            return False, "Biblioteca pywin32 não instalada — MS Outlook indisponível."
        except Exception as e:
            return False, f"Falha no envio via MS Outlook: {e}"


class ServicoEmailPadrao:
    def abrir(self, config):
        return EnviadorOutlook(config) if config.metodo == "Outlook" else EnviadorSMTP(config)

    def testar(self, config):
        """Valida a configuração sem enviar nenhum e-mail."""
        if config.metodo == "Outlook":
            with com_inicializado():
                try:
                    import win32com.client
                    win32com.client.Dispatch("Outlook.Application")
                    return True, "Outlook encontrado e pronto para enviar."
                except Exception as e:
                    return False, f"Outlook indisponível: {e}"
        if not config.host:
            return False, "Informe o servidor SMTP (host)."
        if not config.usuario or not config.senha:
            return False, "Informe usuário e senha do SMTP."
        try:
            conectar_smtp(config).quit()
            return True, "Conexão SMTP realizada e autenticação validada com sucesso."
        except smtplib.SMTPAuthenticationError:
            return False, "Falha na autenticação. Verifique usuário/senha (no Gmail/Office 365, use uma senha de aplicativo)."
        except Exception as e:
            return False, f"Falha ao conectar/autenticar no SMTP: {e}"
