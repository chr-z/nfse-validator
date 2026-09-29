"""Ponto de entrada das verificacoes.

Cada funcao aqui recebe o :class:`~nfse_validator.checks.base.Ctx` ja com a
arvore parseada e devolve/acumula os problemas. A ordem importa: as
verificacoes de estrutura vem antes da reconciliacao aritmetica, que depende
dos itens ja identificados.
"""

from __future__ import annotations

from typing import List

from ..parser import Node
from ..report import Issue
from .base import Ctx
from .emitente import validar_destinatario, validar_emitente
from .ide import achar_infnfe, validar_assinatura, validar_envelope, validar_ide
from .servico import reconciliar, validar_servico, validar_totais

__all__ = [
    "Ctx",
    "executar",
    "achar_infnfe",
    "validar_envelope",
    "validar_ide",
    "validar_emitente",
    "validar_destinatario",
    "validar_servico",
    "validar_totais",
    "reconciliar",
    "validar_assinatura",
]


def executar(ctx: Ctx) -> List[Issue]:
    """Roda todas as verificacoes e devolve a lista de issues."""
    nfse = validar_envelope(ctx)
    infnfe = achar_infnfe(ctx)
    validar_ide(ctx, infnfe)
    validar_emitente(ctx, infnfe)
    validar_destinatario(ctx, infnfe)
    itens = validar_servico(ctx, infnfe)
    total = validar_totais(ctx, infnfe, itens)
    reconciliar(ctx, infnfe, itens, total)
    validar_assinatura(ctx, nfse)
    return ctx.issues
