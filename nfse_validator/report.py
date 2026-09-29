"""Estruturas de relatorio: :class:`Issue` e :class:`Report`.

O modulo nao importa nada fora da biblioteca padrao e nao faz nenhuma
chamada de rede. Tudo aqui e puro e deterministico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

ERROR = "error"
WARNING = "warning"

SEVERITIES = (ERROR, WARNING)


@dataclass(frozen=True)
class Issue:
    """Um problema encontrado no XML.

    ``code``    identificador estavel, seguro para uso em CI (ex.: ``IDE_AUSENTE``)
    ``severity`` ``"error"`` ou ``"warning"``
    ``message``  descricao em portugues
    ``path``     caminho XPath-ish do elemento (``NFSe/InfNFe/Ide``)
    ``line``     linha 1-based ou ``None``
    ``column``   coluna 1-based ou ``None``
    ``hint``     como corrigir, em portugues
    """

    code: str
    severity: str
    message: str
    path: str = ""
    line: Optional[int] = None
    column: Optional[int] = None
    hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "hint": self.hint,
        }

    def location(self) -> str:
        """``arquivo:linha:coluna`` quando a posicao e conhecida."""
        if self.line is None and self.column is None:
            return self.path or "-"
        return f"{self.path or '-'} (linha {self.line}, coluna {self.column})"


def _promote(issue: Issue) -> Issue:
    return Issue(
        code=issue.code,
        severity=ERROR,
        message=issue.message,
        path=issue.path,
        line=issue.line,
        column=issue.column,
        hint=issue.hint,
    )


@dataclass
class Report:
    """Resultado de uma validacao."""

    issues: List[Issue] = field(default_factory=list)
    strict: bool = False
    source: str = "-"

    def __post_init__(self) -> None:
        self.issues = sorted(
            self.issues,
            key=lambda i: (
                0 if i.severity == ERROR else 1,
                i.path or "",
                i.line if i.line is not None else 0,
                i.column if i.column is not None else 0,
                i.code,
            ),
        )

    # -- acesso ---------------------------------------------------------
    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def codes(self) -> List[str]:
        return [i.code for i in self.issues]

    def has_code(self, code: str) -> bool:
        return any(i.code == code for i in self.issues)

    # -- transformacao --------------------------------------------------
    def promoted(self) -> "Report":
        """Devolve uma copia com todo warning promovido a error (modo estrito)."""
        if not self.strict:
            return Report(
                issues=[_promote(i) for i in self.issues],
                strict=True,
                source=self.source,
            )
        return self

    def extend(self, issues: Iterable[Issue]) -> None:
        self.issues = list(self.issues) + list(issues)
        self.__post_init__()

    # -- serializacao ---------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "strict": self.strict,
            "source": self.source,
            "counts": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
            },
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary(),
        }

    def summary(self) -> str:
        n_err, n_warn = len(self.errors), len(self.warnings)
        if n_err == 0 and n_warn == 0:
            return f"{self.source}: OK - nenhum problema encontrado."
        partes = []
        if n_err:
            partes.append(f"{n_err} erro{'s' if n_err != 1 else ''}")
        if n_warn:
            partes.append(f"{n_warn} aviso{'s' if n_warn != 1 else ''}")
        return f"{self.source}: {' e '.join(partes)} encontrado{'s' if (n_err + n_warn) != 1 else ''}."


def make_report(issues: Iterable[Issue], *, strict: bool = False, source: str = "-") -> Report:
    """Cria um :class:`Report`, aplicando a regra do modo estrito.

    Em ``strict=True`` todo warning vira error (e ``.warnings`` fica vazio),
    que e exatamente o que o parametro ``--strict`` da CLI precisa.
    """
    itens: List[Issue] = list(issues)
    if strict:
        itens = [_promote(i) for i in itens]
    return Report(issues=itens, strict=strict, source=source)
