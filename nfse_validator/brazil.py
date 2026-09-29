"""Validacoes de documentos e formatos brasileiros.

Tudo aqui e stdlib puro. Nenhuma chamada de rede, nenhum dado real de
empresa ou pessoa: os testes usam numeros sinteticos gerados por
:func:`gerar_cpf` / :func:`gerar_cnpj`.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

# --- UFs -----------------------------------------------------------------
# Fonte: codigo IBGE da UF. Nenhum outro valor e aceito.
UFS: Tuple[str, ...] = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
)
# Codigo numerico da UF usado na chave de acesso (posicao 21-22 do DV).
UF_CODIGO: dict[str, int] = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 18, "PI": 19, "CE": 21, "RN": 22, "PB": 23, "PE": 25, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}
CODIGO_PARA_UF: dict[int, str] = {v: k for k, v in UF_CODIGO.items()}

RE_CPF = re.compile(r"^\d{11}$")
RE_CNPJ = re.compile(r"^\d{14}$")
RE_CEP = re.compile(r"^\d{8}$")
RE_FONE = re.compile(r"^\d{10,11}$")
RE_IBGE = re.compile(r"^\d{7}$")
RE_CHAVE = re.compile(r"^[0-9]{44}$")
RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


class ErroFormato(ValueError):
    """Formato invalido (distinto de digito verificador invalido)."""


# --- normalizacao --------------------------------------------------------
def somente_digitos(valor: str) -> str:
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def _todos_iguais(digitos: str) -> bool:
    return len(set(digitos)) <= 1


# --- digitos verificadores ------------------------------------------------
def _dv_cpf(base: List[int]) -> int:
    """1o digito verificador do CPF: soma ponderada 10..2, mod 11."""
    soma = sum(d * p for d, p in zip(base, range(10, 1, -1)))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def _dv_cpf2(base: List[int]) -> int:
    """2o digito verificador do CPF: soma ponderada 11..2, mod 11."""
    soma = sum(d * p for d, p in zip(base, range(11, 1, -1)))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


_PESOS_CNPJ = (
    (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
    (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
)


def _dv_cnpj(base: List[int], pesos: Tuple[int, ...]) -> int:
    soma = sum(d * p for d, p in zip(base, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def validar_cpf(cpf: str) -> bool:
    """True se ``cpf`` tem 11 digitos e digito verificador correto.

    Sequencias de digitos repetidos (000..., 111..., 999...) sao rejeitadas:
    elas passam no calculo modulo 11, mas nao sao CPFs validos.
    """
    d = somente_digitos(cpf)
    if not RE_CPF.match(d) or _todos_iguais(d):
        return False
    base = [int(c) for c in d[:9]]
    return d[9] == str(_dv_cpf(base)) and d[10] == str(_dv_cpf2(base + [_dv_cpf(base)]))


def validar_cnpj(cnpj: str) -> bool:
    """True se ``cnpj`` tem 14 digitos e os dois digitos verificadores conferem."""
    d = somente_digitos(cnpj)
    if not RE_CNPJ.match(d) or _todos_iguais(d):
        return False
    base = [int(c) for c in d[:12]]
    d1 = _dv_cnpj(base, _PESOS_CNPJ[0])
    d2 = _dv_cnpj(base + [d1], _PESOS_CNPJ[1])
    return d[12] == str(d1) and d[13] == str(d2)


def gerar_cpf(base: Optional[str] = None) -> str:
    """Gera um CPF sintetico valido (so para fixtures e testes)."""
    if base is None:
        base = "123456789"
    nums = [int(c) for c in somente_digitos(base)[:9].ljust(9, "1")]
    d1 = _dv_cpf(nums)
    d2 = _dv_cpf2(nums + [d1])
    return "".join(str(n) for n in nums + [d1, d2])


def gerar_cnpj(base: Optional[str] = None) -> str:
    """Gera um CNPJ sintetico valido (so para fixtures e testes)."""
    if base is None:
        base = "112223330001"
    nums = [int(c) for c in somente_digitos(base)[:12].ljust(12, "0")]
    d1 = _dv_cnpj(nums, _PESOS_CNPJ[0])
    d2 = _dv_cnpj(nums + [d1], _PESOS_CNPJ[1])
    return "".join(str(n) for n in nums + [d1, d2])


# --- documentos ----------------------------------------------------------
def uf_valida(uf: str) -> bool:
    return (uf or "").strip().upper() in UFS


def cep_valido(cep: str) -> bool:
    """CEP tem 8 digitos. Nao validamos faixa de regiao (CEP e sequencial).

    Diferente de CPF/CNPJ, aqui nao aceitamos formatacao: um CEP com espaco
    no meio normalmente indica montagem errada da string, e o provedor
    rejeita. Espaco nas pontas e tolerado.
    """
    texto = (cep or "").strip()
    if " " in texto:
        return False
    return bool(RE_CEP.match(texto))


def fone_valido(fone: str) -> bool:
    """Telefone: 10 digitos (fixo) ou 11 (celular, com o 9 apos o DDD)."""
    d = somente_digitos(fone)
    if not RE_FONE.match(d):
        return False
    if len(d) == 11:
        # Celular no padrao brasileiro: DDD (2) + 9 + 8 digitos. O 9 fica na
        # posicao 3, depois do DDD de 2 digitos.
        return d[2] == "9"
    return True


def email_valido(email: str) -> bool:
    e = (email or "").strip()
    if not e or len(e) > 254 or ".." in e:
        return False
    return bool(RE_EMAIL.match(e))


def ibge_municipio_valido(codigo: str) -> bool:
    """Codigo IBGE de municipio: 7 digitos. O primeiro digito identifica a UF."""
    d = somente_digitos(codigo)
    if not RE_IBGE.match(d):
        return False
    return d[0] in {"1", "2", "3", "4", "5"}


# --- chave de acesso -----------------------------------------------------
def chave_acesso_dv(chave43: str) -> int:
    """Digito verificador mod-11 da chave de acesso (43 digitos -> 1 digito)."""
    peso = 2
    total = 0
    for ch in reversed(chave43):
        total += int(ch) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = total % 11
    dv = 11 - resto
    return 0 if dv in (0, 10, 11) else dv


def validar_chave_acesso(chave: str, *, ano_esperado: Optional[int] = None) -> bool:
    """Valida a chave de 44 digitos: tamanho, DV mod-11 e posicao de ano/UF.

    A chave e ``cUF(2) AAMM(4) CNPJ/CPF(14) mod(2) serie(3) nNF(9) tpEmis(1)
    cDV(1) cIDE(1) cNF(8) cDV(2)``. Verificamos os campos estruturais
    (posicao 1-2 = UF, 3-6 = ano/mes) alem do DV.
    """
    d = somente_digitos(chave)
    if not RE_CHAVE.match(d):
        return False
    if int(d[-1]) != chave_acesso_dv(d[:-1]):
        return False
    uf = CODIGO_PARA_UF.get(int(d[0:2]))
    if uf is None:
        return False
    ano, mes = int(d[2:4]), int(d[4:6])
    if mes < 1 or mes > 12:
        return False
    if ano_esperado is not None:
        if ano != ano_esperado % 100:
            return False
    return True


def gerar_chave_acesso(
    *,
    uf: str = "SP",
    cnpj: str = "11222333000181",
    serie: int = 1,
    numero: int = 1,
    modelo: int = 55,
    tp_emis: int = 1,
    codigo_municipio: int = 3550308,
    cnf: int = 12345678,
    ano: int = 2026,
    mes: int = 1,
    cide: int = 1,
) -> str:
    """Monta uma chave sintetica com DV correto. Somente para fixtures/testes."""
    cod = UF_CODIGO[uf.upper()]
    # 43 digitos + 1 de DV = 44.
    # cUF(2) AAMM(4) CNPJ(14) modelo(2) serie(3) nNF(9) tpEmis(1) cIDE(1) cNF(7)
    corpo = (
        f"{cod:02d}{ano % 100:02d}{mes:02d}"
        f"{somente_digitos(cnpj).zfill(14)}"
        f"{modelo:02d}{serie:03d}{numero:09d}{tp_emis:01d}"
        f"{cide:01d}{cnf % 10000000:07d}"
    )[:43].ljust(43, "0")
    return corpo + str(chave_acesso_dv(corpo))


# --- dinheiro ------------------------------------------------------------
TOLERANCIA_PADRAO = Decimal("0.01")


def para_decimal(valor: Optional[str]) -> Optional[Decimal]:
    """Converte texto monetario em ``Decimal``. ``None`` quando invalido.

    Nunca use float para dinheiro: ``0.1 + 0.2`` nao e ``0.3`` em binario.
    """
    if valor is None:
        return None
    texto = str(valor).strip().replace(",", ".")
    if not texto or texto in {"-", "--"}:
        return None
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return None


def diferenca(a: Optional[Decimal], b: Optional[Decimal]) -> Optional[Decimal]:
    if a is None or b is None:
        return None
    return a - b


def dentro_da_tolerancia(
    diff: Optional[Decimal],
    tolerancia: Decimal = TOLERANCIA_PADRAO,
) -> bool:
    """True quando ``diff`` cabe na tolerancia (arredondamento de centavo)."""
    if diff is None:
        return False
    return abs(diff) <= tolerancia
