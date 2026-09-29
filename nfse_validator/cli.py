"""Interface de linha de comando do NFS-e Validador.

Saidas: 0 = limpo, 1 = erros de validacao, 2 = erro de uso ou de IO.
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import sys
from typing import List, Optional, Sequence, TextIO

from . import __version__, validate
from .report import ERROR, WARNING, Report

EXIT_OK = 0
EXIT_INVALIDO = 1
EXIT_USO = 2

# Cores usadas apenas quando a saida e um terminal.
CORES = {
    ERROR: "\033[31m",
    WARNING: "\033[33m",
    "ok": "\033[32m",
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}


def _cor(texto: str, chave: str, usar_cor: bool) -> str:
    if not usar_cor:
        return texto
    return f"{CORES[chave]}{texto}{CORES['reset']}"


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nfse-validator",
        description=(
            "Validador offline de XML de NFS-e (Nota Fiscal de Servico eletronica). "
            "Nao faz nenhuma chamada de rede."
        ),
        epilog="Use '-' como caminho para ler da entrada padrao (stdin).",
    )
    p.add_argument("caminho", nargs="?", help="arquivo XML a validar, ou '-' para stdin")
    p.add_argument("--json", action="store_true", help="saida em JSON")
    # --batch recebe um valor: flags precisam vir antes dele
    # ("--batch --json x" faz o argparse tratar --json como valor de --batch,
    # e ele recusa com erro de uso, que e o comportamento correto).
    p.add_argument(
        "--batch",
        metavar="ALVO",
        help="valida varios arquivos (diretorio, arquivo ou glob)",
    )
    p.add_argument("--strict", action="store_true", help="promove todo warning a error")
    p.add_argument("-q", "--quiet", action="store_true", help="imprime apenas o codigo de saida")
    p.add_argument(
        "--fail-on",
        choices=("error", "warning", "none"),
        default="error",
        help="quando falhar: em error (padrao), warning ou none",
    )
    p.add_argument("--no-color", action="store_true", help="desliga as cores no terminal")
    p.add_argument("--version", action="version", version=f"nfse-validator {__version__}")
    return p


def _ler(caminho: str, stdin: TextIO) -> bytes:
    if caminho == "-":
        return stdin.buffer.read() if hasattr(stdin, "buffer") else stdin.read().encode("utf-8")
    with open(caminho, "rb") as fh:
        return fh.read()


def _expandir(alvo: str) -> List[str]:
    """Aceita diretorio, arquivo ou glob."""
    if os.path.isdir(alvo):
        encontrados = []
        for raiz, _dirs, arquivos in os.walk(alvo):
            for nome in sorted(arquivos):
                if nome.lower().endswith(".xml"):
                    encontrados.append(os.path.join(raiz, nome))
        return sorted(encontrados)
    if os.path.isfile(alvo):
        return [alvo]
    return sorted(globmod.glob(alvo))


def _codigo_saida(reportes: List[Report], fail_on: str) -> int:
    if fail_on == "none":
        return EXIT_OK
    tem_erro = any(not r.ok for r in reportes)
    tem_aviso = any(r.warnings for r in reportes)
    if fail_on == "error":
        return EXIT_INVALIDO if tem_erro else EXIT_OK
    # fail_on == "warning"
    return EXIT_INVALIDO if (tem_erro or tem_aviso) else EXIT_OK


def _formatar_issue(issue, usar_cor: bool) -> str:
    rotulo = "ERRO" if issue.severity == ERROR else "AVISO"
    linha = f"  {_cor(rotulo, issue.severity, usar_cor)} "
    linha += f"{_cor(issue.code, 'bold', usar_cor)}: {issue.message}"
    loc = issue.location()
    if loc:
        linha += f"\n    {_cor('em', 'dim', usar_cor)} {loc}"
    if issue.hint:
        linha += f"\n    {_cor('->', 'dim', usar_cor)} {issue.hint}"
    return linha


def _imprimir_relatorio(report: Report, usar_cor: bool) -> None:
    if report.ok and not report.warnings:
        print(_cor("OK", "ok", usar_cor), "- nenhum problema encontrado:", report.source)
        return
    for issue in report.issues:
        print(_formatar_issue(issue, usar_cor))
    print(f"\n{report.summary()}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    usar_cor = (
        not args.no_color
        and not args.json
        and not args.quiet
        and sys.stdout.isatty()
    )

    if args.batch and args.caminho:
        print("erro: use --batch OU um caminho, nao os dois", file=sys.stderr)
        return EXIT_USO
    if not args.batch and not args.caminho:
        parser.print_usage(sys.stderr)
        print("erro: informe um caminho ou use --batch", file=sys.stderr)
        return EXIT_USO

    # --- modo batch -----------------------------------------------------
    if args.batch:
        arquivos = _expandir(args.batch)
        if not arquivos:
            print(f"erro: nenhum XML encontrado em {args.batch!r}", file=sys.stderr)
            return EXIT_USO
        reportes: List[Report] = []
        falhas_io = False
        for arquivo in arquivos:
            try:
                dados = _ler(arquivo, sys.stdin)
            except OSError as exc:
                falhas_io = True
                print(f"erro de IO: {arquivo}: {exc}", file=sys.stderr)
                continue
            reportes.append(validate(dados, strict=args.strict, source=arquivo))

        if args.json:
            print(json.dumps([r.to_dict() for r in reportes], ensure_ascii=False, indent=2))
        elif not args.quiet:
            for report in reportes:
                marcacao = _cor("OK  ", "ok", usar_cor) if report.ok else _cor("FALHA", ERROR, usar_cor)
                n_e, n_a = len(report.errors), len(report.warnings)
                print(f"{marcacao} {report.source}  ({n_e} erro(s), {n_a} aviso(s))")
            total_e = sum(len(r.errors) for r in reportes)
            total_a = sum(len(r.warnings) for r in reportes)
            print(f"\n{len(reportes)} arquivo(s): {total_e} erro(s), {total_a} aviso(s).")

        codigo = _codigo_saida(reportes, args.fail_on)
        if falhas_io:
            return EXIT_USO
        return codigo

    # --- arquivo unico / stdin ------------------------------------------
    caminho = args.caminho
    try:
        dados = _ler(caminho, sys.stdin)
    except OSError as exc:
        print(f"erro de IO: {caminho}: {exc}", file=sys.stderr)
        return EXIT_USO

    report = validate(dados, strict=args.strict, source=caminho)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    elif not args.quiet:
        _imprimir_relatorio(report, usar_cor)

    return _codigo_saida([report], args.fail_on)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
