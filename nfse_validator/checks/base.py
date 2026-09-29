"""Infraestrutura compartilhada das verificacoes.

Um :class:`Ctx` carrega o documento ja parseado, a configuracao e um
acumulador de :class:`Issue`. Cada modulo de ``checks/`` recebe o ``Ctx`` e
devolve uma lista de problemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from ..brazil import TOLERANCIA_PADRAO
from ..parser import Node
from ..report import ERROR, WARNING, Issue


@dataclass
class Ctx:
    """Estado compartilhado entre as verificacoes."""

    root: Node
    source: str = "-"
    tolerancia: Decimal = TOLERANCIA_PADRAO
    tolerancia_aliquota: Decimal = Decimal("0.01")
    agora: Optional[object] = None  # datetime, injetavel para teste
    skew: object = None  # timedelta, injetavel para teste
    issues: List[Issue] = field(default_factory=list)

    # -- emissao de issues ---------------------------------------------
    def erro(self, code: str, message: str, path: str, hint: str = "", node: Optional[Node] = None) -> Issue:
        return self._add(Issue(code, ERROR, message, path, _line(node), _col(node), hint))

    def aviso(self, code: str, message: str, path: str, hint: str = "", node: Optional[Node] = None) -> Issue:
        return self._add(Issue(code, WARNING, message, path, _line(node), _col(node), hint))

    def _add(self, issue: Issue) -> Issue:
        self.issues.append(issue)
        return issue

    # -- acesso a valores ------------------------------------------------
    def decimal_de(self, node: Optional[Node], tag: str) -> Optional[Decimal]:
        from ..brazil import para_decimal

        if node is None:
            return None
        return para_decimal(node.value(tag))

    def texto_de(self, node: Optional[Node], tag: str) -> str:
        return node.value(tag) if node is not None else ""

    def opcional(self, node: Optional[Node], tag: str) -> Optional[Node]:
        return node.find(tag) if node is not None else None


def _line(node: Optional[Node]) -> Optional[int]:
    return node.line if node is not None else None


def _col(node: Optional[Node]) -> Optional[int]:
    return node.column if node is not None else None


# --- helpers de estrutura -------------------------------------------------
def exigir(
    ctx: Ctx,
    pai: Optional[Node],
    tag: str,
    *,
    codigo: Optional[str] = None,
    obrigatorio: bool = True,
    hint: str = "",
) -> Optional[Node]:
    """Garante que ``pai/tag`` exista e nao esteja vazio.

    Devolve o nó (ou ``None``). Quando ``obrigatorio`` e verdadeiro e o
    elemento falta ou esta vazio, emite ``codigo`` (ou ``<TAG>_AUSENTE`` /
    ``<TAG>_VAZIO``) com caminho e posicao corretos.
    """
    if pai is None:
        return None
    node = pai.find(tag)
    prefixo = f"{pai.prefix}:" if pai.prefix else ""
    caminho = f"{pai.path()}/{prefixo}{tag}"
    cod = codigo or tag.upper()
    if node is None:
        if obrigatorio:
            ctx.erro(
                f"{cod}_AUSENTE",
                f"Elemento obrigatorio <{tag}> ausente.",
                caminho,
                hint or f"Inclua <{tag}> dentro de <{pai.tag}>.",
                pai,
            )
        return None
    if not node.text.strip() and not node.children:
        if obrigatorio:
            ctx.erro(
                f"{cod}_VAZIO",
                f"Elemento obrigatorio <{tag}> presente mas vazio.",
                caminho,
                hint or f"Preencha <{tag}> com um valor valido.",
                node,
            )
        return None
    return node


def conferir_ordem(
    ctx: Ctx,
    pai: Node,
    ordem: List[str],
    *,
    codigo_prefixo: str = "",
) -> None:
    """Detecta elementos presentes fora da ordem esperada dentro de ``pai``.

    A ordem do schema e significativa para varios validadores XML: um XSD com
    ``xs:sequence`` rejeita a mesma arvore se as tags estiverem trocadas. Como
    nao usamos XSD, checamos isso a mao.
    """
    if not pai.children:
        return
    posicao_esperada = {nome: i for i, nome in enumerate(ordem)}
    ultimo = -1
    ultimo_tag = ""
    for filho in pai.children:
        if filho.tag not in posicao_esperada:
            continue
        idx = posicao_esperada[filho.tag]
        if idx < ultimo:
            prefixo = f"{pai.prefix}:" if pai.prefix else ""
            ctx.erro(
                f"{codigo_prefixo or pai.tag.upper()}_ORDEM_INVALIDA",
                f"Elemento <{filho.tag}> aparece fora de ordem; <{ultimo_tag}> deveria vir depois.",
                f"{pai.path()}/{prefixo}{filho.tag}",
                (
                    f"Neste perfil a ordem e sequencial: "
                    f"{' -> '.join(ordem)}. Mova <{filho.tag}> para depois de <{ultimo_tag}>."
                ),
                filho,
            )
            return  # um erro de ordem ja basta; evita cascata de falsos positivos
        ultimo = idx
        ultimo_tag = filho.tag
