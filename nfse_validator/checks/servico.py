"""Verificacoes de <Servico> / <ListaServico> e reconciliacao de <Total>."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from .. import codes as C
from ..brazil import TOLERANCIA_PADRAO, dentro_da_tolerancia, para_decimal
from ..parser import Node
from .base import Ctx, conferir_ordem

# Ordem do item de servico (perfil nacional ABRASF, sequencia tcDeclaracaoServico).
# Em <Servico> o mesmo nome pode reaparecer em grupos distintos; a ordem aqui
# cobre a sequencia mais comum (codTributacao -> xServ -> valores -> ISS).
ORDEM_SERVICO = [
    "codTributacao", "codServico", "cCodTributacao", "cServico",
    "xServ", "xServico", "tributacao",
    "codMun", "cMun", "cMunFG", "xMun",
    "vServ", "vServico", "vProd", "qUnid", "vAliq", "pAliq",
    "vBC", "vBcd", "vBCPIS", "vBCCOFINS", "vBCPrev",
    "aliq", "aliqServico", "pISS",
    "vISS", "vISSRetido", "vOutro",
    "vPIS", "vCOFINS", "vINSS", "vIR", "vCSLL",
    "vTotTrib", "vTotTribFed", "vTotTribMun",
    "vDesc", "vDescIncond", "vDescCond", "vDeducao",
    "indISS", "retISS", "indISSRetido", "issRetido",
    "indIncentivo", "cBeneficio", "cServicoRef",
    "xListServ", "cListServ",
]
# Ordem de <Total><ISS>: segue a tcTotais do layout nacional.
ORDEM_TOTAL_ISS = ["vBC", "vServicos", "vServicosNaoIncididos", "vISS", "vPIS", "vCOFINS", "dCompet"]
# Ordem de <Total><ISSRetido>: campos consolidados da nota.
ORDEM_TOTAL_ISS_TRIB = [
    "vBC", "vServicos", "vServico", "vProd",
    "vDescIncond", "vDescCond", "vDeducao",
    "vISS", "vISSRetido", "vPIS", "vCOFINS", "vCPP", "vCSLL", "vIR", "vINSS",
    "vOutro", "vRet", "vTotTrib", "vTotTribFed", "vTotTribMun",
    "vLiq", "vNF", "cRegTrib", "indIncentivo",
]


def validar_servico(ctx: Ctx, infnfe: Optional[Node]) -> List[Node]:
    """Devolve a lista de itens de servico (``Servico/ListaServico/Servico``)."""
    if infnfe is None:
        return []
    servico_pai = infnfe.find("Servico")
    if servico_pai is None:
        ctx.erro(
            C.SERVICO_AUSENTE,
            "Elemento <Servico> ausente dentro de <InfNFe>.",
            infnfe.child_path("Servico"),
            "Todo InfNFe precisa de <Servico> descrevendo o servico prestado.",
            infnfe,
        )
        return []
    if not servico_pai.text.strip() and not servico_pai.children:
        ctx.erro(
            C.SERVICO_VAZIO,
            "Elemento <Servico> presente mas vazio.",
            servico_pai.path(),
            "Preencha <Servico> com <ListaServico>.",
            servico_pai,
        )
        return []

    lista = servico_pai.find("ListaServico")
    if lista is None:
        ctx.erro(
            C.LISTA_SERVICO_AUSENTE,
            "Elemento <ListaServico> ausente dentro de <Servico>.",
            servico_pai.child_path("ListaServico"),
            "Inclua <ListaServico> com ao menos um <Servico>.",
            servico_pai,
        )
        return []
    if not lista.children:
        ctx.erro(
            C.LISTA_SERVICO_VAZIA,
            "<ListaServico> sem nenhum item <Servico>.",
            lista.path(),
            "Adicione ao menos um <Servico> com codigo e valor.",
            lista,
        )
        return []

    itens = lista.findall("Servico")
    if len(itens) == 1:
        # Perfil municipal costuma exigir <ListaServico> mesmo com um item.
        pass

    cmu_servico = servico_pai.value("cMun")
    for idx, item in enumerate(itens, start=1):
        _validar_item(ctx, item, idx, cmu_servico)
    return itens


def _validar_item(ctx: Ctx, item: Node, idx: int, cmu_servico: str = "") -> None:
    conferir_ordem(ctx, item, ORDEM_SERVICO, codigo_prefixo="ITEM_SERVICO")

    # Codigo do servico
    codigo = item.value("codTributacao") or item.value("codServico") or item.value("cServico") or item.value("cCodTributacao")
    if not codigo:
        ctx.erro(
            C.ITEM_SERVICO_SEM_CODIGO,
            f"Item {idx} de <ListaServico> sem codigo de tributacao.",
            item.child_path("codTributacao"),
            "Inclua <codTributacao> (ou <codServico>) com o codigo da LC 116/2003.",
            item,
        )
    elif not any(ch.isdigit() for ch in codigo):
        ctx.erro(
            C.ITEM_SERVICO_CODIGO_INVALIDO,
            f"Codigo de servico do item {idx} sem digitos: {codigo!r}.",
            item.path(),
            "Codigos da LC 116 sao numericos, como 01.07, 14.01 ou 17.01.",
            item,
        )

    # Valor do servico
    v_raw = item.value("vServ") or item.value("vServico") or item.value("vProd")
    if not v_raw:
        ctx.erro(
            C.ITEM_SERVICO_SEM_VALOR,
            f"Item {idx} de <ListaServico> sem valor (<vServ> vazio).",
            item.child_path("vServ"),
            "Informe o valor do servico em <vServ>, com ponto decimal.",
            item,
        )
    else:
        valor = para_decimal(v_raw)
        if valor is None:
            ctx.erro(
                C.VALOR_NAO_NUMERICO,
                f"Valor nao numerico em <vServ> do item {idx}: {v_raw!r}.",
                item.child_path("vServ"),
                "Valores monetarios usam ponto decimal e dois digitos, ex.: 1500.00.",
                item.find("vServ"),
            )
        elif valor < 0:
            ctx.erro(
                C.VALOR_NEGATIVO,
                f"Valor negativo em <vServ> do item {idx}: {v_raw!r}.",
                item.child_path("vServ"),
                "Valor de servico nao pode ser negativo. Use <vDesc> para abatimentos.",
                item.find("vServ"),
            )

    if not item.value("vBC") and not item.value("vBC"):
        if item.value("codTributacao") or item.value("vServ") or item.value("vServico"):
            ctx.erro(
                C.ITEM_SERVICO_SEM_BC,
                f"Item {idx} de <ListaServico> sem base de calculo (<vBC>).",
                item.child_path("vBC"),
                "Quando o ISS e devido sobre a base, informe <vBC>.",
                item,
            )

    # Aliquota
    aliq_raw = item.value("aliq") or item.value("pISS")
    if aliq_raw:
        aliq = para_decimal(aliq_raw)
        if aliq is None:
            ctx.erro(
                C.ITEM_SERVICO_ALIQUOTA_INVALIDA,
                f"Aliquota nao numerica no item {idx}: {aliq_raw!r}.",
                item.child_path("aliq"),
                "Informe a aliquota em percentual, ex.: 2.00 para 2%.",
                item.find("aliq") or item.find("pISS"),
            )
        elif aliq < 0 or aliq > 100:
            ctx.erro(
                C.ITEM_SERVICO_ALIQUOTA_INVALIDA,
                f"Aliquota fora da faixa 0-100 no item {idx}: {aliq_raw}.",
                item.child_path("aliq"),
                "A aliquota do ISS e um percentual: use 5.00 para 5%.",
                item.find("aliq") or item.find("pISS"),
            )
        else:
            _conferir_aliquota_implicita(ctx, item, aliq, idx)

    iss_retido = item.value("retISS")
    if iss_retido and iss_retido not in {"1", "2"}:
        ctx.erro(
            C.ITEM_SERVICO_ISS_RETIDO_INVALIDO,
            f"Valor invalido em <retISS> no item {idx}: {iss_retido!r} (esperado 1 ou 2).",
            item.child_path("retISS"),
            "retISS=1 ISS retido na fonte, retISS=2 ISS nao retido.",
            item.find("retISS"),
        )

    cmu_item = item.value("cMun")
    if cmu_servico and cmu_item and cmu_item != cmu_servico:
        ctx.aviso(
            C.LISTA_SERVICO_CODIGO_MUN_DIVERGENTE,
            f"Municipio do item {idx} ({cmu_item}) difere do municipio de <Servico> ({cmu_servico}).",
            item.child_path("cMun"),
            "Em geral cMun do item e igual ao cMun do servico. Divergencia so faz sentido para servico prestado em outro municipio.",
            item.find("cMun"),
        )


def _conferir_aliquota_implicita(ctx: Ctx, item: Node, aliq: Decimal, idx: int) -> None:
    """vISS / base implícita x aliquota declarada.

    Quando o item traz <vISS> e base (vBC ou vServ), a alíquota implicita
    precisa bater com <aliq> dentro da tolerancia configurada. Diferenca menor
    que a tolerancia e arredondamento normal de centavo.
    """
    v_iss = para_decimal(item.value("vISS"))
    if v_iss is None:
        return
    base = para_decimal(item.value("vBC")) or para_decimal(item.value("vServ")) or para_decimal(item.value("vServico"))
    if base is None or base <= 0:
        return
    implicita = (v_iss / base) * Decimal("100")
    diff = implicita - aliq
    if abs(diff) > ctx.tolerancia_aliquota:
        ctx.aviso(
            C.ITEM_SERVICO_ALIQUOTA_DIVERGENTE,
            (
                f"Item {idx}: aliquota implicita em vISS/vBC e {implicita:.4f}% "
                f"mas <aliq> declara {aliq}% (diferenca {diff:.4f} p.p.)."
            ),
            item.path(),
            "Calcule o ISS a partir da aliquota e da base, arredondando para centavos.",
            item,
        )


# --- totais --------------------------------------------------------------
def validar_totais(ctx: Ctx, infnfe: Optional[Node], itens: List[Node]) -> Optional[Node]:
    if infnfe is None:
        return None
    total = infnfe.find("Total")
    if total is None:
        ctx.erro(
            C.TOTAL_AUSENTE,
            "Elemento <Total> ausente dentro de <InfNFe>.",
            infnfe.child_path("Total"),
            "Todo InfNFe precisa de <Total> com os valores consolidados.",
            infnfe,
        )
        return None
    if not total.text.strip() and not total.children:
        ctx.erro(
            C.TOTAL_VAZIO,
            "Elemento <Total> presente mas vazio.",
            total.path(),
            "Preencha <Total> com <ISS> e <ISSRetido>.",
            total,
        )
        return None

    iss = total.find("ISS")
    if iss is None:
        ctx.erro(
            C.TOTAL_ISS_TRIBUTARIO_AUSENTE,
            "Elemento <ISS> ausente dentro de <Total>.",
            total.child_path("ISS"),
            "Inclua <ISS><vServicos> e <vISS>.",
            total,
        )
    else:
        conferir_ordem(ctx, iss, ORDEM_TOTAL_ISS, codigo_prefixo="TOTAL")
        for tag in ("vServicos", "vISS"):
            if iss.is_empty(tag):
                ctx.erro(
                    C.TOTAL_DECIMAL_INVALIDO,
                    f"Campo <{tag}> ausente ou vazio em <Total><ISS>.",
                    iss.child_path(tag),
                    f"Preencha <{tag}> com o valor total.",
                    iss,
                )

    if total.find("ISSRetido") is None:
        ctx.erro(
            C.TOTAL_ISS_RECOLHIDO_AUSENTE,
            "Elemento <ISSRetido> ausente dentro de <Total>.",
            total.child_path("ISSRetido"),
            "Inclua <ISSRetido>. Se o ISS nao foi retido, envie <vISSRetido>0.00.",
            total,
        )
    else:
        conferir_ordem(
            ctx, total.find("ISSRetido"), ORDEM_TOTAL_ISS_TRIB, codigo_prefixo="TOTAL"
        )

    return total


# --- reconciliacao aritmetica -------------------------------------------
def reconciliar(ctx: Ctx, infnfe: Optional[Node], itens: List[Node], total: Optional[Node]) -> None:
    """Confere se os totais batem com a soma dos itens.

    Tolerancia de 0,01 (um centavo) para nao acusar erro por arredondamento.
    """
    if infnfe is None or total is None:
        return
    iss = total.find("ISS") or total
    iss_retido = total.find("ISSRetido") or total

    def _de(parent: Node, tag: str) -> Optional[Decimal]:
        bruto = parent.value(tag)
        if not bruto:
            return None
        v = para_decimal(bruto)
        if v is None:
            ctx.erro(
                C.TOTAL_DECIMAL_INVALIDO,
                f"Valor nao numerico em <{tag}>: {bruto!r}.",
                parent.child_path(tag),
                "Valores monetarios usam ponto decimal, ex.: 1500.00.",
                parent.find(tag),
            )
        return v

    soma_vservico = _soma(ctx, itens, ("vServ", "vServico", "vProd"), "SOMA_VSERVICO_DIVERGENTE")
    soma_vbc = _soma(ctx, itens, ("vBC",), "SOMA_VBC_DIVERGENTE")
    soma_viss = _soma(ctx, itens, ("vISS",), "SOMA_VISS_DIVERGENTE")
    soma_vtottrib = _soma(ctx, itens, ("vTotTrib",), "SOMA_VTOTTRIB_DIVERGENTE")

    # 1. vServicos == soma dos itens
    declarado = _de(iss, "vServicos")
    if declarado is not None and soma_vservico is not None:
        _comparar(ctx, declarado, soma_vservico, "vServicos", "SOMA_VSERVICO_DIVERGENTE",
                  iss, "Soma dos valores dos itens de servico.")

    # 2. vBC == soma das bases
    declarado = _de(iss, "vBC")
    if declarado is not None and soma_vbc is not None:
        _comparar(ctx, declarado, soma_vbc, "vBC", "SOMA_VBC_DIVERGENTE", iss,
                  "Soma das bases de calculo dos itens.")

    # 3. vISS == soma dos ISS dos itens
    declarado = _de(iss, "vISS")
    if declarado is not None and soma_viss is not None:
        _comparar(ctx, declarado, soma_viss, "vISS", "SOMA_VISS_DIVERGENTE", iss,
                  "Soma dos valores de ISS dos itens.")

    # 4. vTotTrib
    declarado = _de(iss_retido, "vTotTrib")
    if declarado is not None and soma_vtottrib is not None:
        _comparar(ctx, declarado, soma_vtottrib, "vTotTrib", "SOMA_VTOTTRIB_DIVERGENTE",
                  iss_retido, "Soma dos tributos sobre servicos (LC 116).")

    # 5. Liquido: vServicos - vDescIncond (+ outras deducoes) == vServico
    base_liq = _de(iss_retido, "vServico") or _de(iss_retido, "vServicos") or _de(iss, "vServicos")
    if base_liq is not None:
        desconto = _de(iss_retido, "vDescIncond") or Decimal("0")
        deducao = _de(iss_retido, "vDeducao") or Decimal("0")
        esperado = base_liq - desconto - deducao
        liquido = _de(iss_retido, "vLiq")
        if liquido is not None:
            _comparar(
                ctx, liquido, esperado, "vLiq", "LIQUIDO_NAO_CONFERE", iss_retido,
                "Valor liquido = base de calculo menos vDescIncond menos vDeducao.",
            )

    # 6. ISS retido so e comparado quando ha valor a reter.
    soma_iss = soma_viss
    declarado_retido = _de(iss_retido, "vISSRetido")
    if declarado_retido is not None and soma_iss is not None and declarado_retido != 0:
        _comparar(ctx, declarado_retido, soma_iss, "vISSRetido",
                  "TOTAL_ISS_RECOLHIDO_DIVERGENTE", iss_retido,
                  "Total de ISS retido na fonte.")

    # 8. Sem itens declarados, os totais precisam ser zero.
    if not itens:
        _exigir_zero(ctx, iss, ("vServicos",), "vServicos", soma_vservico)
        _exigir_zero(ctx, iss, ("vISS",), "vISS", soma_viss)
        _exigir_zero(ctx, iss, ("vBC",), "vBC", soma_vbc)
        ctx.erro(
            C.TOTAL_SEM_ITENS,
            "Nenhum item de servico declarado, mas ha totais consolidados no XML.",
            total.path(),
            "Uma NFS-e sem itens so faz sentido com tudo zerado. Confira se a geracao de <ListaServico> falhou.",
            total,
        )


def _soma(ctx: Ctx, itens: List[Node], tags: tuple, codigo: str) -> Optional[Decimal]:
    total = Decimal("0")
    achou = False
    for item in itens:
        for tag in tags:
            bruto = item.value(tag)
            if bruto:
                v = para_decimal(bruto)
                if v is None:
                    ctx.erro(
                        C.VALOR_NAO_NUMERICO,
                        f"Valor nao numerico em <{tag}>: {bruto!r}.",
                        item.child_path(tag),
                        "Valores monetarios usam ponto decimal, ex.: 1500.00.",
                        item.find(tag),
                    )
                    continue
                total += v
                achou = True
                break
    return total if achou else None


def _comparar(
    ctx: Ctx,
    declarado: Decimal,
    esperado: Decimal,
    campo: str,
    codigo: str,
    node: Node,
    o_que_e: str,
) -> None:
    """Compara declarado x soma; so reporta acima da tolerancia.

    Diferenca de ate um centavo e arredondamento normal e passa. Acima disso
    e divergencia real de calculo.
    """
    diff = declarado - esperado
    if dentro_da_tolerancia(diff, ctx.tolerancia):
        return
    ctx.erro(
        codigo,
        f"<{campo}> declarado ({declarado}) difere da soma ({esperado}). Diferenca de {diff}.",
        node.child_path(campo),
        f"{o_que_e} A diferenca esta acima da tolerancia de {ctx.tolerancia} (centavo).",
        node.find(campo),
    )


def _exigir_zero(ctx: Ctx, node: Node, tags: tuple, rotulo: str, soma: Optional[Decimal]) -> None:
    for tag in tags:
        bruto = node.value(tag)
        if not bruto:
            continue
        v = para_decimal(bruto)
        if v is None:
            continue
        if v != 0:
            ctx.erro(
                C.TOTAL_SEM_ITENS_NAO_ZERO,
                f"<{rotulo}> e {v} mas <ListaServico> esta sem itens: totais deveriam ser zero.",
                node.child_path(tag),
                "Sem itens nao ha valor a consolidar. Zere o total ou corrija a lista de servicos.",
                node.find(tag),
            )
