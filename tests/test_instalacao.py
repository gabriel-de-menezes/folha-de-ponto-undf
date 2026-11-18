"""Comportamentos de instalação: Tesseract que acompanha o sistema e falha ao abrir sem permissão de escrita."""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

import pytesseract

from folha_ponto.infraestrutura import armazenamento, conversor_pdf, leitor_folhas
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

    def test_libreoffice_que_acompanha_o_sistema_tem_prioridade(self):
        embutido = os.path.join(self.pasta, "LibreOffice", "program", "soffice.exe")
        os.makedirs(os.path.dirname(embutido))
        open(embutido, "w").close()
        with mock.patch.object(armazenamento, "pasta_padrao_app", return_value=self.pasta), \
                mock.patch.object(conversor_pdf.shutil, "which", return_value="/usr/bin/soffice"):
            self.assertEqual(conversor_pdf.achar_libreoffice(), embutido)

    def test_conversao_em_lote_pelo_libreoffice(self):
        """Sem Word: converte em grupos, renomeia para o PDF pedido e não aceita um PDF antigo como convertido."""
        pares = []
        for i in range(conversor_pdf.LOTE_LIBREOFFICE + 3):
            docx = os.path.join(self.pasta, f"folha{i}.docx")
            open(docx, "w").close()
            pares.append((docx, os.path.join(self.pasta, f"folha{i}.pdf")))
        pares.append((pares[0][0], os.path.join(self.pasta, "sub", "outro_nome.pdf")))
        os.makedirs(os.path.join(self.pasta, "sub"))
        open(pares[1][1], "w").close()  # PDF antigo, de uma geração anterior
        chamadas = []

        def soffice_falso(comando, **_):
            chamadas.append(comando)
            pasta = comando[comando.index("--outdir") + 1]
            for docx in comando[comando.index("--outdir") + 2:]:
                if not docx.endswith("folha1.docx"):  # esta falha na conversão
                    open(os.path.join(pasta, os.path.basename(docx)[:-5] + ".pdf"), "w").close()

        progresso = []
        with mock.patch.object(conversor_pdf, "achar_libreoffice", return_value="soffice"), \
                mock.patch.object(conversor_pdf.subprocess, "run", side_effect=soffice_falso):
            with conversor_pdf.ConversorPDF(usar_word=False) as conversor:
                ok = conversor.converter_lote(pares, lambda feitos, total: progresso.append((feitos, total)))
        self.assertEqual(ok, [i != 1 for i in range(len(pares))])
        self.assertTrue(os.path.exists(os.path.join(self.pasta, "sub", "outro_nome.pdf")))
        self.assertEqual(len(chamadas), 3)  # dois grupos na pasta principal + um na subpasta
        self.assertTrue(all(c[1].startswith("-env:UserInstallation=file:") for c in chamadas))
        self.assertEqual(progresso[-1], (len(pares), len(pares)))

    def test_sem_permissao_de_escrita_explica_o_que_fazer(self):
        for erro in (sqlite3.OperationalError("unable to open database file"), PermissionError("acesso negado")):
            texto = mensagem_falha_ao_abrir(erro, r"C:\Program Files\DIGEP Folha de Ponto")
            self.assertIn("permissão para gravar", texto)
            self.assertIn(r"C:\Program Files\DIGEP Folha de Ponto", texto)
            self.assertIn("somente para mim", texto)
        self.assertIn("Erro: falhou", mensagem_falha_ao_abrir(RuntimeError("falhou"), "X"))


if __name__ == "__main__":
    unittest.main()
