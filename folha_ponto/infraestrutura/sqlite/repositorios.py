"""Implementações SQLite das portas de persistência."""
import sqlite3
from contextlib import contextmanager
from datetime import date

from ...dominio.calendario import DataEspecial
from ...dominio.entidades import (
    EventoOperacao, FolhaArquivada, ItemOperacao, Operacao, RegistroEnvio, Servidor,
)
from ...dominio.regras import MatriculaDuplicada
from .banco import utc_para_local


class _Base:
    def __init__(self, banco):
        self.banco = banco

    @contextmanager
    def _conexao(self):
        conn = self.banco.conectar()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _todos(self, sql, params=()):
        with self._conexao() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def _um(self, sql, params=()):
        linhas = self._todos(sql, params)
        return linhas[0] if linhas else None


def _servidor(linha):
    return Servidor(id=linha["id"], **{c: linha[c] or "" for c in Servidor.CAMPOS}) if linha else None


class RepositorioServidoresSQLite(_Base):
    def listar(self, busca=""):
        termo = (busca or "").strip()
        digitos = "".join(c for c in termo if c.isdigit())
        return [_servidor(r) for r in self._todos("""
            SELECT * FROM servidores
            WHERE IFNULL(ativo, 1) = 1
              AND (SEM_ACENTO(nome) LIKE SEM_ACENTO(:like) OR matricula LIKE :like OR IFNULL(cpf, '') LIKE :like
                   OR (:digitos <> '' AND REPLACE(REPLACE(IFNULL(cpf, ''), '.', ''), '-', '') LIKE :dig)
                   OR IFNULL(email, '') LIKE :like)
            ORDER BY nome
        """, {"like": f"%{termo}%", "digitos": digitos, "dig": f"%{digitos}%"})]

    def obter(self, servidor_id):
        return _servidor(self._um("SELECT * FROM servidores WHERE id = ?", (servidor_id,)))

    def contar(self):
        return self._um("SELECT COUNT(*) AS n FROM servidores WHERE IFNULL(ativo, 1) = 1")["n"]

    def remover(self, servidor_id):
        """Remoção lógica: o servidor some das listas, mas folhas e envios já registrados mantêm o nome."""
        with self._conexao() as conn:
            conn.execute("UPDATE servidores SET ativo = 0 WHERE id = ?", (servidor_id,))

    def remover_todos(self):
        """Remoção lógica de todos os servidores ativos. Devolve quantos foram removidos."""
        with self._conexao() as conn:
            return conn.execute("UPDATE servidores SET ativo = 0 WHERE IFNULL(ativo, 1) = 1").rowcount

    def salvar(self, servidor):
        campos = Servidor.CAMPOS
        try:
            with self._conexao() as conn:
                if servidor.id:
                    conn.execute(f"UPDATE servidores SET {', '.join(f'{c} = ?' for c in campos)} WHERE id = ?",
                                 (*[getattr(servidor, c) for c in campos], servidor.id))
                elif (antigo := conn.execute("SELECT id FROM servidores WHERE matricula = ? AND IFNULL(ativo, 1) = 0",
                                             (servidor.matricula,)).fetchone()):
                    servidor.id = antigo["id"]  # matrícula de um servidor removido: reativa o cadastro
                    conn.execute(f"UPDATE servidores SET ativo = 1, {', '.join(f'{c} = ?' for c in campos)} WHERE id = ?",
                                 (*[getattr(servidor, c) for c in campos], servidor.id))
                else:
                    cur = conn.execute(f"INSERT INTO servidores ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})",
                                       tuple(getattr(servidor, c) for c in campos))
                    servidor.id = cur.lastrowid
        except sqlite3.IntegrityError:
            raise MatriculaDuplicada("Já existe outro servidor com essa matrícula.")

    def importar(self, dados):
        """Insere ou atualiza pela matrícula apenas os campos presentes em `dados`. -> (id, novo?)"""
        with self._conexao() as conn:
            existente = conn.execute("SELECT id FROM servidores WHERE matricula = ? AND IFNULL(ativo, 1) = 1",
                                     (dados["matricula"],)).fetchone()
            dados = {**dados, "ativo": 1}  # reimportar um servidor removido o reativa
            colunas = list(dados)
            atualizar = ", ".join(f"{c} = excluded.{c}" for c in colunas if c != "matricula")
            conn.execute(f"""
                INSERT INTO servidores ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})
                ON CONFLICT(matricula) DO UPDATE SET {atualizar}
            """, tuple(dados.values()))
            servidor_id = conn.execute("SELECT id FROM servidores WHERE matricula = ?", (dados["matricula"],)).fetchone()[0]
        return servidor_id, existente is None


class RepositorioFolhasSQLite(_Base):
    def registrar_gerada(self, servidor_id, competencia, docx, pdf):
        with self._conexao() as conn:
            conn.execute("DELETE FROM folhas_geradas WHERE servidor_id = ? AND competencia = ?", (servidor_id, competencia))
            conn.execute("INSERT INTO folhas_geradas (servidor_id, competencia, caminho_docx, caminho_pdf) VALUES (?, ?, ?, ?)",
                         (servidor_id, competencia, docx, pdf))

    def digitalizada_por_hash(self, hash_arquivo):
        return self._um("SELECT * FROM folhas_digitalizadas WHERE hash_arquivo = ? ORDER BY id DESC LIMIT 1", (hash_arquivo,))

    def registrar_digitalizada(self, caminho, servidor_id, competencia, status, texto, hash_arquivo, metodo):
        with self._conexao() as conn:
            cur = conn.execute("""
                INSERT INTO folhas_digitalizadas (caminho_arquivo, servidor_id, competencia, status_ocr, texto_extraido,
                                                  hash_arquivo, metodo_identificacao)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (caminho, servidor_id, competencia, status, texto, hash_arquivo, metodo))
            return cur.lastrowid

    def vincular_digitalizada(self, doc_id, servidor_id, competencia, status, caminho=None):
        with self._conexao() as conn:
            conn.execute("""
                UPDATE folhas_digitalizadas SET servidor_id = ?, competencia = ?, status_ocr = ?,
                       caminho_arquivo = COALESCE(?, caminho_arquivo), atualizado_em = CURRENT_TIMESTAMP WHERE id = ?
            """, (servidor_id, competencia, status, caminho, doc_id))

    def substituir_digitalizada(self, caminho, novo_caminho):
        """A folha arquivada em `caminho` virou backup (_OLD_): deixa de aparecer como folha vigente."""
        with self._conexao() as conn:
            conn.execute("""UPDATE folhas_digitalizadas SET caminho_arquivo = ?, status_ocr = 'Substituída',
                            atualizado_em = CURRENT_TIMESTAMP WHERE caminho_arquivo = ?""", (novo_caminho, caminho))

    def listar_arquivadas(self, termo="", competencia=""):
        rows = self._todos("""
            SELECT f.id, 'Digitalizada' AS origem, s.nome, s.matricula, f.competencia,
                   f.caminho_arquivo AS caminho, COALESCE(f.atualizado_em, f.criado_em) AS data_registro
            FROM folhas_digitalizadas f JOIN servidores s ON f.servidor_id = s.id
            WHERE f.status_ocr IN ('Validado', 'Processado')
              AND (SEM_ACENTO(s.nome) LIKE SEM_ACENTO(:like) OR s.matricula LIKE :like)
              AND (:comp IS NULL OR f.competencia = :comp)
            UNION ALL
            SELECT g.id, 'Gerada' AS origem, s.nome, s.matricula, g.competencia,
                   COALESCE(g.caminho_pdf, g.caminho_docx) AS caminho, g.gerado_em AS data_registro
            FROM folhas_geradas g JOIN servidores s ON g.servidor_id = s.id
            WHERE (SEM_ACENTO(s.nome) LIKE SEM_ACENTO(:like) OR s.matricula LIKE :like)
              AND (:comp IS NULL OR g.competencia = :comp)
            ORDER BY data_registro DESC
        """, {"like": f"%{(termo or '').strip()}%", "comp": competencia or None})
        return [FolhaArquivada(**{**r, "data_registro": utc_para_local(r["data_registro"])}) for r in rows]

    def servidores_com_folha_assinada(self, competencia):
        """Ids dos servidores que já têm folha assinada arquivada (conferida) no mês."""
        return {r["servidor_id"] for r in self._todos("""
            SELECT DISTINCT servidor_id FROM folhas_digitalizadas
            WHERE competencia = ? AND status_ocr = 'Validado' AND servidor_id IS NOT NULL
        """, (competencia,))}

    def competencias(self):
        rows = self._todos("""
            SELECT competencia FROM folhas_geradas WHERE competencia <> ''
            UNION SELECT competencia FROM folhas_digitalizadas WHERE competencia <> '' AND servidor_id IS NOT NULL
        """)
        return [r["competencia"] for r in rows]


_CAMPOS_OPERACAO = ("tipo", "competencia", "iniciado_em", "status", "concluido_em", "usuario", "computador", "origem",
                    "origem_hash", "metodo_envio", "relatorio")
_CAMPOS_ITEM = ("servidor_id", "nome", "matricula", "cpf", "email", "competencia", "arquivo", "arquivo_hash", "identificacao",
                "observacao", "selecionado", "envio_status", "envio_detalhe", "enviado_em")


class RepositorioOperacoesSQLite(_Base):
    def criar(self, operacao):
        with self._conexao() as conn:
            cur = conn.execute(f"INSERT INTO operacoes ({', '.join(_CAMPOS_OPERACAO)}) VALUES ({', '.join('?' * len(_CAMPOS_OPERACAO))})",
                               tuple(getattr(operacao, c) for c in _CAMPOS_OPERACAO))
            operacao.id = cur.lastrowid
            return operacao.id

    def atualizar(self, op_id, **campos):
        invalidos = set(campos) - set(_CAMPOS_OPERACAO)
        if invalidos:
            raise ValueError(f"Campos inválidos: {invalidos}")
        if campos:
            with self._conexao() as conn:
                conn.execute(f"UPDATE operacoes SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?", (*campos.values(), op_id))

    _SELECT = """
        SELECT o.*,
               (SELECT COUNT(*) FROM operacao_itens i WHERE i.operacao_id = o.id AND i.servidor_id IS NOT NULL) AS qtd_itens,
               (SELECT COUNT(*) FROM operacao_itens i WHERE i.operacao_id = o.id AND i.envio_status = 'Enviado') AS qtd_enviados,
               (SELECT COUNT(*) FROM operacao_itens i WHERE i.operacao_id = o.id AND i.envio_status = 'Erro') AS qtd_erros
        FROM operacoes o
    """

    @staticmethod
    def _operacao(r):
        dados = {k: r[k] for k in ("id", *_CAMPOS_OPERACAO, "qtd_itens", "qtd_enviados", "qtd_erros")}
        for k in ("usuario", "computador", "origem", "origem_hash", "metodo_envio", "relatorio"):
            dados[k] = dados[k] or ""
        return Operacao(**dados)

    def obter(self, op_id):
        r = self._um(self._SELECT + " WHERE o.id = ?", (op_id,))
        return self._operacao(r) if r else None

    def listar(self):
        return [self._operacao(r) for r in self._todos(self._SELECT + " ORDER BY o.id DESC")]

    def registrar_evento(self, op_id, momento, descricao):
        with self._conexao() as conn:
            conn.execute("INSERT INTO operacao_eventos (operacao_id, momento, descricao) VALUES (?, ?, ?)",
                         (op_id, momento, descricao))

    def eventos(self, op_id):
        return [EventoOperacao(r["momento"], r["descricao"])
                for r in self._todos("SELECT * FROM operacao_eventos WHERE operacao_id = ? ORDER BY id", (op_id,))]

    def salvar_itens(self, op_id, itens):
        """Grava o retrato atual dos servidores/folhas da operação (substitui o anterior)."""
        with self._conexao() as conn:
            conn.execute("DELETE FROM operacao_itens WHERE operacao_id = ?", (op_id,))
            conn.executemany(
                f"INSERT INTO operacao_itens (operacao_id, {', '.join(_CAMPOS_ITEM)}) VALUES (?, {', '.join('?' * len(_CAMPOS_ITEM))})",
                [(op_id, *[int(getattr(i, c)) if c == "selecionado" else getattr(i, c) for c in _CAMPOS_ITEM]) for i in itens])

    def itens(self, op_id):
        rows = self._todos("SELECT * FROM operacao_itens WHERE operacao_id = ? ORDER BY servidor_id IS NULL, nome", (op_id,))
        return [ItemOperacao(**{c: (bool(r[c]) if c == "selecionado" else (r[c] or "" if c == "competencia" else r[c]))
                               for c in _CAMPOS_ITEM}) for r in rows]


class RepositorioEnviosSQLite(_Base):
    def registrar(self, servidor_id, competencia, destinatario, status, detalhes, anexo, operacao_id):
        with self._conexao() as conn:
            conn.execute("""
                INSERT INTO logs_envio (servidor_id, competencia, destinatario, status, detalhes_erro, anexo, operacao_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (servidor_id, competencia, destinatario, status, detalhes, anexo, operacao_id))

    def listar(self, busca="", status=""):
        """Histórico de envios, do mais recente para o mais antigo. `busca` filtra por nome, CPF ou matrícula."""
        termo = (busca or "").strip()
        digitos = "".join(c for c in termo if c.isdigit())
        rows = self._todos("""
            SELECT l.*, s.nome, s.matricula, s.cpf FROM logs_envio l JOIN servidores s ON s.id = l.servidor_id
            WHERE (:termo = '' OR SEM_ACENTO(s.nome) LIKE SEM_ACENTO(:like) OR s.matricula LIKE :like
                   OR (:digitos <> '' AND REPLACE(REPLACE(IFNULL(s.cpf, ''), '.', ''), '-', '') LIKE :dig)
                   OR IFNULL(s.cpf, '') LIKE :like)
              AND (:status = '' OR l.status = :status)
            ORDER BY l.id DESC
        """, {"termo": termo, "like": f"%{termo}%", "digitos": digitos, "dig": f"%{digitos}%", "status": status or ""})
        return [RegistroEnvio(id=r["id"], servidor_id=r["servidor_id"], nome=r["nome"], competencia=r["competencia"],
                              destinatario=r["destinatario"], status=r["status"], detalhes=r["detalhes_erro"] or "",
                              anexo=r["anexo"], enviado_em=utc_para_local(r["enviado_em"]), operacao_id=r["operacao_id"],
                              matricula=r["matricula"] or "", cpf=r["cpf"] or "")
                for r in rows]

    def situacao_por_servidor_mes(self):
        """{(servidor_id, competencia): "Enviado" | "Erro"} — Enviado se algum envio deu certo, senão Erro."""
        situacao = {}
        for r in self._todos("SELECT servidor_id, competencia, status FROM logs_envio ORDER BY id"):
            chave = (r["servidor_id"], r["competencia"])
            if situacao.get(chave) != "Enviado":
                situacao[chave] = r["status"]
        return situacao


class RepositorioConfiguracoesSQLite(_Base):
    def obter(self, chave, padrao=""):
        r = self._um("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
        return r["valor"] if r and r["valor"] is not None else padrao

    def definir(self, chave, valor):
        with self._conexao() as conn:
            conn.execute("""INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
                            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor""", (chave, valor))


class RepositorioCalendarioSQLite(_Base):
    @staticmethod
    def _data(r):
        return DataEspecial(date.fromisoformat(r["data"]), r["especificacao"])

    def listar(self, ano=None):
        if ano:
            rows = self._todos("SELECT * FROM datas_especiais WHERE data LIKE ? ORDER BY data", (f"{int(ano):04d}-%",))
        else:
            rows = self._todos("SELECT * FROM datas_especiais ORDER BY data")
        return [self._data(r) for r in rows]

    def anos(self):
        return [int(r["ano"]) for r in self._todos(
            "SELECT DISTINCT substr(data, 1, 4) AS ano FROM datas_especiais ORDER BY ano")]

    def obter(self, data):
        r = self._um("SELECT * FROM datas_especiais WHERE data = ?", (data.isoformat(),))
        return self._data(r) if r else None

    def salvar(self, data, especificacao):
        with self._conexao() as conn:
            conn.execute("""INSERT INTO datas_especiais (data, especificacao) VALUES (?, ?)
                            ON CONFLICT(data) DO UPDATE SET especificacao = excluded.especificacao""",
                         (data.isoformat(), especificacao))

    def remover(self, data):
        with self._conexao() as conn:
            conn.execute("DELETE FROM datas_especiais WHERE data = ?", (data.isoformat(),))
