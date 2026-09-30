# Changelog

Todas as mudancas relevantes deste projeto sao registradas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e
o projeto usa [Versionamento Semantico](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-09-29

### Adicionado

- **Biblioteca Python** (`nfse_validator`) sem dependencias de runtime, apenas
  stdlib. API publica: `validate(xml, *, strict=False) -> Report`.
- **Parser XML** baseado em `xml.parsers.expat`, com linha e coluna precisas
  para relatar XML malformado. Detecta documento vazio, ausencia de raiz,
  encoding desconhecido e multiplas raizes.
- **Validacoes de documentos brasileiros** em `brazil.py`: digitos verificadores
  de CPF e CNPJ (com rejeicao de sequencias repetidas), chave de acesso de 44
  digitos com DV mod-11 e conference de UF/ano/mes, UF, CEP, telefone, e-mail e
  codigo IBGE de municipio.
- **Verificacoes estruturais** por area (`checks/`): envelope, `<Ide>`,
  `<Emitente>`, `<Destinatario>`, `<Servico>`, `<Total>` e assinatura. Cada
  campo obrigatorio ausente ou vazio gera um codigo especifico, e elementos fora
  da ordem do schema sao detectados.
- **Reconciliacao aritmetica** com `Decimal`: `vServicos`, `vBC`, `vISS`,
  `vTotTrib`, `vLiq` (honrando `vDescIncond` e `vDeducao`) e `vISSRetido`.
  Tolerancia de 0,01 para nao acusar arredondamento como erro. Lista de
  servicos vazia com totais nao zerados vira erro explicito.
- **Sanidade de aliquota**: compara a aliquota implicita (`vISS / vBC`) com a
  `aliq` declarada, dentro de tolerancia configuravel.
- **Verificacao de datas**: `dhEmi`/`dEmi` em ISO-8601 com fuso; emissao no
  futuro gera aviso (nao erro), com tolerancia de relogio.
- **Checagem estrutural de assinatura**: presenca de `InfNFeSig`, `Signature`,
  `Reference` (com `URI` interna) e `SignatureValue`. **Sem** verificacao
  criptografica, por decisao de escopo.
- **CLI** `nfse-validator`: arquivo unico, `--batch` (diretorio/glob), `--json`,
  `--strict`, `--quiet`, `--fail-on`, `--no-color`, `--version` e leitura por
  stdin com `-`. Codigos de saida 0/1/2.
- **Validador de navegador** (`web/index.html`): arquivo unico, sem build, sem
  CDN e sem nenhuma requisicao externa. Well-formedness, CPF/CNPJ, chave de
  acesso, campos obrigatorios, ordem dos elementos e reconciliacao aritmetica.
- **Fabrica de fixtures sinteticas** com digitos verificadores validos e 21
  quebras deliberadas, usadas por testes e pelo alvo `make demo`.
- **Suite de 169 testes** cobrindo todos os 91 codigos de issue declarados.
- `Makefile` com `test`, `lint`, `demo`, `fixtures` e `batch`, todos sem rede.

### Notas

- O XSD oficial da ABRASF **nao** e distribuido nem copiado: a validacao e
  baseada em regras, e o layout exato varia por municipio. A ordem dos
  elementos verificada e a do perfil nacional e esta declarada como heuristica
  no README.
- A verificacao criptografica da assinatura (XMLDSig/RSA) esta explicitamente
  fora de escopo; o README aponta para o uso de uma biblioteca de assinatura real.
