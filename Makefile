# NFS-e Validador - tarefas de desenvolvimento.
# Todos os alvos rodam sem rede. O projeto e stdlib-only.

PYTHON ?= python3
PKG    := nfse_validator
TESTS  := tests

.DEFAULT_GOAL := help
.PHONY: help test lint demo fixtures batch clean install-web-check

help:  ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

test:  ## Roda a suite de testes (unittest, nao precisa de pytest)
	@echo "== Suite de testes =="
	$(PYTHON) -m unittest discover -s $(TESTS) -t . -v

test-pytest:  ## Roda os testes com pytest, se estiver instalado
	@if $(PYTHON) -c "import pytest" 2>/dev/null; then \
		$(PYTHON) -m pytest -q; \
	else \
		echo "pytest nao esta instalado; use 'make test' (unittest)."; \
		exit 1; \
	fi

lint:  ## Roda o linter se algum estiver instalado (nao instala nada)
	@if $(PYTHON) -c "import ruff" 2>/dev/null; then \
		echo "== ruff =="; $(PYTHON) -m ruff check $(PKG) $(TESTS); \
	elif $(PYTHON) -c "import flake8" 2>/dev/null; then \
		echo "== flake8 =="; $(PYTHON) -m flake8 $(PKG) $(TESTS); \
	else \
		echo "Nenhum linter instalado (ruff/flake8). Pulando."; \
		echo "Verificando compilacao com o proprio interpretador..."; \
		$(PYTHON) -m compileall -q $(PKG) $(TESTS) && echo "compilacao OK"; \
	fi

demo:  ## Gera um XML sintetico e valida pela CLI
	@echo "== Documento valido =="
	@$(PYTHON) -c "from $(PKG) import fixtures as f; open('/tmp/demo-valido.xml','w').write(f.documento_valido())"
	@$(PYTHON) -m $(PKG) /tmp/demo-valido.xml; echo "exit=$$?"
	@echo
	@echo "== Documento com vServicos divergente da soma dos itens =="
	@$(PYTHON) -c "from $(PKG) import fixtures as f; open('/tmp/demo-quebrado.xml','w').write(f.documento_quebrado('vservico_divergente'))"
	@$(PYTHON) -m $(PKG) /tmp/demo-quebrado.xml; echo "exit=$$?"
	@echo
	@echo "== Saida JSON =="
	@$(PYTHON) -m $(PKG) --json /tmp/demo-quebrado.xml; true
	@echo
	@echo "== Modo estrito (promove aviso a erro) =="
	@$(PYTHON) -c "from $(PKG) import fixtures as f; open('/tmp/demo-aviso.xml','w').write(f.documento_quebrado('aliquota_divergente'))"
	@$(PYTHON) -m $(PKG) /tmp/demo-aviso.xml; echo "exit=$$? (0: aviso nao falha)"
	@$(PYTHON) -m $(PKG) --strict /tmp/demo-aviso.xml; echo "exit=$$? (1: com --strict falha)"
	@echo
	@echo "(os exit=1 acima sao o comportamento esperado do validador)"
	@true

fixtures:  ## Gera todos os XMLs sinteticos de exemplo em fixtures/
	@mkdir -p fixtures
	@$(PYTHON) -c "\
from $(PKG) import fixtures as f; \
import pathlib; \
d = pathlib.Path('fixtures'); \
(d / 'valido.xml').write_text(f.documento_valido(), encoding='utf-8'); \
probs = ['ide_ausente','cnpj_dv_invalido','cpf_dv_invalido','vservico_divergente','viss_divergente','lista_vazia_com_total','infnsig_ausente','chave_invalida','dtemi_futuro','cnpj_com_cpf','ordem_incorreta','xml_malformado']; \
[d.joinpath(p + '.xml').write_text(f.documento_quebrado(p), encoding='utf-8') for p in probs]; \
print('gerados', len(probs) + 1, 'arquivos sinteticos em', d)"
	@echo "Todos os dados sao SINTETICOS (digitos verificadores calculados, nenhuma empresa real)."

batch: fixtures  ## Valida todos os XMLs de fixtures/ de uma vez
	@$(PYTHON) -m $(PKG) --batch fixtures; echo "exit=$$?"; true

clean:  ## Remove artefatos temporarios
	rm -rf fixtures /tmp/demo-*.xml
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
