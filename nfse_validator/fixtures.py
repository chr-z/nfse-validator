"""Fabrica de XML sintetico de NFS-e para testes e demonstracoes.

Todos os dados aqui e SINTETICO: CNPJ, CPF, chave de acesso, enderecos e
nomes sao gerados algoritmicamente e nao correspondem a nenhuma empresa ou
pessoa real. Os valores de cheque usam digitos verificadores calculados de
verdade, para que a validacao exercite o caminho feliz.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .brazil import gerar_chave_acesso, gerar_cnpj, gerar_cpf

# Documento-base sintetico. CNPJ/CPF com digitos verificadores corretos.
CNPJ_SINTETICO = gerar_cnpj("112223330001")
CPF_SINTETICO = gerar_cpf("987654321")
CNPJ_HOMOLOG = gerar_cnpj("9988776655")


def _item_servico(
    *,
    codigo: str = "01.07",
    descricao: str = "Servico de teste sintetico",
    v_serv: str = "1000.00",
    v_bc: str = "1000.00",
    v_iss: str = "50.00",
    aliq: str = "5.00",
    v_tot_trib: str = "120.00",
    extra: Optional[Dict[str, str]] = None,
) -> str:
    partes = [
        f"<codTributacao>{codigo}</codTributacao>",
        f"<xServ>{descricao}</xServ>",
        f"<vServ>{v_serv}</vServ>",
        f"<vBC>{v_bc}</vBC>",
        f"<aliq>{aliq}</aliq>",
        f"<vISS>{v_iss}</vISS>",
    ]
    if v_tot_trib:
        partes.append(f"<vTotTrib>{v_tot_trib}</vTotTrib>")
    partes.append("<indISS>1</indISS>")
    for chave, valor in (extra or {}).items():
        partes.append(f"<{chave}>{valor}</{chave}>")
    return "<Servico>" + "".join(partes) + "</Servico>"


def _dt_referencia() -> str:
    """Data de emissao recente, com fuso de Sao Paulo, calculada de hoje.

    Mantem o XML valido sem depender de uma data fixa no futuro.
    """
    agora = datetime.now(timezone(timedelta(hours=-3)))
    alvo = agora - timedelta(days=2)
    return alvo.replace(microsecond=0, second=0).isoformat()


def _chave_de_referencia(cnpj: str, uf: str, n_nf: int) -> str:
    agora = datetime.now(timezone(timedelta(hours=-3)))
    return gerar_chave_acesso(uf=uf, cnpj=cnpj, numero=n_nf, ano=agora.year, mes=agora.month)


def documento_base(
    *,
    dt_emi: Optional[str] = None,
    chave: Optional[str] = None,
    cnpj: str = CNPJ_SINTETICO,
    cpf_dest: Optional[str] = CPF_SINTETICO,
    itens: Optional[List[str]] = None,
    v_servicos: str = "1000.00",
    v_bc_total: str = "1000.00",
    v_iss_total: str = "50.00",
    v_tot_trib_total: str = "120.00",
    v_liq: str = "950.00",
    v_desc_incond: str = "50.00",
    v_iss_retido: str = "0.00",
    c_stat: str = "1",
    n_nf: str = "1",
    c_mun_fg: str = "3550308",
    uf: str = "SP",
    sem_destinatario: bool = False,
    sem_ide: bool = False,
    sem_infnsig: bool = False,
    assinatura_incompleta: bool = False,
    assinatura_vazia: bool = False,
    assinatura_sem_reference: bool = False,
    assinatura_sem_valor: bool = False,
    assinatura_valor_vazio: bool = False,
    assinatura_fora: bool = False,
    uri_invalida: bool = False,
    itens_total_overrides: Optional[Dict[str, str]] = None,
) -> str:
    """Monta um XML de NFS-e sintetico.

    Os parametros existem para que cada teste quebre exatamente uma coisa.
    """
    if chave is None:
        chave = _chave_de_referencia(cnpj, uf, int(n_nf or 1))
    if dt_emi is None:
        dt_emi = _dt_referencia()

    if itens is None:
        itens = [_item_servico(**(itens_total_overrides or {}))]

    ide_partes: List[str] = []
    if not sem_ide:
        ide_partes = [
            f"<cStat>{c_stat}</cStat>",
            "<cServ>1</cServ>",
            f"<cMunFG>{c_mun_fg}</cMunFG>",
            f"<nNF>{n_nf}</nNF>",
            f"<dhEmi>{dt_emi}</dhEmi>",
            "<tpNF>1</tpNF>",
            f"<cMun>{c_mun_fg}</cMun>",
            "<tpImp>1</tpImp>",
            "<tpEmis>1</tpEmis>",
            "<cDV>1</cDV>",
            "<tpAmb>2</tpAmb>",
            "<indFinal>0</indFinal>",
            "<indPres>1</indPres>",
            f"<chNFe>{chave}</chNFe>",
        ]
    ide = "<Ide>" + "".join(ide_partes) + "</Ide>" if not sem_ide else ""

    emitente = (
        "<Emitente>"
        f"<CNPJ>{cnpj}</CNPJ>"
        "<xNome>EMPRESA SINTETICA DE TESTE LTDA</xNome>"
        "<xFant>EMPRESA SINTETICA</xFant>"
        "<EndeEmit>"
        "<xLgr>Rua Sintetica</xLgr><nro>100</nro><xBairro>Centro</xBairro>"
        f"<cMun>{c_mun_fg}</cMun><xMun>Cidade Sintetica</xMun><UF>{uf}</UF>"
        "<CEP>01001000</CEP><cPais>1058</cPais><xPais>BRASIL</xPais>"
        "<fone>1133334444</fone>"
        "</EndeEmit>"
        f"<xMun>Cidade Sintetica</xMun><UF>{uf}</UF><IE>ISENTO</IE><CRT>3</CRT>"
        "</Emitente>"
    )

    if sem_destinatario:
        destinatario = ""
    else:
        destinatario = (
            "<Destinatario>"
            f"<CPF>{cpf_dest}</CPF>"
            "<xNome>CLIENTE SINTETICO</xNome>"
            "<EndeDest>"
            "<xLgr>Avenida Sintetica</xLgr><nro>200</nro><xBairro>Centro</xBairro>"
            f"<cMun>{c_mun_fg}</cMun><xMun>Cidade Sintetica</xMun><UF>{uf}</UF>"
            "<CEP>01002000</CEP>"
            "</EndeDest>"
            f"<xMun>Cidade Sintetica</xMun><UF>{uf}</UF>"
            "</Destinatario>"
        )

    servico = (
        "<Servico>"
        f"<cMun>{c_mun_fg}</cMun>"
        "<xServ>Servicos de teste sintetico</xServ>"
        "<ListaServico>" + "".join(itens) + "</ListaServico>"
        "</Servico>"
    )

    total = (
        "<Total>"
        "<ISS>"
        f"<vBC>{v_bc_total}</vBC>"
        f"<vServicos>{v_servicos}</vServicos>"
        f"<vISS>{v_iss_total}</vISS>"
        "</ISS>"
        "<ISSRetido>"
        f"<vServico>{v_servicos}</vServico>"
        f"<vDescIncond>{v_desc_incond}</vDescIncond>"
        f"<vISSRetido>{v_iss_retido}</vISSRetido>"
        f"<vTotTrib>{v_tot_trib_total}</vTotTrib>"
        f"<vLiq>{v_liq}</vLiq>"
        "</ISSRetido>"
        "</Total>"
    )

    infnfe = "<InfNFe>" + ide + emitente + destinatario + servico + total + "</InfNFe>"

    if sem_infnsig:
        # Perfil sem assinatura: <InfNFe> direto, como filho de <NFSe>.
        infnsig = ""
        corpo = infnfe
    else:
        uri = "http://exemplo.invalido" if uri_invalida else f"#{chave}"
        if assinatura_vazia:
            assinatura = "<Signature></Signature>"
        elif assinatura_sem_reference:
            assinatura = (
                '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
                "<SignedInfo></SignedInfo>"
                "<SignatureValue>U0lOVEVUSUNBLVlNIRVM=</SignatureValue>"
                "</Signature>"
            )
        elif assinatura_sem_valor:
            assinatura = (
                '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
                f'<SignedInfo><Reference URI="{uri}"></Reference></SignedInfo>'
                "</Signature>"
            )
        elif assinatura_valor_vazio:
            assinatura = (
                '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
                f'<SignedInfo><Reference URI="{uri}"></Reference></SignedInfo>'
                "<SignatureValue></SignatureValue>"
                "</Signature>"
            )
        elif assinatura_incompleta:
            assinatura = f'<Signature><Reference URI="{uri}"></Reference></Signature>'
        else:
            assinatura = (
                f'<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
                f'<SignedInfo><Reference URI="{uri}"></Reference></SignedInfo>'
                "<SignatureValue>U0lOVEVUSUNBLVlNIRVM=</SignatureValue>"
                "</Signature>"
            )
        # <InfNFe> fica DENTRO de <InfNFeSig>, que e o layout ABRASF. Nao
        # emitimos uma segunda copia: dois <InfNFe> no mesmo documento e
        # estrutura invalida e o provedor rejeita.
        infnsig = f"<InfNFeSig>{assinatura}{infnfe}</InfNFeSig>"
        corpo = infnsig

    assinatura_extra = "<Signature></Signature>" if assinatura_fora else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFSe xmlns="http://www.abrasf.org.br/nfse.xsd">'
        f"{corpo}{assinatura_extra}"
        "</NFSe>"
    )


def documento_valido() -> str:
    """XML completo e coerente (sintetico)."""
    return documento_base()


def documento_com_lista_vazia() -> str:
    """<ListaServico> vazio mas com totais nao zerados."""
    return documento_base(itens=[], v_servicos="1000.00", v_iss_total="50.00")


def documento_quebrado(
    problema: str,
) -> str:
    """Cada ``problema`` quebra exatamente uma regra."""
    if problema == "ide_ausente":
        return documento_base(sem_ide=True)
    if problema == "cnpj_dv_invalido":
        return documento_base(cnpj=gerar_cnpj("112223330001")[:-1] + "9")
    if problema == "cpf_dv_invalido":
        return documento_base(cpf_dest=gerar_cpf("987654321")[:-1] + "8")
    if problema == "vservico_divergente":
        return documento_base(v_servicos="1500.00", v_liq="1450.00")
    if problema == "viss_divergente":
        return documento_base(v_iss_total="99.00")
    if problema == "lista_vazia_com_total":
        return documento_com_lista_vazia()
    if problema == "infnsig_ausente":
        return documento_base(sem_infnsig=True)
    if problema == "chave_invalida":
        return documento_base(chave="1" * 44)
    if problema == "dtemi_futuro":
        return documento_base(dt_emi="2099-01-15T10:30:00-03:00")
    if problema == "cnpj_com_cpf":
        return documento_base(cnpj=CPF_SINTETICO)
    if problema == "ordem_incorreta":
        xml = documento_base()
        # Troca nNF e cMunFG de lugar (cStat continua no inicio).
        return xml.replace(
            "<cMunFG>3550308</cMunFG><nNF>1</nNF>",
            "<nNF>1</nNF><cMunFG>3550308</cMunFG>",
        )
    if problema == "xml_malformado":
        return documento_base().replace("</Total>", "")
    if problema == "assinatura_uri":
        return documento_base(uri_invalida=True)
    if problema == "assinatura_incompleta":
        return documento_base(assinatura_incompleta=True)
    if problema == "cstat_invalido":
        return documento_base(c_stat="9")
    if problema == "nnf_zero":
        return documento_base(n_nf="0", chave=None)
    if problema == "uf_invalida":
        # Troca so a UF em <Emitente> e no endereco, mantendo a chave valida.
        return documento_base().replace("<UF>SP</UF>", "<UF>XX</UF>")
    if problema == "aliquota_divergente":
        return documento_base(
            itens=[_item_servico(v_serv="1000.00", v_bc="1000.00", v_iss="50.00", aliq="10.00")],
            v_iss_total="50.00",
        )
    if problema == "diferenca_um_centavo":
        # vServicos 1000.00 vs soma 1000.01 -> dentro da tolerancia, passa.
        return documento_base(
            itens=[_item_servico(v_serv="1000.01")],
            v_servicos="1000.00",
            v_liq="950.00",
        )
    if problema == "diferenca_dois_centavos":
        return documento_base(
            itens=[_item_servico(v_serv="1000.02")],
            v_servicos="1000.00",
            v_liq="950.00",
        )
    if problema == "raiz_duplicada":
        return documento_base() + documento_base()
    raise ValueError(f"problema desconhecido: {problema!r}")


def xml_cnpj_esperado() -> str:
    """CNPJ sintetico com digito verificador correto, so para documentacao."""
    return CNPJ_SINTETICO
