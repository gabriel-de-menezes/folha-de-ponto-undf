"""Controle simples de uso simultâneo: um arquivo de “lock” na pasta do sistema (que pode estar numa pasta de rede).

Quem abre o sistema grava o arquivo e o renova a cada poucos segundos (batimento). Se outra pessoa abrir
enquanto o batimento estiver recente, recebe o aviso “em uso por …”. Se o programa fechar de forma abrupta,
o arquivo fica velho e deixa de valer depois do tempo de tolerância — não é preciso apagar nada à mão."""
import json
import os
import time
import uuid
from dataclasses import dataclass

NOME_ARQUIVO = "folha_ponto.lock"
TOLERANCIA_SEGUNDOS = 90


@dataclass
class UsoAtual:
    usuario: str
    computador: str
    desde: float

    def descricao(self):
        inicio = time.strftime("%d/%m/%Y %H:%M", time.localtime(self.desde))
        return f"{self.usuario} ({self.computador}) desde {inicio}"


class BloqueioDeUso:
    def __init__(self, pasta, usuario, computador, tolerancia=TOLERANCIA_SEGUNDOS, relogio=time.time):
        self.caminho = os.path.join(pasta, NOME_ARQUIVO)
        self.usuario, self.computador = usuario, computador
        self.tolerancia = tolerancia
        self.relogio = relogio
        self.token = uuid.uuid4().hex  # identifica esta execução (mesmo usuário em duas janelas conta como outro)
        self.desde = relogio()
        self.posse = False

    # ---------- leitura ----------
    def _ler(self):
        try:
            with open(self.caminho, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def em_uso_por_outro(self):
        """UsoAtual de quem está com o sistema aberto (diferente desta execução), ou None."""
        dados = self._ler()
        if not dados or dados.get("token") == self.token:
            return None
        if self.relogio() - float(dados.get("batimento", 0)) > self.tolerancia:
            return None  # lock velho: quem o criou fechou sem liberar
        return UsoAtual(dados.get("usuario", "?"), dados.get("computador", "?"), float(dados.get("desde", 0)))

    # ---------- escrita ----------
    def _gravar(self):
        dados = {"token": self.token, "usuario": self.usuario, "computador": self.computador,
                 "desde": self.desde, "batimento": self.relogio()}
        temporario = self.caminho + f".{self.token[:8]}.tmp"
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(dados, f)
        os.replace(temporario, self.caminho)

    def adquirir(self):
        """Tenta assumir o uso. Retorna None se conseguiu, ou o UsoAtual de quem já está usando."""
        outro = self.em_uso_por_outro()
        if outro:
            self.posse = False
            return outro
        try:
            self._gravar()
            self.posse = True
        except OSError:
            self.posse = False  # pasta somente leitura: segue sem controle, sem travar o uso
        return None

    def renovar(self):
        """Batimento periódico. Retorna o UsoAtual se outra pessoa assumiu (ou já estava) em seu lugar."""
        if not self.posse:
            return self.adquirir()
        dados = self._ler()
        if dados and dados.get("token") != self.token:
            self.posse = False
            return self.em_uso_por_outro()
        try:
            self._gravar()
        except OSError:
            pass
        return None

    def liberar(self):
        """Apaga o lock, mas só se ele ainda for desta execução."""
        if not self.posse:
            return
        dados = self._ler()
        if dados and dados.get("token") == self.token:
            try:
                os.remove(self.caminho)
            except OSError:
                pass
        self.posse = False
