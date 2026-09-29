"""Testes das regras de validacao sobre o XML sintetico.

Cada teste parte de um documento valido e quebra exatamente uma coisa.
"""

import unittest
from datetime import datetime, timedelta, timezone

from nfse_validator import validate
from nfse_validator import fixtures as fx


def _codigos(xml, **kw):
    return validate(xml, **kw).codes()


class TestDocumentoValido(unittest.TestCase):
    def test_documento_valido_passa_sem_issues(self):
        relatorio = validate(fx.documento_valido())
        self.assertTrue(
            relatorio.ok,
            f"esperado sem erros, veio: {[i.code for i in relatorio.errors]}",
        )
        self.assertEqual(relatorio.errors, [])
        self.assertEqual(relatorio.warnings, [])

    def test_relatorio_ok_e_true(self):
        self.assertTrue(validate(fx.documento_valido()).ok)

    def test_infnfe_apenas_uma_vez(self):
        # Um <InfNFe> duplicado (dentro e fora de InfNFeSig) e estrutura invalida.
        xml = fx.documento_valido()
        self.assertEqual(xml.count("<InfNFe>"), 1)
        self.assertEqual(xml.count("<InfNFeSig>"), 1)


class TestEstrutura(unittest.TestCase):
    def test_ide_ausente(self):
        self.assertIn("IDE_AUSENTE", _codigos(fx.documento_quebrado("ide_ausente")))

    def test_infnsig_ausente(self):
        self.assertIn("INFNFESIG_AUSENTE", _codigos(fx.documento_quebrado("infnsig_ausente")))

    def test_ordem_de_elementos_incorreta(self):
        self.assertIn("IDE_ORDEM_INVALIDA", _codigos(fx.documento_quebrado("ordem_incorreta")))

    def test_xml_malformado(self):
        relatorio = validate(fx.documento_quebrado("xml_malformado"))
        self.assertIn("XML_MALFORMADO", relatorio.codes())
        # Deve trazer posicao util para quem vai corrigir.
        erro = relatorio.errors[0]
        self.assertIsNotNone(erro.line)
        self.assertGreater(erro.line, 0)

    def test_raiz_duplicada(self):
        self.assertIn("XML_RAIZES_MULTIPLAS", _codigos(fx.documento_quebrado("raiz_duplicada")))

    def test_infnfe_duplicado(self):
        # Extrai o <InfNFe> assinado e o colo como irmao de <InfNFeSig>,
        # produzindo um documento com duas copias da nota.
        xml = fx.documento_valido()
        inicio = xml.index("<InfNFe>")
        infnfe = xml[inicio:]
        infnfe = infnfe[: infnfe.index("</InfNFe>") + len("</InfNFe>")]
        duplicado = xml.replace("</InfNFeSig>", "</InfNFeSig>" + infnfe)
        self.assertIn("ENV_INFNFE_DUPLICADO", _codigos(duplicado))

    def test_documento_vazio(self):
        relatorio = validate(b"")
        self.assertIn("XML_VAZIO", relatorio.codes())
        self.assertFalse(relatorio.ok)

    def test_estrutura_completa_tem_issue_com_hint(self):
        relatorio = validate(fx.documento_quebrado("ide_ausente"))
        erro = relatorio.errors[0]
        self.assertTrue(erro.hint, "todo erro deve trazer uma dica de correcao")
        self.assertIn("Ide", erro.path)

    def test_cstat_invalido(self):
        self.assertIn("IDE_CSTAT_INVALIDO", _codigos(fx.documento_quebrado("cstat_invalido")))

    def test_nnf_zero(self):
        self.assertIn("IDE_NNF_NAO_POSITIVO", _codigos(fx.documento_quebrado("nnf_zero")))


class TestDocumentosBrasileiros(unittest.TestCase):
    def test_cnpj_dv_invalido(self):
        self.assertIn("EMITENTE_CNPJ_INVALIDO", _codigos(fx.documento_quebrado("cnpj_dv_invalido")))

    def test_cpf_dv_invalido(self):
        self.assertIn("DESTINATARIO_CPF_INVALIDO", _codigos(fx.documento_quebrado("cpf_dv_invalido")))

    def test_cnpj_com_cpf(self):
        self.assertIn("EMITENTE_CNPJ_E_CPF", _codigos(fx.documento_quebrado("cnpj_com_cpf")))

    def test_uf_invalida(self):
        self.assertIn("EMITENTE_UF_INVALIDA", _codigos(fx.documento_quebrado("uf_invalida")))

    def test_chave_de_acesso_invalida(self):
        self.assertIn(
            "IDE_CHAVE_ACESSO_INVALIDA", _codigos(fx.documento_quebrado("chave_invalida"))
        )

    def test_dtemi_futuro_gera_aviso_nao_erro(self):
        relatorio = validate(fx.documento_quebrado("dtemi_futuro"))
        avisos = [i for i in relatorio.warnings if i.code == "IDE_DTEMI_FUTURO"]
        self.assertTrue(avisos, "data no futuro deveria gerar aviso")
        # Nao pode virar erro por si so.
        self.assertNotIn("IDE_DTEMI_FUTURO", [i.code for i in relatorio.errors])


class TestAritmetica(unittest.TestCase):
    def test_vservico_divergente_da_soma(self):
        self.assertIn(
            "SOMA_VSERVICO_DIVERGENTE", _codigos(fx.documento_quebrado("vservico_divergente"))
        )

    def test_viss_divergente_da_soma(self):
        self.assertIn("SOMA_VISS_DIVERGENTE", _codigos(fx.documento_quebrado("viss_divergente")))

    def test_lista_vazia_com_totais_nao_zerados(self):
        codigos = _codigos(fx.documento_quebrado("lista_vazia_com_total"))
        self.assertIn("LISTA_SERVICO_VAZIA", codigos)
        self.assertIn("TOTAL_SEM_ITENS", codigos)
        self.assertIn("TOTAL_SEM_ITENS_NAO_ZERO", codigos)

    def test_diferenca_de_um_centavo_passa(self):
        # Exatamente 0,01 de diferenca e arredondamento, nao erro.
        relatorio = validate(fx.documento_quebrado("diferenca_um_centavo"))
        self.assertNotIn("SOMA_VSERVICO_DIVERGENTE", relatorio.codes())

    def test_diferenca_de_dois_centavos_falha(self):
        relatorio = validate(fx.documento_quebrado("diferenca_dois_centavos"))
        self.assertIn("SOMA_VSERVICO_DIVERGENTE", relatorio.codes())

    def test_aliquota_implicita_divergente_gera_aviso(self):
        relatorio = validate(fx.documento_quebrado("aliquota_divergente"))
        avisos = [i for i in relatorio.warnings if i.code == "ITEM_SERVICO_ALIQUOTA_DIVERGENTE"]
        self.assertTrue(avisos, "aliquota implicita muito diferente da declarada deve avisar")


class TestAssinatura(unittest.TestCase):
    def test_uri_de_reference_invalida(self):
        self.assertIn(
            "ASSINATURA_URI_INVALIDA", _codigos(fx.documento_quebrado("assinatura_uri"))
        )

    def test_assinatura_sem_signaturevalue(self):
        codigos = _codigos(fx.documento_quebrado("assinatura_incompleta"))
        self.assertIn("ASSINATURA_SIGNATUREVALUE_AUSENTE", codigos)


class TestStrict(unittest.TestCase):
    def test_strict_promove_aviso_a_erro(self):
        xml = fx.documento_quebrado("aliquota_divergente")  # so produz aviso
        normal = validate(xml, strict=False)
        estrito = validate(xml, strict=True)
        self.assertTrue(normal.ok, "sem strict, so avisos => ok")
        self.assertEqual(normal.warnings[0].code, "ITEM_SERVICO_ALIQUOTA_DIVERGENTE")
        self.assertFalse(estrito.ok, "com strict, aviso vira erro")
        self.assertEqual(estrito.errors[0].code, "ITEM_SERVICO_ALIQUOTA_DIVERGENTE")
        self.assertEqual(estrito.warnings, [])

    def test_strict_nao_muda_documento_valido(self):
        self.assertTrue(validate(fx.documento_valido(), strict=True).ok)


if __name__ == "__main__":
    unittest.main()
