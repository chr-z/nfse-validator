"""Verificacoes do envelope, da assinatura (presenca) e de <Ide>."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .. import codes as C
from ..brazil import (
    RE_CHAVE,
    ibge_municipio_valido,
    somente_digitos,
    validar_chave_acesso,
)
from ..parser import NAMESPACES_ACEITOS, Node, XmlError
from ..report import Issue
from .base import Ctx, conferir_ordem, exigir

# Elementos de <Ide> na ordem do schema ABRASF (xs:sequence).
ORDEM_IDE = [
    "cStat", "cServ", "cMunFG", "nNF", "cVerif", "dhEmi", "dhSai", "tpNF",
    "idDest", "cMun", "tpImp", "tpEmis", "cDV", "tpAmb", "finNFe", "indFinal",
    "indPres", "indIntermed", "procEmi", "verProc",
]

RE_ISO8601 = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(\.\d+)?"
    r"(Z|[+-]\d{2}:\d{2})$"
)


def validar_envelope(ctx: Ctx) -> Node:
    """Confere a raiz, o namespace e a presenca de ``InfNFe``/``InfNFeSig``."""
    root = ctx.root
    caminho_root = root.path()

    if root.tag != "NFSe":
        ctx.erro(
            C.ENVELOPE_RAIZ_INVALIDA,
            f"Elemento raiz invalido: esperado <NFSe>, encontrado <{root.tag}>.",
            caminho_root,
            "A raiz do documento deve ser <NFSe xmlns=\"http://www.abrasf.org.br/nfse.xsd\">.",
            root,
        )

    ns = root.ns_declarations.get("", "")
    if ns and ns not in NAMESPACES_ACEITOS:
        ctx.aviso(
            C.RAIZ_NAMESPACE_DESCONHECIDO,
            f"Namespace da raiz nao e um perfil ABRASF conhecido: {ns}",
            caminho_root,
            (
                "Este validador conhece os perfis ABRASF e nacional. Se o seu "
                "municipio usa um schema proprio, os nomes de tag podem diferir."
            ),
            root,
        )

    # A raiz pode ser <NFSe> diretamente, ou um envelope externo que contem
    # <NFSe>. Nos dois casos o envelope que importa e o proprio <NFSe>.
    nfse = root if root.tag == "NFSe" else root.find("NFSe")
    if nfse is None:
        ctx.erro(
            C.ENV_NFSE_AUSENTE,
            "Elemento <NFSe> (filho da raiz) ausente.",
            caminho_root,
            "O documento precisa de <NFSe> envolvendo <InfNFeSig> e <InfNFe>.",
            root,
        )
        return root
    if not nfse.text.strip() and not nfse.children:
        ctx.erro(
            C.ENV_NFSE_VAZIA,
            "Elemento <NFSe> presente mas vazio.",
            nfse.path(),
            "Preencha <NFSe> com os dados da nota.",
            nfse,
        )
        return root

    # <InfNFe> vive dentro de <InfNFeSig> no layout assinado, ou direto em
    # <NFSe> no perfil sem assinatura. Procuramos nos dois lugares.
    sig = nfse.find("InfNFeSig")
    infnfe = (sig.find("InfNFe") if sig is not None else None) or nfse.find("InfNFe")
    if infnfe is None:
        ctx.erro(
            C.ENV_INFNFE_AUSENTE,
            "Elemento <InfNFe> ausente dentro de <NFSe>.",
            nfse.child_path("InfNFe"),
            "Inclua <InfNFe> com os dados fiscais da nota.",
            nfse,
        )
    elif not infnfe.text.strip() and not infnfe.children:
        ctx.erro(
            C.ENV_INFNFE_VAZIA,
            "Elemento <InfNFe> presente mas vazio.",
            infnfe.path(),
            "Preencha <InfNFe> com os dados fiscais da nota.",
            infnfe,
        )
    return nfse


def achar_infnfe(ctx: Ctx) -> Optional[Node]:
    """InfNFe dentro de InfNFeSig, ou InfNFe direto (perfil sem signature)."""
    root = ctx.root
    nfse = root if root.tag == "NFSe" else (root.find("NFSe") or root)
    sig = nfse.find("InfNFeSig")
    if sig is not None:
        alvo = sig.find("InfNFe")
        if alvo is not None:
            # Um documento com <InfNFe> dentro E fora de <InfNFeSig> tem duas
            # copias da nota. Pegamos a assinada para nao duplicar erros, mas
            # sinalizamos a ambiguidade.
            if nfse.find("InfNFe") is not None:
                ctx.erro(
                    "ENV_INFNFE_DUPLICADO",
                    "<InfNFe> aparece dentro e fora de <InfNFeSig>: o documento tem duas copias da nota.",
                    nfse.child_path("InfNFe"),
                    "No layout ABRASF, <InfNFe> fica dentro de <InfNFeSig>. Remova a copia solta.",
                    nfse,
                )
            return alvo
    return nfse.find("InfNFe")


# --- assinatura -----------------------------------------------------------
def validar_assinatura(ctx: Ctx, nfse: Optional[Node]) -> None:
    """Presenca de assinatura. **Nao** faz verificacao criptografica.

    A validacao criptografica (XMLDSig/RSA) exige uma biblioteca de
    assinatura e o certificado do emitente. Esta ferramenta checa apenas a
    estrutura: se a assinatura existe, esta no lugar certo e tem os campos
    minimos preenchidos.
    """
    if nfse is None:
        return
    sig = nfse.find("InfNFeSig")
    if sig is None:
        ctx.erro(
            C.INFNFESIG_AUSENTE,
            "Elemento <InfNFeSig> ausente: a NFS-e nao tem bloco de assinatura.",
            nfse.child_path("InfNFeSig"),
            "Todo XML de NFS-e assinado precisa de <InfNFeSig> contendo <Signature>.",
            nfse,
        )
        return
    if not sig.text.strip() and not sig.children:
        ctx.erro(
            C.INFNFESIG_VAZIA,
            "Elemento <InfNFeSig> presente mas vazio.",
            sig.path(),
            "Preencha <InfNFeSig> com <Signature>.",
            sig,
        )
        return

    assinatura = sig.find("Signature")
    if assinatura is None:
        ctx.erro(
            C.ASSINATURA_AUSENTE,
            "Elemento <Signature> ausente dentro de <InfNFeSig>.",
            sig.child_path("Signature"),
            "Inclua <Signature> com <SignedInfo> e <SignatureValue>.",
            sig,
        )
        return
    if not assinatura.text.strip() and not assinatura.children:
        ctx.erro(
            C.ASSINATURA_VAZIA,
            "Elemento <Signature> presente mas vazio.",
            assinatura.path(),
            "Preencha <Signature>.",
            assinatura,
        )
        return

    # <Reference> normalmente vive dentro de <SignedInfo>; procuramos nos dois
    # lugares para aceitar o layout completo e tambem o simplificado.
    signed_info = assinatura.find("SignedInfo")
    reference = assinatura.find("Reference") or (signed_info.find("Reference") if signed_info else None)
    if reference is None:
        ctx.erro(
            C.ASSINATURA_REFERENCE_AUSENTE,
            "Elemento <Reference> ausente dentro de <Signature>.",
            assinatura.child_path("Reference"),
            "Inclua <Reference URI=\"#NFe...\">.",
            assinatura,
        )
    else:
        # <Reference> e um elemento com atributo URI: pode legitimamente ter
        # texto vazio, entao so tratamos como vazio quando nao tem texto nem
        # filhos nem atributos.
        if not reference.text.strip() and not reference.children and not reference.attrs:
            ctx.erro(
                C.ASSINATURA_REFERENCE_VAZIA,
                "Elemento <Reference> presente mas totalmente vazio.",
                reference.path(),
                "Preencha <Reference URI=\"#NFe<chave de acesso>\">.",
                reference,
            )
        uri = reference.attrs.get("URI", "")
        if uri and not uri.startswith("#"):
            ctx.erro(
                C.ASSINATURA_URI_INVALIDA,
                f"Atributo URI invalido em <Reference>: {uri!r}.",
                reference.path(),
                "Em NFS-e o URI e uma referencia interna, no formato #NFe<chave de acesso>. Deve comecar com '#'.",
                reference,
            )

    valor = assinatura.find("SignatureValue")
    if valor is None:
        ctx.erro(
            C.ASSINATURA_SIGNATUREVALUE_AUSENTE,
            "Elemento <SignatureValue> ausente dentro de <Signature>.",
            assinatura.child_path("SignatureValue"),
            "Inclua <SignatureValue> com a assinatura em Base64.",
            assinatura,
        )
    elif not valor.text.strip():
        ctx.erro(
            C.ASSINATURA_SIGNATUREVALUE_VAZIA,
            "Elemento <SignatureValue> presente mas vazio.",
            valor.path(),
            "Preencha <SignatureValue> com a assinatura em Base64.",
            valor,
        )

    # Assinatura fora do InfNFeSig sugere documento montado errado.
    if nfse.find("Signature") is not None:
        ctx.erro(
            C.ASSINATURA_FORA_DE_INFNFE,
            "<Signature> aparece fora de <InfNFeSig>.",
            nfse.child_path("Signature"),
            "A assinatura deve ficar dentro de <InfNFeSig>.",
            nfse,
        )


# --- Ide ------------------------------------------------------------------
def _parse_iso(valor: str) -> Optional[datetime]:
    m = RE_ISO8601.match(valor.strip())
    if not m:
        return None
    ano, mes, dia, hora, minuto, seg = (int(m.group(i)) for i in range(1, 7))
    tz_txt = m.group(8)
    if tz_txt == "Z":
        tzinfo = timezone.utc
    else:
        sinal = 1 if tz_txt[0] == "+" else -1
        off = timedelta(hours=int(tz_txt[1:3]), minutes=int(tz_txt[4:6]))
        tzinfo = timezone(sinal * off)
    try:
        return datetime(ano, mes, dia, hora, minuto, seg, tzinfo=tzinfo)
    except ValueError:
        return None


def validar_ide(ctx: Ctx, infnfe: Optional[Node]) -> None:
    if infnfe is None:
        return
    ide = infnfe.find("Ide")
    if ide is None:
        ctx.erro(
            C.IDE_AUSENTE,
            "Elemento <Ide> ausente dentro de <InfNFe>.",
            infnfe.child_path("Ide"),
            "Todo InfNFe precisa de <Ide> com os dados de identificacao da nota.",
            infnfe,
        )
        return
    if not ide.text.strip() and not ide.children:
        ctx.erro(
            C.IDE_VAZIO,
            "Elemento <Ide> presente mas vazio.",
            ide.path(),
            "Preencha <Ide>.",
            ide,
        )
        return

    conferir_ordem(ctx, ide, ORDEM_IDE, codigo_prefixo="IDE")

    # cStat
    if ide.is_empty("cStat"):
        ctx.erro(
            C.IDE_CSTAT_OBRIGATORIO,
            "Campo obrigatorio <cStat> ausente ou vazio em <Ide>.",
            ide.child_path("cStat"),
            "Use <cStat>1</cStat> para NFS-e normal (emissao de servico efetuada).",
            ide,
        )
    else:
        cstat = ide.value("cStat")
        if cstat not in {"1"}:
            ctx.erro(
                C.IDE_CSTAT_INVALIDO,
                f"Valor invalido em <cStat>: {cstat!r}. Para NFS-e so o codigo 1 e valido.",
                ide.child_path("cStat"),
                "Em NFS-e, <cStat> deve ser 1. Se voce esta enviando 2,6 ou 9, este XML e de NF-e, nao de NFS-e.",
                ide.find("cStat"),
            )

    # nNF
    if ide.is_empty("nNF"):
        ctx.erro(
            C.IDE_NNF_OBRIGATORIO,
            "Campo obrigatorio <nNF> (numero da nota) ausente ou vazio.",
            ide.child_path("nNF"),
            "Inclua <nNF> com um numero inteiro positivo.",
            ide,
        )
    else:
        nnf = ide.value("nNF")
        if not somente_digitos(nnf):
            ctx.erro(
                C.IDE_NNF_NAO_NUMERICO,
                f"Valor nao numerico em <nNF>: {nnf!r}.",
                ide.child_path("nNF"),
                "<nNF> e um inteiro sem zeros a esquerda obrigatorios.",
                ide.find("nNF"),
            )
        else:
            try:
                if int(nnf) <= 0:
                    ctx.erro(
                        C.IDE_NNF_NAO_POSITIVO,
                        f"<nNF> deve ser maior que zero, encontrado {nnf!r}.",
                        ide.child_path("nNF"),
                        "Numeracao de NFS-e comeca em 1.",
                        ide.find("nNF"),
                    )
            except ValueError:
                pass

    # dhEmi / dEmi
    dt = None
    ano_emissao = None
    if ide.is_empty("dhEmi") and ide.is_empty("dEmi"):
        ctx.erro(
            C.IDE_DTEMI_OBRIGATORIO,
            "Campo obrigatorio <dhEmi> (ou <dEmi>) ausente em <Ide>.",
            ide.child_path("dhEmi"),
            "Inclua <dhEmi> no formato ISO-8601 com fuso, ex.: 2026-01-15T10:30:00-03:00.",
            ide,
        )
    else:
        node_dt = ide.find("dhEmi") or ide.find("dEmi")
        bruto = node_dt.text.strip()
        dt = _parse_iso(bruto)
        if dt is None:
            if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", bruto):
                ctx.erro(
                    C.IDE_DTEMI_INVALIDO,
                    f"Data/hora invalida em <dhEmi>: {bruto!r}.",
                    node_dt.path(),
                    "O formato esperado e ISO-8601: 2026-01-15T10:30:00-03:00.",
                    node_dt,
                )
            elif re.match(r"^\d{4}-\d{2}-\d{2}", bruto):
                ctx.erro(
                    C.IDE_DTEMI_SEM_FUSO,
                    f"<dEmi> sem fuso horario: {bruto!r}.",
                    node_dt.path(),
                    "Quando usar <dEmi>, inclua o fuso (ex.: 2026-01-15T10:30:00-03:00).",
                    node_dt,
                )
            else:
                ctx.erro(
                    C.IDE_DTEMI_INVALIDO,
                    f"Data/hora invalida em <dhEmi>: {bruto!r}.",
                    node_dt.path(),
                    "O formato esperado e ISO-8601: 2026-01-15T10:30:00-03:00.",
                    node_dt,
                )
        else:
            ano_emissao = dt.year
            _conferir_data(ctx, node_dt, dt)

    # Chave de acesso
    chave_node = ide.find("chNFe")
    if chave_node is None or not chave_node.text.strip():
        ctx.erro(
            C.IDE_CHAVE_ACESSO_OBRIGATORIA,
            "Campo obrigatorio <chNFe> (chave de acesso) ausente ou vazio.",
            ide.child_path("chNFe"),
            "Inclua <chNFe> com os 44 digitos da chave de acesso.",
            ide,
        )
    else:
        chave = somente_digitos(chave_node.text)
        if not RE_CHAVE.match(chave):
            ctx.erro(
                C.IDE_CHAVE_ACESSO_INVALIDA,
                f"Chave de acesso invalida: {chave_node.text.strip()!r} (esperado 44 digitos).",
                chave_node.path(),
                "A chave de acesso tem 44 digitos, apenas numeros, sem pontuacao.",
                chave_node,
            )
        else:
            ano_esperado = ano_emissao
            ok = validar_chave_acesso(chave, ano_esperado=ano_esperado)
            if not ok:
                ctx.erro(
                    C.IDE_CHAVE_ACESSO_INVALIDA,
                    "Chave de acesso invalida: digito verificador mod-11 ou posicoes de UF/ano nao conferem.",
                    chave_node.path(),
                    "A chave tem 44 digitos com DV mod-11. Confira os 43 primeiros digitos e recalcule o ultimo.",
                    chave_node,
                )
            elif ano_esperado is not None and int(chave[2:4]) != ano_esperado % 100:
                ctx.aviso(
                    C.IDE_CHAVE_ACESSO_ANO_DIVERGENTE,
                    f"Ano da chave de acesso ({chave[2:4]}) difere do ano de emissao ({ano_esperado}).",
                    chave_node.path(),
                    "A posicao 3-4 da chave traz AAMM. Emissao e chave devem concordar.",
                    chave_node,
                )

    # cMunFG
    cmunfg = None
    if ide.is_empty("cMunFG"):
        ctx.erro(
            C.IDE_CMUNFG_OBRIGATORIO,
            "Campo obrigatorio <cMunFG> (codigo IBGE do municipio de geracao) ausente ou vazio.",
            ide.child_path("cMunFG"),
            "Inclua <cMunFG> com 7 digitos do codigo IBGE do municipio emissor.",
            ide,
        )
    else:
        cmunfg = ide.value("cMunFG")
        if not ibge_municipio_valido(cmunfg):
            ctx.erro(
                C.IDE_CMUNFG_INVALIDO,
                f"Codigo de municipio invalido em <cMunFG>: {cmunfg!r}.",
                ide.child_path("cMunFG"),
                "Use o codigo IBGE com 7 digitos (ex.: 3550308 para Sao Paulo/SP).",
                ide.find("cMunFG"),
            )

    # cMun vs cMunFG
    if not ide.is_empty("cMun") and cmunfg:
        cmun = ide.value("cMun")
        if not ibge_municipio_valido(cmun):
            ctx.erro(
                C.IDE_CMUN_INVALIDO,
                f"Codigo de municipio invalido em <cMun>: {cmun!r}.",
                ide.child_path("cMun"),
                "Use o codigo IBGE com 7 digitos.",
                ide.find("cMun"),
            )
        elif cmun != cmunfg:
            ctx.aviso(
                C.IDE_CMUN_CMUNFG_DIVERGEM,
                f"<cMun> ({cmun}) difere de <cMunFG> ({cmunfg}).",
                ide.child_path("cMun"),
                "Em geral cMunFG e cMun sao iguais. Divergencia so faz sentido se o servico for prestado em outro municipio.",
                ide.find("cMun"),
            )

    # tpAmb
    if not ide.is_empty("tpAmb") and ide.value("tpAmb") not in {"1", "2"}:
        ctx.aviso(
            C.IDE_TPAMB_INVALIDO,
            f"Valor inesperado em <tpAmb>: {ide.value('tpAmb')!r} (esperado 1 para producao ou 2 para homologacao).",
            ide.child_path("tpAmb"),
            "tpAmb=1 producao, tpAmb=2 homologacao.",
            ide.find("tpAmb"),
        )


def _conferir_data(ctx: Ctx, node: Node, dt: datetime) -> None:
    agora = ctx.agora or datetime.now(timezone.utc)
    skew = ctx.skew if ctx.skew is not None else timedelta(minutes=5)
    if dt.tzinfo is None:
        return
    if dt > agora + skew:
        ctx.aviso(
            C.IDE_DTEMI_FUTURO,
            f"Data de emissao no futuro: {dt.isoformat()} (agora: {agora.isoformat()}).",
            node.path(),
            "O relogio do servidor emissor pode estar adiantado, ou o XML foi gerado com data trocada.",
            node,
        )
    elif dt < agora - timedelta(days=30):
        ctx.aviso(
            C.IDE_DTEMI_ANTIGO,
            f"Data de emissao muito antiga: {dt.isoformat()}.",
            node.path(),
            "Emissao com mais de 30 dias pode ser rejeitada pelo provedor.",
            node,
        )
