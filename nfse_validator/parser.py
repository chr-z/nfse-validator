"""Parser XML baseado em :mod:`xml.parsers.expat`.

Por que expat e nao ``xml.etree``? Porque o ElementTree nao expoe posicao
(linha/coluna) dos elementos, e posicao e justamente o que torna um relatorio
de XML malformado util para quem vai corrigir o arquivo.

A arvore retornada (:class:`Node`) e minimalista de proposito: tag local,
prefixo, atributos, texto, filhos, pai e posicao. Nao tentamos ser um DOM
completo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple
from xml.parsers import expat

from .report import ERROR, Issue

# Namespaces aceitos no elemento raiz. O padrao ABRASF e o padrao nacional.
NAMESPACES_ACEITOS = (
    "http://www.abrasf.org.br/nfse.xsd",
    "http://www.portalfiscal.inf.br/nfe",
)

# Erros do expat que deserves um codigo proprio.
_ERRO_ENCODING = {
    expat.errors.codes[expat.errors.XML_ERROR_UNKNOWN_ENCODING],
    expat.errors.codes[expat.errors.XML_ERROR_INCORRECT_ENCODING],
}
_ERRO_RAIZES = {
    expat.errors.codes[expat.errors.XML_ERROR_JUNK_AFTER_DOC_ELEMENT],
    expat.errors.codes[expat.errors.XML_ERROR_SYNTAX],
    expat.errors.codes[expat.errors.XML_ERROR_INVALID_TOKEN],
}


class XmlError(Exception):
    """Erro de parse carrying o :class:`Issue` ja pronto para o relatorio."""

    def __init__(self, issue: Issue):
        super().__init__(issue.message)
        self.issue = issue


@dataclass
class Node:
    """Um elemento XML com posicao e caminho ja resolvidos."""

    tag: str
    prefix: str = ""
    attrs: Dict[str, str] = field(default_factory=dict)
    text: str = ""
    line: Optional[int] = None
    column: Optional[int] = None
    children: List["Node"] = field(default_factory=list)
    parent: Optional["Node"] = None
    ns_declarations: Dict[str, str] = field(default_factory=dict)
    _path: str = ""

    # -- caminho --------------------------------------------------------
    def path(self) -> str:
        if not self._path:
            partes: List[str] = []
            n: Optional[Node] = self
            while n is not None:
                pfx = f"{n.prefix}:" if n.prefix else ""
                partes.append(f"{pfx}{n.tag}")
                n = n.parent
            self._path = "/".join(reversed(partes))
        return self._path

    # -- busca ----------------------------------------------------------
    def find(self, tag: str) -> Optional["Node"]:
        for c in self.children:
            if c.tag == tag:
                return c
        return None

    def findall(self, tag: str) -> List["Node"]:
        return [c for c in self.children if c.tag == tag]

    def iter(self) -> Iterator["Node"]:
        yield self
        for c in self.children:
            yield from c.iter()

    def value(self, tag: str, default: str = "") -> str:
        """Texto (limpo) do primeiro filho direto ``tag``."""
        n = self.find(tag)
        if n is None:
            return default
        return n.text.strip()

    def is_empty(self, tag: str) -> bool:
        """True quando o filho ``tag`` nao existe ou tem texto vazio."""
        n = self.find(tag)
        return n is None or not n.text.strip()

    def child_path(self, tag: str) -> str:
        pfx = f"{self.prefix}:" if self.prefix else ""
        return f"{self.path()}/{pfx}{tag}"

    def __repr__(self) -> str:  # pragma: no cover - debug
        return f"<Node {self.path()!r} linea={self.line}>"


class _Builder:
    def __init__(self) -> None:
        self.root: Optional[Node] = None
        self.stack: List[Node] = []
        self.ns_stack: List[Dict[str, str]] = [{}]

    def start(self, qname: str, attrs: Dict[str, str]) -> None:
        # Durante o StartElementHandler, CurrentLineNumber/ColumnNumber apontam
        # para o inicio da tag -- e exatamente a posicao que queremos reportar.
        line = self.parser.CurrentLineNumber or 0
        column = (self.parser.CurrentColumnNumber or 0) + 1
        prefix, local = _split_qname(qname)
        # Herda as declaracoes de namespace dos ancestrais.
        parent_ns = self.ns_stack[-1]
        own = dict(parent_ns)
        for key, value in attrs.items():
            if key == "xmlns":
                own[""] = value
            elif key.startswith("xmlns:"):
                own[key[6:]] = value
        node = Node(
            tag=local,
            prefix=prefix,
            attrs={k: v for k, v in attrs.items() if not k.startswith("xmlns")},
            ns_declarations=own,
            line=line or None,
            column=column or None,
        )
        node._path = (
            f"{self.stack[-1]._path}/{prefix + ':' if prefix else ''}{local}"
            if self.stack
            else f"{prefix + ':' if prefix else ''}{local}"
        )
        if self.stack:
            node.parent = self.stack[-1]
            self.stack[-1].children.append(node)
        elif self.root is None:
            self.root = node
        self.stack.append(node)
        self.ns_stack.append(own)

    def end(self, qname: str) -> None:
        if self.stack:
            self.stack.pop()
        if self.ns_stack:
            self.ns_stack.pop()

    def chardata(self, data: str) -> None:
        if self.stack:
            self.stack[-1].text += data

    def position(self) -> Tuple[int, int]:
        line = getattr(self.parser, "CurrentLineNumber", 0) or 0
        col = getattr(self.parser, "CurrentColumnNumber", 0) or 0
        return line, col + 1  # expat reporta coluna 0-based


def _split_qname(qname: str) -> Tuple[str, str]:
    if ":" in qname:
        prefix, local = qname.split(":", 1)
        return prefix, local
    return "", qname


def parse(
    data: bytes | str,
    *,
    source: str = "-",
) -> Node:
    """Faz o parse de ``data`` e devolve o elemento raiz.

    Levanta :class:`XmlError` com um :class:`Issue` pronto quando o documento
    nao e well-formed.
    """
    if isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = bytes(data)

    if not payload.strip():
        raise XmlError(
            Issue(
                code="XML_VAZIO",
                severity=ERROR,
                message="Documento XML vazio.",
                path="",
                line=None,
                column=None,
                hint="O arquivo nao contem nenhum conteudo. Verifique se o processo de geracao gravou o XML em disco.",
            )
        )

    builder = _Builder()
    parser = expat.ParserCreate()
    parser.namespace_prefixes = True
    builder.parser = parser
    parser.StartElementHandler = builder.start
    parser.EndElementHandler = builder.end
    parser.CharacterDataHandler = builder.chardata

    try:
        parser.Parse(payload, True)
    except expat.ExpatError as exc:
        raise XmlError(_expat_to_issue(exc, source)) from exc

    root = builder.root
    if root is None:
        raise XmlError(
            Issue(
                code="XML_SEM_RAIZ",
                severity=ERROR,
                message="Nenhum elemento raiz encontrado no documento.",
                path="",
                line=1,
                column=1,
                hint="Todo XML precisa de exatamente um elemento raiz. Confira se o conteudo comecou a ser gravado.",
            )
        )

    return root


def _expat_to_issue(exc: expat.ExpatError, source: str) -> Issue:
    code_number = exc.code
    line, col = exc.lineno, exc.offset + 1
    msg = expat.ErrorString(code_number)

    if code_number in _ERRO_ENCODING:
        code = "XML_ENCODING_INVALIDO"
        message = f"Declaracao de codificacao invalida: {msg}."
        hint = (
            "Use uma codificacao suportada pelo XML (UTF-8 e o recomendado). "
            "Em PHP, grave o arquivo com mb_convert_encoding($xml, 'UTF-8', 'UTF-8')."
        )
    elif code_number in _ERRO_RAIZES and "junk after document element" in msg:
        code = "XML_RAIZES_MULTIPLAS"
        message = "Ha mais de um elemento raiz no documento."
        hint = (
            "Um documento XML so pode ter uma raiz. Voce provavelmente concatenou "
            "duas NFS-e; gere um arquivo por nota."
        )
    else:
        code = "XML_MALFORMADO"
        message = f"XML malformado: {msg}."
        hint = _hint_malformado(msg)

    return Issue(
        code=code,
        severity=ERROR,
        message=message,
        path="",
        line=line,
        column=col,
        hint=hint,
    )


def _hint_malformado(msg: str) -> str:
    if "no element found" in msg:
        return (
            "O documento nao tem elemento raiz. Verifique se o arquivo foi "
            "cortado no meio da escrita ou se a string esta vazia."
        )
    if "unclosed token" in msg or "mismatched tag" in msg:
        return "Ha uma tag aberta que nao foi fechada. Confira o aninhamento de <InfNFe>, <Ide> e <Total>."
    if "not well-formed" in msg or "syntax error" in msg:
        return "Algum caractere especial (ex.: & ou <) aparece no texto sem escape. Use &amp; e &lt;."
    if "mismatched" in msg:
        return "Uma tag de fechamento nao corresponde a tag de abertura."
    return "Revise o XML gerado: Tags balanceadas, atributos com aspas, sem & solto no texto."
