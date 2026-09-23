"""Casos de uso de configuração: e-mail e aparência."""
from ..dominio.entidades import ConfiguracaoEmail

# chave no banco -> atributo de ConfiguracaoEmail (chaves mantidas por compatibilidade com bancos antigos)
_CHAVES_EMAIL = {
    "metodo_envio": "metodo", "smtp_host": "host", "smtp_port": "porta", "smtp_username": "usuario",
    "smtp_password": "senha", "smtp_use_tls": "usar_tls", "smtp_remetente_nome": "remetente_nome",
}


class ServicoConfiguracoes:
    def __init__(self, repositorio, servico_email):
        self.repositorio = repositorio
        self.servico_email = servico_email

    def email(self):
        padrao = ConfiguracaoEmail()
        valores = {}
        for chave, atributo in _CHAVES_EMAIL.items():
            atual = getattr(padrao, atributo)
            bruto = self.repositorio.obter(chave, "")
            if bruto == "":
                valores[atributo] = atual
            elif atributo == "usar_tls":
                valores[atributo] = bruto.lower() in ("1", "true", "sim")
            else:
                valores[atributo] = bruto
        if valores["metodo"] not in ConfiguracaoEmail.METODOS:
            valores["metodo"] = "SMTP"  # bancos antigos podem ter "Resend", que foi removido
        return ConfiguracaoEmail(**valores)

    def salvar_email(self, config):
        for chave, atributo in _CHAVES_EMAIL.items():
            valor = getattr(config, atributo)
            self.repositorio.definir(chave, ("1" if valor else "0") if atributo == "usar_tls" else str(valor))

    def testar_email(self, config):
        return self.servico_email.testar(config)

    def aparencia(self):
        return self.repositorio.obter("aparencia", "System")

    def definir_aparencia(self, modo):
        self.repositorio.definir("aparencia", modo)
