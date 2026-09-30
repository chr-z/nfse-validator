"""Cobertura de todos os codigos de issue alcancaveis.

Cada teste quebra exatamente uma coisa num documento valido e afirma que o
codigo esperado aparece. Os casos sao feitos com remocoes/substituicoes
sobre o XML sintetico, e nao com blobs escritos a mao.
"""

import unittest
from datetime import datetime, timedelta, timezone

from nfse_validator import validate
from nfse_validator import fixtures as fx


def v(**kw):
    return fx.documento_base(**kw)


def codigos(xml):
    return validate(xml).codes()


class TestXML(unittest.TestCase):
    def test_xml_vazio(self):
        self.assertIn("XML_VAZIO", codigos(""))

    def test_xml_so_com_espaco(self):
        self.assertIn("XML_VAZIO", codigos("   \n  "))

    def test_xml_malformado(self):
        self.assertIn("XML_MALFORMADO", codigos(fx.documento_quebrado("xml_malformado")))

    def test_roots_multiplas(self):
        self.assertIn("XML_RAIZES_MULTIPLAS", codigos(fx.documento_quebrado("raiz_duplicada")))

    def test_encoding_invalido(self):
        xml = '<?xml version="1.0" encoding="XINVALID-9"?><NFSe></NFSe>'.encode("utf-8")
        r = validate(xml)
        self.assertFalse(r.ok)
        self.assertTrue(
            r.has_code("XML_ENCODING_INVALIDO") or r.has_code("XML_MALFORMADO"),
            f"esperava erro de encoding, veio {r.codes()}",
        )

    def test_sem_raiz(self):
        # Somente processing instructions: nenhum elemento raiz.
        rel = validate("<?xml version='1.0'?>")
        self.assertFalse(rel.ok)
        self.assertIn("XML_SEM_RAIZ", rel.codes())

    def test_raiz_invalida(self):
        xml = v().replace("<NFSe ", "<Outro ").replace("</NFSe>", "</Outro>")
        self.assertIn("ENVELOPE_RAIZ_INVALIDA", codigos(xml))

    def test_namespace_desconhecido(self):
        xml = v().replace("http://www.abrasf.org.br/nfse.xsd", "http://exemplo.invalido/ns")
        rel = validate(xml)
        self.assertIn("RAIZ_NAMESPACE_DESCONHECIDO", rel.codes())
        # Namespace desconhecido e aviso, nao erro fatal.
        self.assertEqual(rel.warnings[0].code, "RAIZ_NAMESPACE_DESCONHECIDO")


class TestEnvelope(unittest.TestCase):
    def test_nfse_ausente(self):
        xml = v().replace("<NFSe xmlns=\"http://www.abrasf.org.br/nfse.xsd\">", "<NFSe>")
        # Sem <NFSe> filho e sem namespace: a raiz vira o proprio envelope.
        xml = "<?xml version=\"1.0\"?><Raiz></Raiz>"
        self.assertIn("ENV_NFSE_AUSENTE", codigos(xml))

    def test_nfse_vazia(self):
        xml = '<?xml version="1.0"?><NFSe xmlns="http://www.abrasf.org.br/nfse.xsd"></NFSe>'
        self.assertIn("ENV_NFSE_VAZIA", codigos(xml))

    def test_infnfe_ausente(self):
        xml = '<?xml version="1.0"?><NFSe xmlns="http://www.abrasf.org.br/nfse.xsd"><InfNFeSig></InfNFeSig></NFSe>'
        cds = codigos(xml)
        self.assertIn("ENV_INFNFE_AUSENTE", cds)

    def test_infnfe_vazia(self):
        xml = fx.documento_valido()
        ini = xml.index("<InfNFe>")
        fim = xml.index("</InfNFe>") + len("</InfNFe>")
        self.assertIn("ENV_INFNFE_VAZIA", codigos(xml[:ini] + "<InfNFe></InfNFe>" + xml[fim:]))

    def test_infnfe_duplicado(self):
        xml = fx.documento_valido()
        ini = xml.index("<InfNFe>")
        bloco = xml[ini: xml.index("</InfNFe>") + len("</InfNFe>")]
        self.assertIn("ENV_INFNFE_DUPLICADO", codigos(xml.replace("</InfNFeSig>", "</InfNFeSig>" + bloco)))


class TestAssinatura(unittest.TestCase):
    def test_infnsig_ausente(self):
        self.assertIn("INFNFESIG_AUSENTE", codigos(fx.documento_quebrado("infnsig_ausente")))

    def test_infnsig_vazia(self):
        # <InfNFeSig> presente porem sem <InfNFe> dentro dele.
        xml = fx.documento_quebrado("infnsig_ausente").replace(
            "<InfNFe>", "<InfNFeSig></InfNFeSig><InfNFe>"
        )
        self.assertIn("INFNFESIG_VAZIA", codigos(xml))

    def test_assinatura_ausente(self):
        # <InfNFeSig> existe mas nao tem <Signature>.
        xml = fx.documento_quebrado("infnsig_ausente").replace(
            "<InfNFe>", "<InfNFeSig></InfNFeSig><InfNFe>"
        )
        cds = codigos(xml)
        self.assertTrue(
            "ASSINATURA_AUSENTE" in cds or "INFNFESIG_VAZIA" in cds, f"veio {cds}"
        )

    def test_assinatura_vazia(self):
        self.assertIn("ASSINATURA_VAZIA", codigos(v(assinatura_vazia=True)))

    def test_reference_ausente(self):
        self.assertIn("ASSINATURA_REFERENCE_AUSENTE", codigos(v(assinatura_sem_reference=True)))

    def test_reference_vazia(self):
        xml = v(assinatura_sem_reference=True).replace(
            "<SignedInfo></SignedInfo>", "<SignedInfo><Reference></Reference></SignedInfo>"
        )
        self.assertIn("ASSINATURA_REFERENCE_VAZIA", codigos(xml))

    def test_uri_invalida(self):
        self.assertIn("ASSINATURA_URI_INVALIDA", codigos(fx.documento_quebrado("assinatura_uri")))

    def test_signaturevalue_ausente(self):
        self.assertIn("ASSINATURA_SIGNATUREVALUE_AUSENTE", codigos(v(assinatura_sem_valor=True)))

    def test_signaturevalue_vazia(self):
        self.assertIn("ASSINATURA_SIGNATUREVALUE_VAZIA", codigos(v(assinatura_valor_vazio=True)))

    def test_assinatura_fora_de_infnfe(self):
        self.assertIn("ASSINATURA_FORA_DE_INFNFE", codigos(v(assinatura_fora=True)))


class TestIde(unittest.TestCase):
    def test_ide_ausente(self):
        self.assertIn("IDE_AUSENTE", codigos(fx.documento_quebrado("ide_ausente")))

    def test_ide_vazio(self):
        xml = fx.documento_valido().replace("<Ide>", "<Ide></Ide>")
        # Reconstroi para nao deixar Ideal duplicado: substitui bloco inteiro.
        xml = fx.documento_quebrado("ide_ausente")
        xml = xml.replace("<Emitente>", "<Ide></Ide><Emitente>")
        self.assertIn("IDE_VAZIO", codigos(xml))

    def test_cstat_obrigatorio(self):
        xml = v().replace("<cStat>1</cStat>", "")
        self.assertIn("IDE_CSTAT_OBRIGATORIO", codigos(xml))

    def test_cstat_invalido(self):
        self.assertIn("IDE_CSTAT_INVALIDO", codigos(fx.documento_quebrado("cstat_invalido")))

    def test_nnf_obrigatorio(self):
        xml = v().replace("<nNF>1</nNF>", "")
        self.assertIn("IDE_NNF_OBRIGATORIO", codigos(xml))

    def test_nnf_nao_numerico(self):
        xml = v().replace("<nNF>1</nNF>", "<nNF>ABC</nNF>")
        self.assertIn("IDE_NNF_NAO_NUMERICO", codigos(xml))

    def test_nnf_nao_positivo(self):
        self.assertIn("IDE_NNF_NAO_POSITIVO", codigos(fx.documento_quebrado("nnf_zero")))

    def test_dtemi_obrigatorio(self):
        xml = fx.documento_valido()
        ini = xml.index("<dhEmi>")
        xml = xml[: ini] + xml[xml.index("</dhEmi>") + len("</dhEmi>") :]
        self.assertIn("IDE_DTEMI_OBRIGATORIO", codigos(xml))

    def test_dtemi_invalido(self):
        xml = v(dt_emi="15/01/2026 10:30")
        self.assertIn("IDE_DTEMI_INVALIDO", codigos(xml))

    def test_dtemi_sem_fuso(self):
        xml = v(dt_emi="2026-01-15T10:30:00")
        self.assertIn("IDE_DTEMI_SEM_FUSO", codigos(xml))

    def test_dtemi_futuro(self):
        rel = validate(fx.documento_quebrado("dtemi_futuro"))
        self.assertIn("IDE_DTEMI_FUTURO", rel.codes())
        self.assertEqual(
            [i for i in rel.warnings if i.code == "IDE_DTEMI_FUTURO"][0].severity, "warning"
        )

    def test_dtemi_antigo(self):
        xml = v(dt_emi="2020-01-15T10:30:00-03:00")
        rel = validate(xml)
        self.assertIn("IDE_DTEMI_ANTIGO", rel.codes())

    def test_chave_obrigatoria(self):
        xml = v().replace(
            f"<chNFe>{_chave_de(v())}</chNFe>",
            "",
        )
        self.assertIn("IDE_CHAVE_ACESSO_OBRIGATORIA", codigos(xml))

    def test_chave_invalida(self):
        self.assertIn("IDE_CHAVE_ACESSO_INVALIDA", codigos(fx.documento_quebrado("chave_invalida")))

    def test_chave_curta(self):
        xml = v().replace(f"<chNFe>{_chave_de(v())}</chNFe>", "<chNFe>123</chNFe>")
        self.assertIn("IDE_CHAVE_ACESSO_INVALIDA", codigos(xml))

    def test_chave_ano_divergente(self):
        # Chave com DV valido mas AAMM de outro ano que o dhEmi: aviso, nao erro.
        from nfse_validator.brazil import gerar_chave_acesso

        hoje = datetime.now(timezone(timedelta(hours=-3)))
        outro_ano = hoje.year - 3
        chave = gerar_chave_acesso(uf="SP", cnpj=fx.CNPJ_SINTETICO, ano=outro_ano, mes=1)
        xml = v(chave=chave)
        rel = validate(xml)
        avisos = [i for i in rel.warnings if i.code == "IDE_CHAVE_ACESSO_ANO_DIVERGENTE"]
        self.assertTrue(avisos, f"veio {rel.codes()}")
        # Divergencia de ano nao pode virar erro por si so.
        self.assertNotIn("IDE_CHAVE_ACESSO_INVALIDA", [i.code for i in rel.errors])

    def test_cmunfg_obrigatorio(self):
        xml = v().replace("<cMunFG>3550308</cMunFG>", "")
        self.assertIn("IDE_CMUNFG_OBRIGATORIO", codigos(xml))

    def test_cmunfg_invalido(self):
        xml = v(c_mun_fg="9999999")
        self.assertIn("IDE_CMUNFG_INVALIDO", codigos(xml))

    def test_cmun_invalido(self):
        xml = v().replace("<cMun>3550308</cMun>", "<cMun>9999999</cMun>")
        self.assertIn("IDE_CMUN_INVALIDO", codigos(xml))

    def test_cmun_divergem(self):
        xml = v().replace("<cMun>3550308</cMun>", "<cMun>3304557</cMun>")
        rel = validate(xml)
        self.assertIn("IDE_CMUN_CMUNFG_DIVERGEM", rel.codes())
        self.assertEqual(
            [i for i in rel.warnings if i.code == "IDE_CMUN_CMUNFG_DIVERGEM"][0].severity, "warning"
        )

    def test_tpamb_invalido(self):
        xml = v().replace("<tpAmb>2</tpAmb>", "<tpAmb>9</tpAmb>")
        rel = validate(xml)
        self.assertIn("IDE_TPAMB_INVALIDO", rel.codes())
        self.assertEqual(
            [i for i in rel.warnings if i.code == "IDE_TPAMB_INVALIDO"][0].severity, "warning"
        )

    def test_ordem_incorreta(self):
        self.assertIn("IDE_ORDEM_INVALIDA", codigos(fx.documento_quebrado("ordem_incorreta")))


def _chave_de(xml):
    import re

    m = re.search(r"<chNFe>(.*?)</chNFe>", xml)
    return m.group(1)


class TestEmitente(unittest.TestCase):
    def test_emitente_ausente(self):
        xml = fx.documento_quebrado("ide_ausente")
        ini = xml.index("<Emitente>")
        xml = xml[:ini] + xml[xml.index("</Emitente>") + len("</Emitente>") :]
        self.assertIn("EMITENTE_AUSENTE", codigos(xml))

    def test_emitente_vazio(self):
        xml = fx.documento_quebrado("ide_ausente")
        ini = xml.index("<Emitente>")
        xml = xml[:ini] + "<Emitente></Emitente>" + xml[xml.index("</Emitente>") + len("</Emitente>") :]
        self.assertIn("EMITENTE_VAZIO", codigos(xml))

    def test_cnpj_e_cpf(self):
        self.assertIn("EMITENTE_CNPJ_E_CPF", codigos(fx.documento_quebrado("cnpj_com_cpf")))

    def test_cnpj_dv_invalido(self):
        self.assertIn("EMITENTE_CNPJ_INVALIDO", codigos(fx.documento_quebrado("cnpj_dv_invalido")))

    def test_cnpj_vazio(self):
        xml = v().replace(f"<CNPJ>{fx.CNPJ_SINTETICO}</CNPJ>", "<CNPJ></CNPJ>")
        self.assertIn("EMITENTE_CNPJ_OBRIGATORIO", codigos(xml))

    def test_cpf_invalido(self):
        xml = v().replace(f"<CNPJ>{fx.CNPJ_SINTETICO}</CNPJ>", "<CPF>123</CPF>")
        self.assertIn("EMITENTE_CPF_INVALIDO", codigos(xml))

    def test_cpf_dv_invalido(self):
        xml = v().replace(f"<CNPJ>{fx.CNPJ_SINTETICO}</CNPJ>", "<CPF>12345678900</CPF>")
        self.assertIn("EMITENTE_CPF_INVALIDO", codigos(xml))

    def test_cpf_vazio(self):
        xml = v().replace(f"<CNPJ>{fx.CNPJ_SINTETICO}</CNPJ>", "<CPF></CPF>")
        self.assertIn("EMITENTE_CPF_OBRIGATORIO", codigos(xml))

    def test_razao_social_obrigatoria(self):
        # Sem xNome E sem xFant.
        xml = v().replace("<xNome>EMPRESA SINTETICA DE TESTE LTDA</xNome>", "")
        xml = xml.replace("<xFant>EMPRESA SINTETICA</xFant>", "")
        self.assertIn("EMITENTE_RAZAO_SOCIAL_OBRIGATORIA", codigos(xml))

    def test_nome_obrigatorio(self):
        # Sem xNome mas com xFant => nome fantasia nao substitui razao social.
        xml = v().replace("<xNome>EMPRESA SINTETICA DE TESTE LTDA</xNome>", "")
        self.assertIn("EMITENTE_NOME_OBRIGATORIO", codigos(xml))

    def test_uf_invalida(self):
        self.assertIn("EMITENTE_UF_INVALIDA", codigos(fx.documento_quebrado("uf_invalida")))

    def test_ordem_incorreta(self):
        xml = v().replace(
            "<xNome>EMPRESA SINTETICA DE TESTE LTDA</xNome><xFant>EMPRESA SINTETICA</xFant>",
            "<xFant>EMPRESA SINTETICA</xFant><xNome>EMPRESA SINTETICA DE TESTE LTDA</xNome>",
        )
        self.assertIn("EMITENTE_ORDEM_INVALIDA", codigos(xml))

    def test_cep_invalido(self):
        xml = v().replace("<CEP>01001000</CEP>", "<CEP>123</CEP>")
        self.assertIn("ENDERECO_CEP_INVALIDO", codigos(xml))

    def test_tel_invalido(self):
        xml = v().replace("<fone>1133334444</fone>", "<fone>123</fone>")
        self.assertIn("ENDERECO_TEL_INVALIDO", codigos(xml))


class TestDestinatario(unittest.TestCase):
    def test_destinatario_ausente_e_aviso(self):
        rel = validate(fx.documento_base(sem_destinatario=True))
        self.assertIn("DESTINATARIO_AUSENTE", rel.codes())
        self.assertEqual(
            [i for i in rel.warnings if i.code == "DESTINATARIO_AUSENTE"][0].severity, "warning"
        )

    def test_destinatario_vazio(self):
        xml = fx.documento_valido()
        ini = xml.index("<Destinatario>")
        fim = xml.index("</Destinatario>") + len("</Destinatario>")
        rel = validate(xml[:ini] + "<Destinatario></Destinatario>" + xml[fim:])
        self.assertIn("DESTINATARIO_VAZIO", rel.codes())
        self.assertEqual(
            [i for i in rel.warnings if i.code == "DESTINATARIO_VAZIO"][0].severity, "warning"
        )

    def test_cpf_invalido(self):
        self.assertIn("DESTINATARIO_CPF_INVALIDO", codigos(fx.documento_quebrado("cpf_dv_invalido")))

    def test_cnpj_invalido(self):
        xml = v().replace(
            f"<CPF>{fx.CPF_SINTETICO}</CPF>", "<CNPJ>11222333000199</CNPJ>"
        )
        self.assertIn("DESTINATARIO_CNPJ_INVALIDO", codigos(xml))

    def test_cpf_e_cnpj(self):
        xml = v().replace(
            f"<CPF>{fx.CPF_SINTETICO}</CPF>",
            f"<CPF>{fx.CPF_SINTETICO}</CPF><CNPJ>{fx.CNPJ_SINTETICO}</CNPJ>",
        )
        self.assertIn("DESTINATARIO_CPF_E_CNPJ", codigos(xml))

    def test_sem_documento(self):
        xml = v().replace(f"<CPF>{fx.CPF_SINTETICO}</CPF>", "")
        self.assertIn("DESTINATARIO_SEM_DOCUMENTO", codigos(xml))

    def test_ordem_incorreta(self):
        xml = v().replace(
            f"<CPF>{fx.CPF_SINTETICO}</CPF><xNome>CLIENTE SINTETICO</xNome>",
            f"<xNome>CLIENTE SINTETICO</xNome><CPF>{fx.CPF_SINTETICO}</CPF>",
        )
        self.assertIn("DESTINATARIO_ORDEM_INVALIDA", codigos(xml))


class TestServico(unittest.TestCase):
    def test_servico_ausente(self):
        # </ListaServico> contem "</Servico>" como sufixo: buscar a partir do
        # fim da lista evita cortar no lugar errado.
        xml = fx.documento_valido()
        ini = xml.index("<Servico>")
        fim = xml.index("</ListaServico>") + len("</ListaServico></Servico>")
        self.assertIn("SERVICO_AUSENTE", codigos(xml[:ini] + xml[fim:]))

    def test_servico_vazio(self):
        xml = fx.documento_valido()
        ini = xml.index("<Servico>")
        fim = xml.index("</ListaServico>") + len("</ListaServico></Servico>")
        self.assertIn("SERVICO_VAZIO", codigos(xml[:ini] + "<Servico></Servico>" + xml[fim:]))

    def test_lista_ausente(self):
        xml = fx.documento_quebrado("ide_ausente")
        xml = xml.replace("<ListaServico><Servico><codTributacao>01.07</codTributacao>"
                          "<xServ>Servico de teste sintetico</xServ><vServ>1000.00</vServ>"
                          "<vBC>1000.00</vBC><aliq>5.00</aliq><vISS>50.00</vISS>"
                          "<vTotTrib>120.00</vTotTrib><indISS>1</indISS></Servico></ListaServico>", "")
        self.assertIn("LISTA_SERVICO_AUSENTE", codigos(xml))

    def test_lista_vazia(self):
        self.assertIn("LISTA_SERVICO_VAZIA", codigos(fx.documento_quebrado("lista_vazia_com_total")))

    def test_item_sem_codigo(self):
        xml = v().replace("<codTributacao>01.07</codTributacao>", "")
        self.assertIn("ITEM_SERVICO_SEM_CODIGO", codigos(xml))

    def test_item_codigo_invalido(self):
        xml = v().replace("<codTributacao>01.07</codTributacao>", "<codTributacao>ABC</codTributacao>")
        self.assertIn("ITEM_SERVICO_CODIGO_INVALIDO", codigos(xml))

    def test_item_sem_valor(self):
        xml = v().replace("<vServ>1000.00</vServ>", "<vServ></vServ>")
        self.assertIn("ITEM_SERVICO_SEM_VALOR", codigos(xml))

    def test_valor_nao_numerico(self):
        xml = v().replace("<vServ>1000.00</vServ>", "<vServ>abc</vServ>")
        self.assertIn("VALOR_NAO_NUMERICO", codigos(xml))

    def test_valor_negativo(self):
        xml = v().replace("<vServ>1000.00</vServ>", "<vServ>-50.00</vServ>")
        self.assertIn("VALOR_NEGATIVO", codigos(xml))

    def test_item_sem_bc(self):
        xml = v().replace("<vBC>1000.00</vBC>", "")
        self.assertIn("ITEM_SERVICO_SEM_BC", codigos(xml))

    def test_aliq_invalida(self):
        xml = v().replace("<aliq>5.00</aliq>", "<aliq>150.00</aliq>")
        self.assertIn("ITEM_SERVICO_ALIQUOTA_INVALIDA", codigos(xml))

    def test_aliq_nao_numerica(self):
        xml = v().replace("<aliq>5.00</aliq>", "<aliq>abc</aliq>")
        self.assertIn("ITEM_SERVICO_ALIQUOTA_INVALIDA", codigos(xml))

    def test_aliq_divergente(self):
        rel = validate(fx.documento_quebrado("aliquota_divergente"))
        self.assertIn("ITEM_SERVICO_ALIQUOTA_DIVERGENTE", rel.codes())

    def test_retiss_invalido(self):
        xml = v(itens=[fx._item_servico(extra={"retISS": "9"})])
        self.assertIn("ITEM_SERVICO_ISS_RETIDO_INVALIDO", codigos(xml))

    def test_item_ordem_incorreta(self):
        xml = v().replace(
            "<vServ>1000.00</vServ><vBC>1000.00</vBC><aliq>5.00</aliq><vISS>50.00</vISS>",
            "<vBC>1000.00</vBC><vServ>1000.00</vServ><aliq>5.00</aliq><vISS>50.00</vISS>",
        )
        self.assertIn("ITEM_SERVICO_ORDEM_INVALIDA", codigos(xml))

    def test_codmun_divergente(self):
        # O <cMun> do item precisa vir depois de <xServ> na ordem do schema.
        xml = v(itens=[fx._item_servico(extra={"cMun": "3304557"})])
        rel = validate(xml)
        self.assertIn("LISTA_SERVICO_CODIGO_MUN_DIVERGENTE", rel.codes())


class TestTotais(unittest.TestCase):
    def test_total_ausente(self):
        xml = fx.documento_quebrado("ide_ausente")
        ini = xml.index("<Total>")
        xml = xml[:ini] + xml[xml.index("</Total>") + len("</Total>") :]
        self.assertIn("TOTAL_AUSENTE", codigos(xml))

    def test_total_vazio(self):
        xml = fx.documento_quebrado("ide_ausente")
        ini = xml.index("<Total>")
        xml = xml[:ini] + "<Total></Total>" + xml[xml.index("</Total>") + len("</Total>") :]
        self.assertIn("TOTAL_VAZIO", codigos(xml))

    def test_iss_ausente(self):
        xml = v().replace("<ISS><vBC>1000.00</vBC><vServicos>1000.00</vServicos><vISS>50.00</vISS></ISS>", "")
        self.assertIn("TOTAL_ISS_TRIBUTARIO_AUSENTE", codigos(xml))

    def test_iss_recolhido_ausente(self):
        xml = v().replace(
            "<ISSRetido><vServico>1000.00</vServico><vDescIncond>50.00</vDescIncond>"
            "<vISSRetido>0.00</vISSRetido><vTotTrib>120.00</vTotTrib><vLiq>950.00</vLiq></ISSRetido>",
            "",
        )
        self.assertIn("TOTAL_ISS_RECOLHIDO_AUSENTE", codigos(xml))

    def test_decimal_invalido(self):
        xml = v().replace("<vServicos>1000.00</vServicos>", "<vServicos>abc</vServicos>")
        self.assertIn("TOTAL_DECIMAL_INVALIDO", codigos(xml))

    def test_total_sem_itens(self):
        self.assertIn("TOTAL_SEM_ITENS", codigos(fx.documento_quebrado("lista_vazia_com_total")))

    def test_total_sem_itens_nao_zero(self):
        self.assertIn(
            "TOTAL_SEM_ITENS_NAO_ZERO", codigos(fx.documento_quebrado("lista_vazia_com_total"))
        )


class TestAritmetica(unittest.TestCase):
    def test_vservico_divergente(self):
        self.assertIn("SOMA_VSERVICO_DIVERGENTE", codigos(fx.documento_quebrado("vservico_divergente")))

    def test_viss_divergente(self):
        self.assertIn("SOMA_VISS_DIVERGENTE", codigos(fx.documento_quebrado("viss_divergente")))

    def test_vbc_divergente(self):
        xml = v(v_bc_total="1500.00")
        self.assertIn("SOMA_VBC_DIVERGENTE", codigos(xml))

    def test_vtottrib_divergente(self):
        xml = v(v_tot_trib_total="300.00")
        self.assertIn("SOMA_VTOTTRIB_DIVERGENTE", codigos(xml))

    def test_liquido_nao_confer(self):
        xml = v(v_liq="999.00")
        self.assertIn("LIQUIDO_NAO_CONFERE", codigos(xml))

    def test_liquido_com_deducao(self):
        # vServico 1000 - desc 50 - deducao 100 = 850. Declarado 850 => ok.
        xml = v(v_liq="850.00").replace(
            "<vDescIncond>50.00</vDescIncond>", "<vDescIncond>50.00</vDescIncond><vDeducao>100.00</vDeducao>"
        )
        self.assertNotIn("LIQUIDO_NAO_CONFERE", codigos(xml))

    def test_iss_recolhido_divergente(self):
        xml = v(v_iss_retido="10.00", v_iss_total="50.00")
        self.assertIn("TOTAL_ISS_RECOLHIDO_DIVERGENTE", codigos(xml))

    def test_tolerancia_um_centavo_passa(self):
        self.assertNotIn("SOMA_VSERVICO_DIVERGENTE", codigos(fx.documento_quebrado("diferenca_um_centavo")))

    def test_tolerancia_dois_centavos_falha(self):
        self.assertIn("SOMA_VSERVICO_DIVERGENTE", codigos(fx.documento_quebrado("diferenca_dois_centavos")))


if __name__ == "__main__":
    unittest.main()
