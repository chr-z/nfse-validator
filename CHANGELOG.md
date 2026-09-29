# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e
o versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-09-29

### Adicionado
- `validate(xml, *, strict=False, source="-", tolerancia=Decimal("0.01"))` como API
  pública, retornando um `Report` com `ok`, `errors`, `warnings`, `summary()` e
  `to_dict()`.
- Parser XML baseado em `xml.parsers.expat`, reportando linha e coluna reais
  para XML malformado, codificação inválida, documento vazio, ausência de raiz e
  múltiplas raízes.
- `brazil.py` com validação de dígitos verificadores de CPF e CNPJ, rejeição de
  sequências de dígitos repetidos, validação de UF, chave de acesso de 44 dígitos
  (dígito verificador mod-11 e posição de ano/UF), telefone, CEP, e-mail e
  código IBGE de município.
- Verificações estruturais por área (`Ide`, `Emitente`, `Destinatario`,
  `Servico`/`ListaServico`, `Total`), incluindo campos obrigatórios ausentes ou
  vazios e elementos fora de ordem dentro do pai.
- Reconciliação aritmética com `Decimal` (nunca `float`) para `vServicos`,
  `vProd`, `vBC`, `vISS`, `vLiq`/`vNF` e `vTotTrib`, com divergência implícita de
  alíquota por item e detecção de `ListaServico` vazia com total não zerado.
  Tolerância padrão de 0,01 para não reportar arredondamento como erro.
- Verificações de data e hora: ISO-8601 com fuso obrigatório, `dtEmi` no futuro
  como aviso (não erro), `nNF` positivo, divergência entre `cMun` e `cMunFG`.
- Checagem de presença da assinatura (`InfNFeSig`, `Signature`, `Reference`,
  `SignatureValue` e `URI` parseável) — sem verificação criptográfica.
- Modo `--strict` que promove avisos a erros.
- CLI `nfse-validator` com modo arquivo, `--json`, `--batch`, `--strict`,
  `--quiet`, `--fail-on`, `--version` e leitura por stdin (`-`).
  Códigos de saída: 0 limpo, 1 erro de validação, 2 erro de uso/IO.
- Validador no navegador em `web/index.html`: arquivo único, sem build, sem CDN,
  sem requisições externas, funcional offline e em celular, com acessibilidade
  por teclado.
- Fábrica de fixtures em `nfse_validator/fixtures.py` com 21 cenários de
  defeito, todos com dados sintéticos de dígitos verificadores válidos.
- 69 testes cobrindo cada código de erro, a fronteira de tolerância (0,01 passa e
  0,02 falha), os dígitos de CPF/CNPJ, a saída JSON e os códigos de saída da CLI.

### Limitações conhecidas
- Não verifica criptografia da assinatura (XMLDSig).
- Não valida o XSD específico do provedor municipal.
- Não emite NFS-e e não substitui homologação.
- Não é aconselhamento fiscal ou jurídico.
