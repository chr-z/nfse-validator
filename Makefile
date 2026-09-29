.PHONY: test demo lint clean

PY ?= python3

test:
	$(PY) -m unittest discover -s tests -v

demo:
	@$(PY) -c "import sys; sys.path.insert(0,'.'); from nfse_validator import fixtures; \
	import os; os.makedirs('/tmp/nfse-demo', exist_ok=True); \
	open('/tmp/nfse-demo/valida.xml','w').write(fixtures.documento_valido()); \
	open('/tmp/nfse-demo/cnpj-invalido.xml','w').write(fixtures.documento_quebrado('cnpj_dv_invalido')); \
	open('/tmp/nfse-demo/soma-divergente.xml','w').write(fixtures.documento_quebrado('vservico_divergente')); \
	open('/tmp/nfse-demo/xml-malformado.xml','w').write(fixtures.documento_quebrado('xml_malformado')); \
	print('fixtures em /tmp/nfse-demo')"
	@echo ""
	@echo "=== documento valido (esperado: exit 0) ==="
	@$(PY) -m nfse_validator /tmp/nfse-demo/valida.xml; echo "exit=$$?"
	@echo ""
	@echo "=== CNPJ com DV invalido (esperado: exit 1) ==="
	@$(PY) -m nfse_validator /tmp/nfse-demo/cnpj-invalido.xml; echo "exit=$$?"
	@echo ""
	@echo "=== vServicos divergente da soma dos itens (esperado: exit 1) ==="
	@$(PY) -m nfse_validator /tmp/nfse-demo/soma-divergente.xml; echo "exit=$$?"
	@echo ""
	@echo "=== XML malformado (esperado: exit 1) ==="
	@$(PY) -m nfse_validator /tmp/nfse-demo/xml-malformado.xml; echo "exit=$$?"
	@echo ""
	@echo "=== lote + JSON (esperado: exit 1, 3 com erro) ==="
	@$(PY) -m nfse_validator --batch /tmp/nfse-demo/ --json; echo "exit=$$?"

lint:
	@command -v ruff >/dev/null 2>&1 && ruff check nfse_validator tests || \
	 echo "ruff nao instalado; nada a fazer (zero dependencias de lint sao assumidas)"

clean:
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf build dist *.egg-info
