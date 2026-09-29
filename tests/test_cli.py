"""Testes da interface de linha de comando: saida, JSON e codigos de saida."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from nfse_validator import fixtures as fx
from nfse_validator.cli import EXIT_INVALIDO, EXIT_OK, EXIT_USO, main


def _rodar(argv):
    """Executa a CLI capturing stdout/stderr. Devolve (codigo, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        codigo = main(argv)
    return codigo, out.getvalue(), err.getvalue()


class TestCLIArquivo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nfse-cli-")
        self.valido = os.path.join(self.dir, "valido.xml")
        self.quebrado = os.path.join(self.dir, "quebrado.xml")
        with open(self.valido, "w", encoding="utf-8") as fh:
            fh.write(fx.documento_valido())
        with open(self.quebrado, "w", encoding="utf-8") as fh:
            fh.write(fx.documento_quebrado("vservico_divergente"))

    def test_arquivo_valido_saida_zero(self):
        codigo, out, _ = _rodar([self.valido])
        self.assertEqual(codigo, EXIT_OK)
        self.assertIn("OK", out)

    def test_arquivo_invalido_saida_um(self):
        codigo, out, _ = _rodar([self.quebrado])
        self.assertEqual(codigo, EXIT_INVALIDO)
        self.assertIn("SOMA_VSERVICO_DIVERGENTE", out)

    def test_json_saida_e_json_valido(self):
        codigo, out, _ = _rodar(["--json", self.valido])
        self.assertEqual(codigo, EXIT_OK)
        dados = json.loads(out)
        self.assertIn("ok", dados)
        self.assertIn("issues", dados)
        self.assertIn("summary", dados)
        self.assertIs(dados["ok"], True)

    def test_json_de_arquivo_quebrado_lista_o_codigo(self):
        codigo, out, _ = _rodar(["--json", self.quebrado])
        self.assertEqual(codigo, EXIT_INVALIDO)
        dados = json.loads(out)
        self.assertIs(dados["ok"], False)
        codigos = [i["code"] for i in dados["issues"]]
        self.assertIn("SOMA_VSERVICO_DIVERGENTE", codigos)

    def test_erro_de_io_dois(self):
        codigo, _, err = _rodar(["/caminho/que/nao/existe.xml"])
        self.assertEqual(codigo, EXIT_USO)
        self.assertIn("erro de IO", err)

    def test_sem_argumentos_uso(self):
        codigo, _, err = _rodar([])
        self.assertEqual(codigo, EXIT_USO)

    def test_quiet_nao_imprime_nada(self):
        codigo, out, _ = _rodar(["--quiet", self.valido])
        self.assertEqual(codigo, EXIT_OK)
        self.assertEqual(out.strip(), "")

    def test_quiet_em_arquivo_quebrado(self):
        codigo, out, _ = _rodar(["-q", self.quebrado])
        self.assertEqual(codigo, EXIT_INVALIDO)
        self.assertEqual(out.strip(), "")

    def test_strict_muda_codigo_de_saida_em_avisos(self):
        # aliquota divergente so produz aviso; sem strict sai 0, com strict sai 1.
        so_aviso = os.path.join(self.dir, "aviso.xml")
        with open(so_aviso, "w", encoding="utf-8") as fh:
            fh.write(fx.documento_quebrado("aliquota_divergente"))
        codigo, _, _ = _rodar([so_aviso])
        self.assertEqual(codigo, EXIT_OK, "sem strict, aviso nao falha")
        codigo, _, _ = _rodar(["--strict", so_aviso])
        self.assertEqual(codigo, EXIT_INVALIDO, "com strict, aviso falha")

    def test_fail_on_warning(self):
        so_aviso = os.path.join(self.dir, "aviso2.xml")
        with open(so_aviso, "w", encoding="utf-8") as fh:
            fh.write(fx.documento_quebrado("aliquota_divergente"))
        codigo, _, _ = _rodar(["--fail-on", "warning", so_aviso])
        self.assertEqual(codigo, EXIT_INVALIDO)

    def test_fail_on_none_nunca_falha(self):
        codigo, _, _ = _rodar(["--fail-on", "none", self.quebrado])
        self.assertEqual(codigo, EXIT_OK)

    def test_batch_agrega(self):
        codigo, out, _ = _rodar(["--batch", self.dir])
        # O diretório tem valido, quebrado e os de aviso: deve falhar.
        self.assertEqual(codigo, EXIT_INVALIDO)
        self.assertIn("arquivo(s)", out)
        self.assertIn("valido.xml", out)

    def test_batch_json_e_lista_de_relatorios(self):
        # Flags antes de --batch: "--batch --json" seria lido como valor.
        codigo, out, _ = _rodar(["--json", "--batch", self.dir])
        dados = json.loads(out)
        self.assertIsInstance(dados, list)
        self.assertGreaterEqual(len(dados), 2)
        for item in dados:
            self.assertIn("ok", item)

    def test_batch_diretorio_inexistente(self):
        codigo, _, err = _rodar(["--batch", "/nao/existe/xyz"])
        self.assertEqual(codigo, EXIT_USO)

    def test_path_e_batch_conflitam(self):
        codigo, _, err = _rodar(["--batch", self.dir, self.valido])
        self.assertEqual(codigo, EXIT_USO)


class TestCLIStdin(unittest.TestCase):
    def test_le_do_stdin(self):
        import sys

        dados = fx.documento_valido().encode("utf-8")

        class FakeStdin:
            buffer = io.BytesIO(dados)

        antigo = sys.stdin
        sys.stdin = FakeStdin()
        try:
            codigo, out, _ = _rodar(["-"])
        finally:
            sys.stdin = antigo
        self.assertEqual(codigo, EXIT_OK)
        self.assertIn("OK", out)


if __name__ == "__main__":
    unittest.main()
