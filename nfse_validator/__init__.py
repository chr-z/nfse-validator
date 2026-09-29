"""NFS-e Validador - validacao offline de XML de NFS-e (ABRASF / padrao nacional).

Uso basico::

    from nfse_validator import validate

    relatorio = validate(xml_bytes, strict=False)
    if not relatorio.ok:
        for erro in relatorio.errors:
            print(erro.code, erro.path, erro.message)

Sem dependencias, sem rede, sem telemetria. Tudo roda na sua maquina.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Union

from .brazil import TOLERANCIA_PADRAO
from .checks import Ctx, executar
from .parser import XmlError, parse
from .report import ERROR, WARNING, Issue, Report, make_report

__version__ = "1.0.0"

__all__ = [
    "validate",
    "Report",
    "Issue",
    "XmlError",
    "TOLERANCIA_PADRAO",
    "__version__",
]

Dados = Union[bytes, str]


def validate(
    xml: Dados,
    *,
    strict: bool = False,
    source: str = "-",
    tolerancia: Decimal = TOLERANCIA_PADRAO,
    tolerancia_aliquota: Optional[Decimal] = None,
) -> Report:
    """Valida um XML de NFS-e e devolve um :class:`Report`.

    ``strict=True`` promove todo warning a error.
    ``tolerancia`` controla o limite (em reais) das comparacoes aritmeticas;
    o padrao e 0,01, ou seja, um centavo.
    """
    try:
        root = parse(xml, source=source)
    except XmlError as exc:
        return make_report([exc.issue], strict=strict, source=source)

    ctx = Ctx(root=root, source=source, tolerancia=tolerancia)
    if tolerancia_aliquota is not None:
        ctx.tolerancia_aliquota = tolerancia_aliquota
    issues = executar(ctx)
    return make_report(issues, strict=strict, source=source)
