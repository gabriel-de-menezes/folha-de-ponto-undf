"""Comportamentos de instalação: Tesseract que acompanha o sistema e falha ao abrir sem permissão de escrita."""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

import pytesseract

from folha_ponto.infraestrutura import armazenamento, leitor_folhas
from main import mensagem_falha_ao_abrir


class TestInstalacao(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        cmd_original = pytesseract.pytesseract.tesseract_cmd
        self.addCleanup(setattr, pytesseract.pytesseract, "tesseract_cmd", cmd_original)
        ambiente = mock.patch.dict(os.environ)
        ambiente.start()
        self.addCleanup(ambiente.stop)

    def test_tesseract_que_acompanha_o_sistema_tem_prioridade(self):
        portatil = os.path.join(self.pasta, "Tesseract-OCR")
        os.makedirs(os.path.join(portatil, "tessdata"))
        open(os.path.join(portatil, "tesseract.exe"), "w").close()
        os.environ["TESSDATA_PREFIX"] = r"C:\outro\tessdata"  # de outra instalação do computador
        with mock.patch.object(armazenamento, "pasta_padrao_app", return_value=self.pasta), \
                mock.patch.object(leitor_folhas.shutil, "which", return_value=r"C:\outro\tesseract.exe"):
            leitor_folhas._configurar_tesseract()
        self.assertEqual(pytesseract.pytesseract.tesseract_cmd, os.path.join(portatil, "tesseract.exe"))
        self.assertEqual(os.environ["TESSDATA_PREFIX"], os.path.join(portatil, "tessdata"))

    def test_sem_permissao_de_escrita_explica_o_que_fazer(self):
        for erro in (sqlite3.OperationalError("unable to open database file"), PermissionError("acesso negado")):
            texto = mensagem_falha_ao_abrir(erro, r"C:\Program Files\DIGEP Folha de Ponto")
            self.assertIn("permissão para gravar", texto)
            self.assertIn(r"C:\Program Files\DIGEP Folha de Ponto", texto)
            self.assertIn("somente para mim", texto)
        self.assertIn("Erro: falhou", mensagem_falha_ao_abrir(RuntimeError("falhou"), "X"))


if __name__ == "__main__":
    unittest.main()
