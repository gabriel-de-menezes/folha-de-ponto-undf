"""Controle de uso simultâneo (lock em pasta compartilhada)."""
import os
import shutil
import tempfile
import unittest

from folha_ponto.infraestrutura.bloqueio import NOME_ARQUIVO, BloqueioDeUso


class Relogio:
    def __init__(self):
        self.agora = 1_800_000_000.0

    def __call__(self):
        return self.agora


class TestBloqueio(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.relogio = Relogio()

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def novo(self, usuario, pc):
        return BloqueioDeUso(self.pasta, usuario, pc, tolerancia=90, relogio=self.relogio)

    def test_segundo_usuario_recebe_aviso(self):
        ana, bia = self.novo("ana", "PC-01"), self.novo("bia", "PC-02")
        self.assertIsNone(ana.adquirir())
        outro = bia.adquirir()
        self.assertEqual((outro.usuario, outro.computador), ("ana", "PC-01"))
        self.assertIn("ana (PC-01)", outro.descricao())
        self.assertFalse(bia.posse)

    def test_liberar_permite_novo_uso(self):
        ana, bia = self.novo("ana", "PC-01"), self.novo("bia", "PC-02")
        ana.adquirir()
        ana.liberar()
        self.assertFalse(os.path.exists(os.path.join(self.pasta, NOME_ARQUIVO)))
        self.assertIsNone(bia.adquirir())

    def test_lock_velho_de_queda_abrupta_nao_vale(self):
        ana, bia = self.novo("ana", "PC-01"), self.novo("bia", "PC-02")
        ana.adquirir()
        self.relogio.agora += 91  # ninguém renovou: o programa da Ana caiu
        self.assertIsNone(bia.adquirir())
        self.assertTrue(bia.posse)

    def test_batimento_mantem_o_lock_valido(self):
        ana, bia = self.novo("ana", "PC-01"), self.novo("bia", "PC-02")
        ana.adquirir()
        for _ in range(5):
            self.relogio.agora += 60
            self.assertIsNone(ana.renovar())
        self.assertIsNotNone(bia.adquirir())

    def test_quem_nao_e_dono_nao_apaga_o_lock(self):
        ana, bia = self.novo("ana", "PC-01"), self.novo("bia", "PC-02")
        ana.adquirir()
        bia.adquirir()
        bia.liberar()
        self.assertTrue(os.path.exists(os.path.join(self.pasta, NOME_ARQUIVO)))

    def test_mesmo_usuario_em_duas_janelas_tambem_avisa(self):
        a1, a2 = self.novo("ana", "PC-01"), self.novo("ana", "PC-01")
        a1.adquirir()
        self.assertIsNotNone(a2.adquirir())


if __name__ == "__main__":
    unittest.main()
