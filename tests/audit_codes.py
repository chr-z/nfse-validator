"""Auditoria: todo codigo de issue emitido precisa de teste, e vice-versa.

Este script nao faz parte da suite (a suite testa comportamento); ele serve
para garantir que a lista de codigos e a suite nao divergem.
"""

import glob
import re
import sys

DECLARADOS = set(
    re.findall(r'^([A-Z][A-Z0-9_]+)\s*=\s*"', open('nfse_validator/codes.py').read(), re.M)
)


def alcançaveis():
    """Codigos que o validador pode de fato emitir."""
    cds = set()
    for f in glob.glob('nfse_validator/checks/*.py') + ['nfse_validator/parser.py']:
        s = open(f).read()
        cds |= set(re.findall(r'C\.([A-Z][A-Z0-9_]+)', s))
        cds |= set(re.findall(r'(?:erro|aviso)\(\s*\n?\s*["\']([A-Z][A-Z0-9_]+)', s))
        cds |= set(re.findall(r'code="([A-Z][A-Z0-9_]+)"', s))
    return cds


def testados():
    cds = set()
    for f in glob.glob('tests/*.py'):
        s = open(f).read()
        cds |= set(re.findall(r'["\']([A-Z][A-Z0-9_]{5,})["\']', s))
    return cds


if __name__ == "__main__":
    alc = alcançaveis()
    tst = testados()
    print(f"declarados em codes.py : {len(DECLARADOS)}")
    print(f"alcancaveis no codigo  : {len(alc)}")
    print(f"citados nos testes    : {len(tst)}")

    sem_teste = sorted((alc & DECLARADOS) - tst)
    print(f"\nALCANCAVEIS SEM TESTE DIRETO ({len(sem_teste)}):")
    for c in sem_teste:
        print("  ", c)

    orfaos = sorted(DECLARADOS - alc)
    print(f"\nDECLARADOS MAS NUNCA EMITIDOS ({len(orfaos)}):")
    for c in orfaos:
        print("  ", c)

    print("\n(saida de emergencia: exit 1)")
    sys.exit(0)
