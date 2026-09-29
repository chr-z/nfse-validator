"""Testes de ``nfse_validator.brazil``: digitos verificadores e formatos.

Escrito com ``unittest.TestCase`` para rodar sem pytest instalado, mas
coletado normalmente pelo pytest.
"""

import unittest
from decimal import Decimal

from nfse_validator import brazil as bz


class TestCPF(unittest.TestCase):
    def test_cpf_gerado_e_valido(self):
        for base in ("123456789", "987654321", "111222333", "000111222"):
            cpf = bz.gerar_cpf(base)
            self.assertTrue(bz.validar_cpf(cpf), f"{cpf} deveria ser valido")

    def test_cpf_sequencias_repetidas_sao_rejeitadas(self):
        for repetido in ("00000000000", "11111111111", "22222222222",
                         "99999999999", "12312312312"):
            self.assertFalse(bz.validar_cpf(repetido), f"{repetido} deveria ser rejeitado")

    def test_cpf_dv_incorreto(self):
        # 12345678909 e valido; trocar o ultimo digito quebra o DV.
        self.assertTrue(bz.validar_cpf("12345678909"))
        self.assertFalse(bz.validar_cpf("12345678900"))
        self.assertFalse(bz.validar_cpf("12345678910"))

    def test_cpf_tamanho_errado(self):
        self.assertFalse(bz.validar_cpf("1234567890"))
        self.assertFalse(bz.validar_cpf("123456789091"))
        self.assertFalse(bz.validar_cpf(""))

    def test_cpf_aceita_formatacao_com_mascara(self):
        # A funcao normaliza, o que e o comportamento desejado.
        self.assertTrue(bz.validar_cpf("123.456.789-09"))
        self.assertTrue(bz.validar_cpf("123 456 789 09"))


class TestCNPJ(unittest.TestCase):
    def test_cnpj_gerado_e_valido(self):
        for base in ("112223330001", "998877665501", "000000000001"):
            cnpj = bz.gerar_cnpj(base)
            self.assertTrue(bz.validar_cnpj(cnpj), f"{cnpj} deveria ser valido")

    def test_cnpj_sequencias_repetidas_sao_rejeitadas(self):
        for repetido in ("00000000000000", "11111111111111", "22222222222222"):
            self.assertFalse(bz.validar_cnpj(repetido), f"{repetido} deveria ser rejeitado")

    def test_cnpj_dv_incorreto(self):
        cnpj = bz.gerar_cnpj("112223330001")
        self.assertTrue(bz.validar_cnpj(cnpj))
        ultimo = int(cnpj[-1])
        quebra = cnpj[:-1] + str((ultimo + 1) % 10)
        self.assertFalse(bz.validar_cnpj(quebra))

    def test_cnpj_tamanho_errado(self):
        self.assertFalse(bz.validar_cnpj("1122233300018"))
        self.assertFalse(bz.validar_cnpj("112223330001811"))
        self.assertFalse(bz.validar_cnpj(""))


class TestUF(unittest.TestCase):
    def test_ufs_validas(self):
        for uf in ("SP", "RJ", "MG", "DF", "AC", "TO"):
            self.assertTrue(bz.uf_valida(uf), uf)

    def test_ufs_invalidas(self):
        for uf in ("XX", "ZZ", "S", "SPP", "1", "", "spp"):
            self.assertFalse(bz.uf_valida(uf), uf)

    def test_uf_minuscula_e_aceita(self):
        self.assertTrue(bz.uf_valida("sp"))


class TestChaveAcesso(unittest.TestCase):
    def test_chave_gerada_e_valida(self):
        chave = bz.gerar_chave_acesso()
        self.assertEqual(len(chave), 44)
        self.assertTrue(bz.validar_chave_acesso(chave), chave)

    def test_chave_dv_incorreto_e_rejeitada(self):
        chave = bz.gerar_chave_acesso()
        quebra = chave[:-1] + str((int(chave[-1]) + 1) % 10)
        self.assertFalse(bz.validar_chave_acesso(quebra))

    def test_chave_tamanho_errado(self):
        self.assertFalse(bz.validar_chave_acesso("1" * 43))
        self.assertFalse(bz.validar_chave_acesso("1" * 45))
        self.assertFalse(bz.validar_chave_acesso(""))

    def test_chave_com_uf_invalida(self):
        # "00" nao e um codigo de UF valido.
        chave = bz.gerar_chave_acesso()
        corpo = "00" + chave[2:]
        nova = corpo[:43] + str(bz.chave_acesso_dv(corpo[:43]))
        self.assertFalse(bz.validar_chave_acesso(nova))

    def test_chave_com_mes_invalido(self):
        chave = list(bz.gerar_chave_acesso())
        chave[4] = "9"
        chave[5] = "9"  # mes 99
        corpo = "".join(chave[:43])
        nova = corpo + str(bz.chave_acesso_dv(corpo))
        self.assertFalse(bz.validar_chave_acesso(nova))

    def test_chave_ano_divergente(self):
        chave = bz.gerar_chave_acesso(ano=2026, mes=1)
        self.assertTrue(bz.validar_chave_acesso(chave, ano_esperado=2026))
        self.assertFalse(bz.validar_chave_acesso(chave, ano_esperado=2025))


class TestFormatos(unittest.TestCase):
    def test_cep(self):
        self.assertTrue(bz.cep_valido("01001000"))
        self.assertFalse(bz.cep_valido("0100100"))
        # Formato nao e normalizado: espaco no meio indica montagem errada.
        self.assertFalse(bz.cep_valido("01001 000"))
        self.assertTrue(bz.cep_valido("  01001000  "))

    def test_fone(self):
        self.assertTrue(bz.fone_valido("1133334444"))
        # Celular: DDD(2) + 9 + 8 digitos.
        self.assertTrue(bz.fone_valido("11987654321"))
        self.assertFalse(bz.fone_valido("123"))
        self.assertFalse(bz.fone_valido("119876543210"))
        # 11 digitos sem o 9 na posicao do celular nao passa.
        self.assertFalse(bz.fone_valido("11887654321"))

    def test_email(self):
        self.assertTrue(bz.email_valido("contato@empresa.com.br"))
        self.assertFalse(bz.email_valido("contato@empresa"))
        self.assertFalse(bz.email_valido("contatoempresa.com"))
        self.assertFalse(bz.email_valido(""))

    def test_ibge_municipio(self):
        self.assertTrue(bz.ibge_municipio_valido("3550308"))
        self.assertTrue(bz.ibge_municipio_valido("5300108"))
        self.assertFalse(bz.ibge_municipio_valido("355030"))
        self.assertFalse(bz.ibge_municipio_valido("9990308"))


class TestDecimal(unittest.TestCase):
    def test_para_decimal_aceita_virgula(self):
        self.assertEqual(bz.para_decimal("1000.00"), Decimal("1000.00"))
        self.assertEqual(bz.para_decimal("1000,00"), Decimal("1000.00"))

    def test_para_decimal_none_para_invalido(self):
        self.assertIsNone(bz.para_decimal("abc"))
        self.assertIsNone(bz.para_decimal(""))
        self.assertIsNone(bz.para_decimal(None))

    def test_tolerancia_exata(self):
        # Exatamente 0,01 passa; 0,02 falha.
        self.assertTrue(bz.dentro_da_tolerancia(Decimal("0.01")))
        self.assertTrue(bz.dentro_da_tolerancia(Decimal("-0.01")))
        self.assertTrue(bz.dentro_da_tolerancia(Decimal("0.00")))
        self.assertFalse(bz.dentro_da_tolerancia(Decimal("0.02")))
        self.assertFalse(bz.dentro_da_tolerancia(Decimal("-0.02")))

    def test_tolerancia_customizada(self):
        self.assertTrue(bz.dentro_da_tolerancia(Decimal("0.50"), Decimal("1.00")))
        self.assertFalse(bz.dentro_da_tolerancia(Decimal("1.01"), Decimal("1.00")))


if __name__ == "__main__":
    unittest.main()
