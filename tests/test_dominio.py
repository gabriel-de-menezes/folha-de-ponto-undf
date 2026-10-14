import unittest

from folha_ponto.dominio.competencia import normalizar_competencia, rotulo_competencia, separar_competencia
from folha_ponto.dominio.entidades import FolhaAssinada, ItemOperacao, Servidor, TipoOperacao
from folha_ponto.dominio.regras import identificar_servidor, mascarar_cpf, nome_arquivo_folha, pasta_folhas_mes, montar_email, resolver_conflitos


class TestCompetencia(unittest.TestCase):
    def test_normaliza_variacoes(self):
        for entrada in ("julho/2026", "JUL/2026", "Julho 2026", "07/2026", "7-2026", " jul 2026 "):
            self.assertEqual(normalizar_competencia(entrada), "JULHO/2026", entrada)
        self.assertEqual(normalizar_competencia("marco/2026"), "MARÇO/2026")

    def test_texto_invalido_fica_em_maiusculas(self):
        self.assertEqual(normalizar_competencia("abc"), "ABC")
        self.assertEqual(separar_competencia("abc"), (None, None))

    def test_rotulo(self):
        self.assertEqual(rotulo_competencia("FEVEREIRO/2026"), "Fevereiro/2026")


class TestIdentificacao(unittest.TestCase):
    servidores = [Servidor(id=1, nome="Fernanda Rocha Lima", matricula="17289106"),
                  Servidor(id=2, nome="Ana Lima", matricula="1728"),
                  Servidor(id=3, nome="João Pedro Portella", matricula="99887766")]

    def test_por_matricula_com_pontuacao(self):
        self.assertEqual(identificar_servidor("MATRÍCULA: 1.728.910-6", self.servidores)[0], 1)

    def test_matricula_curta_nao_casa_dentro_de_outra(self):
        # "1728" (Ana) aparece dentro de 17289106, mas não isolada
        self.assertEqual(identificar_servidor("MATRICULA 17289106", self.servidores)[0], 1)

    def test_por_nome_com_palavras_separadas_e_acentos(self):
        texto = "NOME DO SERVIDOR: JOAO PEDRO\nfolha de PORTELLA"
        self.assertEqual(identificar_servidor(texto, self.servidores)[0], 3)

    def test_competencia_da_referencia(self):
        _, comp = identificar_servidor("REGISTRO DE FREQUÊNCIA   REFERÊNCIA: AGO/2026", self.servidores)
        self.assertEqual(comp, "AGOSTO/2026")

    def test_nao_identificado(self):
        self.assertEqual(identificar_servidor("texto qualquer", self.servidores), (None, ""))


class TestRegras(unittest.TestCase):
    def test_conflito_deixa_segunda_folha_sem_dono(self):
        a = FolhaAssinada(doc_id=1, caminho="a", hash="1", original="a.pdf", servidor_id=7)
        b = FolhaAssinada(doc_id=2, caminho="b", hash="2", original="b.pdf", servidor_id=7)
        resolver_conflitos([a, b])
        self.assertEqual((a.servidor_id, b.servidor_id), (7, None))
        self.assertIn("Duplicada", b.observacao)

    def test_mesmo_servidor_em_meses_diferentes_nao_conflita(self):
        a = FolhaAssinada(doc_id=1, caminho="a", hash="1", original="a.pdf", servidor_id=7, competencia="JULHO/2026")
        b = FolhaAssinada(doc_id=2, caminho="b", hash="2", original="a.pdf", servidor_id=7, competencia="AGOSTO/2026")
        resolver_conflitos([a, b])
        self.assertEqual((a.servidor_id, b.servidor_id), (7, 7))

    def test_nome_padrao_da_folha(self):
        self.assertEqual(nome_arquivo_folha("  MARIA  da Silva-Sántos ", "JANEIRO/2027"), "Maria_Da_Silva_Santos-2027-01.pdf")
        self.assertEqual(nome_arquivo_folha("D'Ávila / João", "dez/2026"), "D_Avila_Joao-2026-12.pdf")
        self.assertEqual(pasta_folhas_mes("FEVEREIRO/2027"), "Folhas_2027-02")

    def test_mascara_cpf(self):
        self.assertEqual(mascarar_cpf("111.222.333-01"), "111.***.***-01")
        self.assertEqual(mascarar_cpf(""), "—")

    def test_email_por_tipo(self):
        assunto, corpo = montar_email("Ana", "JULHO/2026", TipoOperacao.ASSINADAS)
        self.assertIn("Julho/2026", assunto)
        self.assertIn("assinada", corpo)
        self.assertIn("preenchimento", montar_email("Ana", "JULHO/2026", TipoOperacao.GERACAO)[1])

    def test_item_pode_enviar(self):
        s = Servidor(id=1, nome="Ana", matricula="1", email="a@b.c")
        self.assertTrue(ItemOperacao.de_servidor(s, arquivo="x.pdf").pode_enviar)
        s.email = ""
        self.assertFalse(ItemOperacao.de_servidor(s, arquivo="x.pdf").pode_enviar)


if __name__ == "__main__":
    unittest.main()
