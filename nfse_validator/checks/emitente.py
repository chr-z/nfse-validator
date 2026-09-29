"""Verificacoes de <Emitente>, <Destinatario> e <Endereco>."""

from __future__ import annotations

from typing import Optional

from .. import codes as C
from ..brazil import (
    RE_CNPJ,
    RE_CPF,
    cep_valido,
    fone_valido,
    somente_digitos,
    uf_valida,
    validar_cnpj,
    validar_cpf,
)
from ..parser import Node
from .base import Ctx, conferir_ordem, exigir

ORDEM_EMITENTE = [
    "CNPJ", "CPF", "xNome", "xFant", "EndeEmit", "xMun", "UF", "IE", "IEST",
    "IM", "CNAE", "CRT",
]
ORDEM_DESTINATARIO = [
    "CPF", "CNPJ", "idEstrangeiro", "xNome", "EndeDest", "xMun", "UF", "IE",
    "ISUF", "IM", "Email",
]
ORDEM_ENDERECO = ["xLgr", "nro", "xCpl", "xBairro", "cMun", "xMun", "UF", "CEP", "cPais", "xPais", "fone"]


def validar_emitente(ctx: Ctx, infnfe: Optional[Node]) -> Optional[Node]:
    if infnfe is None:
        return None
    emit = infnfe.find("Emitente")
    if emit is None:
        ctx.erro(
            C.EMITENTE_AUSENTE,
            "Elemento <Emitente> ausente dentro de <InfNFe>.",
            infnfe.child_path("Emitente"),
            "Todo InfNFe precisa de <Emitente> com os dados do prestador de servico.",
            infnfe,
        )
        return None
    if not emit.text.strip() and not emit.children:
        ctx.erro(
            C.EMITENTE_VAZIO,
            "Elemento <Emitente> presente mas vazio.",
            emit.path(),
            "Preencha <Emitente>.",
            emit,
        )
        return None

    conferir_ordem(ctx, emit, ORDEM_EMITENTE, codigo_prefixo="EMITENTE")

    cnpj_node = emit.find("CNPJ")
    cpf_node = emit.find("CPF")

    if cnpj_node is not None and cpf_node is not None:
        ctx.erro(
            C.EMITENTE_CNPJ_E_CPF,
            "<Emitente> tem <CNPJ> e <CPF> ao mesmo tempo; escolha um.",
            emit.path(),
            "Preencha apenas um: <CNPJ> para pessoa juridica, <CPF> para pessoa fisica.",
            emit,
        )

    if cnpj_node is not None:
        bruto = cnpj_node.text.strip()
        digitos = somente_digitos(bruto)
        if not digitos:
            ctx.erro(
                C.EMITENTE_CNPJ_OBRIGATORIO,
                "<CNPJ> do emitente presente mas vazio.",
                cnpj_node.path(),
                "Preencha o CNPJ com 14 digitos, apenas numeros.",
                cnpj_node,
            )
        elif RE_CPF.match(digitos):
            ctx.erro(
                C.EMITENTE_CNPJ_E_CPF,
                f"<CNPJ> do emitente contem {len(digitos)} digitos: parece um CPF, nao um CNPJ.",
                cnpj_node.path(),
                "CPF tem 11 digitos e CNPJ tem 14. Confira se nao gravou o documento errado no campo.",
                cnpj_node,
            )
        elif not RE_CNPJ.match(digitos):
            ctx.erro(
                C.EMITENTE_CNPJ_INVALIDO,
                f"<CNPJ> do emitente invalido: {bruto!r} (esperado 14 digitos).",
                cnpj_node.path(),
                "O CNPJ tem 14 digitos, apenas numeros, sem pontos, barras ou espacos.",
                cnpj_node,
            )
        elif not validar_cnpj(digitos):
            ctx.erro(
                C.EMITENTE_CNPJ_INVALIDO,
                f"CNPJ do emitente {digitos} tem digito verificador incorreto.",
                cnpj_node.path(),
                "Recalcule os dois digitos verificadores do CNPJ. Em PHP, use a funcao de validacao do seu SDK ou faca o calculo mod-11.",
                cnpj_node,
            )
    elif cpf_node is not None:
        digitos = somente_digitos(cpf_node.text)
        if not digitos:
            ctx.erro(
                C.EMITENTE_CPF_OBRIGATORIO,
                "<CPF> do emitente presente mas vazio.",
                cpf_node.path(),
                "Preencha o CPF com 11 digitos.",
                cpf_node,
            )
        elif not RE_CPF.match(digitos):
            ctx.erro(
                C.EMITENTE_CPF_INVALIDO,
                f"<CPF> do emitente invalido: {cpf_node.text.strip()!r} (esperado 11 digitos).",
                cpf_node.path(),
                "O CPF tem 11 digitos, apenas numeros.",
                cpf_node,
            )
        elif not validar_cpf(digitos):
            ctx.erro(
                C.EMITENTE_CPF_INVALIDO,
                f"CPF do emitente {digitos} tem digito verificador incorreto.",
                cpf_node.path(),
                "Recalcule os dois digitos verificadores do CPF (mod-11).",
                cpf_node,
            )
    else:
        ctx.erro(
            C.EMITENTE_CNPJ_OBRIGATORIO,
            "<Emitente> sem <CNPJ> e sem <CPF>: nao ha como identificar o prestador.",
            emit.path(),
            "Inclua <CNPJ> (pessoa juridica) ou <CPF> (pessoa fisica).",
            emit,
        )

    # Nome / razao social
    nome = emit.value("xNome")
    if not nome:
        fant = emit.value("xFant")
        if not fant:
            ctx.erro(
                C.EMITENTE_RAZAO_SOCIAL_OBRIGATORIA,
                "<Emitente> sem <xNome> (razao social) ou <xFant> (nome fantasia).",
                emit.child_path("xNome"),
                "Inclua <xNome> com a razao social do prestador.",
                emit,
            )
        else:
            ctx.erro(
                C.EMITENTE_NOME_OBRIGATORIO,
                "<Emitente> tem <xFant> mas nao tem <xNome> (razao social).",
                emit.child_path("xNome"),
                "Nome fantasia sozinho nao substitui a razao social nesta posicao.",
                emit,
            )

    # UF
    uf = emit.value("UF")
    if uf and not uf_valida(uf):
        ctx.erro(
            C.EMITENTE_UF_INVALIDA,
            f"UF invalida no emitente: {uf!r}.",
            emit.child_path("UF"),
            "Use a sigla de uma UF brasileira (ex.: SP, RJ, MG).",
            emit.find("UF"),
        )

    _validar_endereco(ctx, emit.find("EndeEmit"), "ENDERECO")
    return emit


def _validar_endereco(ctx: Ctx, ender: Optional[Node], prefixo: str) -> None:
    if ender is None:
        return
    conferir_ordem(ctx, ender, ORDEM_ENDERECO, codigo_prefixo=prefixo)
    cep = ender.value("CEP")
    if cep and not cep_valido(cep):
        ctx.erro(
            f"{prefixo}_CEP_INVALIDO",
            f"CEP invalido: {cep!r} (esperado 8 digitos).",
            ender.child_path("CEP"),
            "CEP tem 8 digitos, apenas numeros.",
            ender.find("CEP"),
        )
    fone = ender.value("fone")
    if fone and not fone_valido(fone):
        ctx.erro(
            f"{prefixo}_TEL_INVALIDO",
            f"Telefone invalido: {fone!r} (esperado 10 ou 11 digitos).",
            ender.child_path("fone"),
            "DDD com 2 digitos + numero de 8 ou 9 digitos, apenas numeros.",
            ender.find("fone"),
        )


def validar_destinatario(ctx: Ctx, infnfe: Optional[Node]) -> Optional[Node]:
    if infnfe is None:
        return None
    dest = infnfe.find("Destinatario")
    if dest is None:
        ctx.aviso(
            C.DESTINATARIO_AUSENTE,
            "<Destinatario> ausente: a NFS-e foi emitida sem tomador identificado.",
            infnfe.child_path("Destinatario"),
            "Muitas NFS-e para pessoa fisica sao emitidas sem destinatario. Se o servico e B2B, o provedor pode exigir.",
            infnfe,
        )
        return None
    if not dest.text.strip() and not dest.children:
        ctx.aviso(
            C.DESTINATARIO_VAZIO,
            "<Destinatario> presente mas vazio.",
            dest.path(),
            "Preencha <Destinatario> ou remova o elemento.",
            dest,
        )
        return None

    conferir_ordem(ctx, dest, ORDEM_DESTINATARIO, codigo_prefixo="DESTINATARIO")

    cpf_node = dest.find("CPF")
    cnpj_node = dest.find("CNPJ")
    estrangeiro = dest.find("idEstrangeiro")

    if cpf_node is not None and cnpj_node is not None:
        ctx.erro(
            C.DESTINATARIO_CPF_E_CNPJ,
            "<Destinatario> tem <CPF> e <CNPJ> ao mesmo tempo; escolha um.",
            dest.path(),
            "Preencha apenas um dos dois.",
            dest,
        )
    elif cpf_node is not None:
        digitos = somente_digitos(cpf_node.text)
        if digitos and not RE_CPF.match(digitos):
            ctx.erro(
                C.DESTINATARIO_CPF_INVALIDO,
                f"CPF do destinatario invalido: {cpf_node.text.strip()!r} (esperado 11 digitos).",
                cpf_node.path(),
                "O CPF tem 11 digitos.",
                cpf_node,
            )
        elif digitos and not validar_cpf(digitos):
            ctx.erro(
                C.DESTINATARIO_CPF_INVALIDO,
                f"CPF do destinatario {digitos} tem digito verificador incorreto.",
                cpf_node.path(),
                "Recalcule os digitos verificadores do CPF.",
                cpf_node,
            )
    elif cnpj_node is not None:
        digitos = somente_digitos(cnpj_node.text)
        if digitos and not RE_CNPJ.match(digitos):
            ctx.erro(
                C.DESTINATARIO_CNPJ_INVALIDO,
                f"CNPJ do destinatario invalido: {cnpj_node.text.strip()!r} (esperado 14 digitos).",
                cnpj_node.path(),
                "O CNPJ tem 14 digitos.",
                cnpj_node,
            )
        elif digitos and not validar_cnpj(digitos):
            ctx.erro(
                C.DESTINATARIO_CNPJ_INVALIDO,
                f"CNPJ do destinatario {digitos} tem digito verificador incorreto.",
                cnpj_node.path(),
                "Recalcule os digitos verificadores do CNPJ.",
                cnpj_node,
            )
    elif estrangeiro is None:
        ctx.erro(
            C.DESTINATARIO_SEM_DOCUMENTO,
            "<Destinatario> sem <CPF>, <CNPJ> ou <idEstrangeiro>.",
            dest.path(),
            "Identifique o tomador por um dos tres campos.",
            dest,
        )

    _validar_endereco(ctx, dest.find("EndeDest"), "ENDERECO")
    return dest
