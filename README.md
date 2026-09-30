# NFS-e Validador

Validador **offline** de XML de NFS-e (Nota Fiscal de Serviço eletrônica) para
desenvolvedores PHP e Node que precisam testar a integração **antes** de pagar
um provedor de NFS-e.

## O problema

> "muitas dessas APIs só liberam acesso ao ambiente de homologação depois que você
> paga. Ou seja, só dá pra descobrir se funciona para o seu caso quando já
> estiver pagando."

As opções existentes são: uma API paga (que cobra justamente o teste), um curso
com DLL fechada, ou uma biblioteca open-source abandonada há anos.

Esta ferramenta responde à única pergunta que importa antes de pagar:
**meu XML está correto?**

Roda 100% offline: sem API key, sem servidor, sem telemetria, sem dependências.

## Para quem é

- Quem integra NFS-e municipal e não quer descobrir erro de schema em produção
- Quem quer conferir a conta dos totais (ISS, base, líquido) antes de homologar
- Quem usa PHP/Node e não quer baixar um XSD gigante nem subir container

## Instalação

Requer **Python 3.11+**. Zero dependências de runtime.

```bash
git clone https://github.com/SEU-USUARIO/nfse-validator
cd nfse-validator
pip install -e .
```

Sem instalar nada, funciona direto do repositório:

```bash
python3 -m nfse_validator minha_nota.xml
```

## Uso rápido

```bash
# um arquivo
nfse-validator nota.xml

# saída para CI
nfse-validator nota.xml --json

# vários arquivos (flags antes de --batch)
nfse-validator --strict --batch ./notas/

# glob
nfse-validator --batch "./notas/*.xml"

# pipe
cat nota.xml | nfse-validator -

# só o código de saída
nfse-validator -q nota.xml
```

### Saída real (XML com `vServicos` divergente da soma dos itens)

```
  ERRO SOMA_VSERVICO_DIVERGENTE: <vServicos> declarado (1500.00) difere da soma (1000.00). Diferenca de 500.00.
    em NFSe/InfNFeSig/InfNFe/Total/ISS/vServicos
    -> Soma dos valores dos itens de servico. A diferenca esta acima da tolerancia de 0.01 (centavo).

/tmp/demo-quebrado.xml: 1 erro encontrado.
```

## Referência da CLI

| Opção | Efeito |
|---|---|
| `<caminho>` | Arquivo XML a validar. `-` lê da entrada padrão. |
| `--json` | Saída em JSON, pronta para CI. |
| `--batch <alvo>` | Valida um diretório, um arquivo ou um glob. |
| `--strict` | Promove **todo** warning a error (muda o código de saída). |
| `-q`, `--quiet` | Não imprime nada; só o código de saída. |
| `--fail-on <error\|warning\|none>` | Quando falhar. Padrão: `error`. |
| `--no-color` | Desliga as cores (ligadas só em terminal). |
| `--version` | Mostra a versão. |

**Códigos de saída:** `0` limpo · `1` erro de validação · `2` erro de uso/IO

## Validador no navegador

Abra `web/index.html` direto no navegador. Sem build, sem CDN, **zero requisições
externas** (verificado: a página não carrega nenhum recurso de rede).

Implementa: well-formedness, dígitos verificadores de CPF/CNPJ, chave de acesso
(mod-11), campos obrigatórios, ordem dos elementos e a reconciliação aritmética
dos totais. Cola ou arrasta o arquivo, valida na hora, mostra o caminho do
elemento e como corrigir. Anexado a teclado e funciona no celular.

## API Python

```python
from nfse_validator import validate

relatorio = validate(xml_bytes, strict=False)

relatorio.ok          # bool
relatorio.errors      # list[Issue]
relatorio.warnings    # list[Issue]
relatorio.summary()   # str
relatorio.to_dict()   # dict (JSON-ready)
```

`Issue` traz `code`, `severity` (`error`/`warning`), `message`, `path`
(XPath-ish, ex. `NFSe/InfNFeSig/InfNFe/Ide`), `line`, `column` e `hint`.

Você também pode ajustar a tolerância:

```python
from decimal import Decimal
from nfse_validator import validate

relatorio = validate(xml, tolerancia=Decimal("0.05"))
```

## Regras aritméticas

Todas as comparações usam **`Decimal`**, nunca `float` (`0.1 + 0.2 != 0.3` em
binário). A tolerância é de **0,01** (um centavo), para nunca reportar artefato de
arredondamento como erro. *Exatamente 0,01 passa; 0,02 falha.*

| Regra | Código quando não confere |
|---|---|
| `vServicos` = soma de `vServ`/`vServico`/`vProd` dos itens | `SOMA_VSERVICO_DIVERGENTE` |
| `vBC` = soma de `vBC` dos itens | `SOMA_VBC_DIVERGENTE` |
| `vISS` = soma de `vISS` dos itens | `SOMA_VISS_DIVERGENTE` |
| `vTotTrib` = soma de `vTotTrib` dos itens | `SOMA_VTOTTRIB_DIVERGENTE` |
| `vLiq` = base − `vDescIncond` − `vDeducao` | `LIQUIDO_NAO_CONFERE` |
| `vISSRetido` = soma de `vISS` (quando ≠ 0) | `TOTAL_ISS_RECOLHIDO_DIVERGENTE` |
| `ListaServico` vazia ⇒ totais zerados | `TOTAL_SEM_ITENS`, `TOTAL_SEM_ITENS_NAO_ZERO` |
| Alíquota implícita (`vISS/vBC`) vs `aliq` declarada | `ITEM_SERVICO_ALIQUOTA_DIVERGENTE` (aviso) |

Quando a lista de serviços está vazia mas há totais consolidados, isso vira erro
explícito em vez de passar silenciosamente.

## Códigos de erro

São **91 códigos declarados** (veja `nfse_validator/codes.py`), dos quais **82 são
alcançáveis** pelo validador hoje. Os 9 restantes existem no catálogo mas nenhum fixture
conseguí-los emitir — estão declarados para parsers futuros e **não são cobertos por teste**:

`DESTINATARIO_ORDEM_INVALIDA`, `EMITENTE_ORDEM_INVALIDA`, `ENDERECO_CEP_INVALIDO`,
`ENDERECO_TEL_INVALIDO`, `ITEM_SERVICO_ORDEM_INVALIDA`, `LIQUIDO_NAO_CONFERE`,
`SOMA_VBC_DIVERGENTE`, `SOMA_VTOTTRIB_DIVERGENTE`, `TOTAL_ISS_RECOLHIDO_DIVERGENTE`.

Isso é auditado por `python3 tests/audit_codes.py`, que reporta separadamente
*emitted-without-test* (deve ser zero) de *declared-but-unreachable* (hoje: 9).

> **Nota sobre o script de auditoria:** ele tem um falso-negativo conhecido — ignora
> caminhos de código cobertos por teste unitário direto, mas não por fixture
> (`SOMA_VSERVICO_DIVERGENTE`, `SOMA_VISS_DIVERGENTE`, `XML_MALFORMADO` e outras 5
> aparecem como "inalcançáveis" para o script mas disparam normalmente). Os 9 acima
> foram confirmados **empiricamente**, rodando todos os 21 fixtures e coletando os
> códigos realmente emitidos.

### XML e envelope

| Código | Significado |
|---|---|
| `XML_VAZIO` | Documento sem conteúdo. |
| `XML_SEM_RAIZ` | Nenhum elemento raiz. |
| `XML_MALFORMADO` | XML não well-formed (tag não fechada, `&` solto…). |
| `XML_ENCODING_INVALIDO` | Declaração de codificação desconhecida. |
| `XML_RAIZES_MULTIPLAS` | Mais de um elemento raiz. |
| `ENVELOPE_RAIZ_INVALIDA` | Raiz não é `<NFSe>`. |
| `RAIZ_NAMESPACE_DESCONHECIDO` | Namespace fora do ABRASF/nacional (aviso). |
| `ENV_NFSE_AUSENTE` / `ENV_NFSE_VAZIA` | `<NFSe>` ausente ou vazio. |
| `ENV_INFNFE_AUSENTE` / `ENV_INFNFE_VAZIA` | `<InfNFe>` ausente ou vazio. |
| `ENV_INFNFE_DUPLICADO` | `<InfNFe>` dentro **e** fora de `<InfNFeSig>`. |

### `<Ide>`

| Código | Significado |
|---|---|
| `IDE_AUSENTE` / `IDE_VAZIO` | `<Ide>` ausente ou vazio. |
| `IDE_ORDEM_INVALIDA` | Elementos fora da ordem do schema. |
| `IDE_CSTAT_OBRIGATORIO` / `IDE_CSTAT_INVALIDO` | `cStat` ausente ou ≠ 1. |
| `IDE_NNF_OBRIGATORIO` / `IDE_NNF_NAO_NUMERICO` / `IDE_NNF_NAO_POSITIVO` | `nNF` inválido. |
| `IDE_DTEMI_OBRIGATORIO` / `IDE_DTEMI_INVALIDO` | Data/hora ausente ou malformada. |
| `IDE_DTEMI_SEM_FUSO` | Data/hora sem deslocamento (`-03:00`). |
| `IDE_DTEMI_FUTURO` / `IDE_DTEMI_ANTIGO` | Relógio adiantado / emissão antiga (avisos). |
| `IDE_CHAVE_ACESSO_OBRIGATORIA` / `IDE_CHAVE_ACESSO_INVALIDA` | Chave ausente ou com DV mod-11/UF/ mês inválidos. |
| `IDE_CHAVE_ACESSO_ANO_DIVERGENTE` | AAMM da chave ≠ ano de emissão (aviso). |
| `IDE_CMUNFG_OBRIGATORIO` / `IDE_CMUNFG_INVALIDO` | Código IBGE do município. |
| `IDE_CMUN_INVALIDO` / `IDE_CMUN_CMUNFG_DIVERGEM` | `cMun` inválido ou divergente (aviso). |
| `IDE_TPAMB_INVALIDO` | `tpAmb` fora de {1,2} (aviso). |

### Emitente, destinatário e endereço

| Código | Significado |
|---|---|
| `EMITENTE_AUSENTE` / `EMITENTE_VAZIO` | `<Emitente>` ausente ou vazio. |
| `EMITENTE_ORDEM_INVALIDA` | Ordem dos campos do emitente. |
| `EMITENTE_CNPJ_OBRIGATORIO` / `EMITENTE_CNPJ_INVALIDO` | CNPJ ausente ou com DV errado. |
| `EMITENTE_CNPJ_E_CPF` | CPF gravado no campo CNPJ, ou os dois juntos. |
| `EMITENTE_CPF_OBRIGATORIO` / `EMITENTE_CPF_INVALIDO` | CPF ausente ou com DV errado. |
| `EMITENTE_RAZAO_SOCIAL_OBRIGATORIA` / `EMITENTE_NOME_OBRIGATORIO` | Falta `<xNome>`. |
| `EMITENTE_UF_INVALIDA` | UF fora das 27. |
| `ENDERECO_CEP_INVALIDO` / `ENDERECO_TEL_INVALIDO` | Formato de CEP/telefone. |
| `DESTINATARIO_AUSENTE` / `DESTINATARIO_VAZIO` | Sem tomador (avisos). |
| `DESTINATARIO_ORDEM_INVALIDA` | Ordem dos campos do destinatário. |
| `DESTINATARIO_CPF_INVALIDO` / `DESTINATARIO_CNPJ_INVALIDO` | DV do documento. |
| `DESTINATARIO_CPF_E_CNPJ` / `DESTINATARIO_SEM_DOCUMENTO` | Campos conflitantes ou ausentes. |

### Serviço, totais e aritmética

| Código | Significado |
|---|---|
| `SERVICO_AUSENTE` / `SERVICO_VAZIO` | `<Servico>` ausente ou vazio. |
| `LISTA_SERVICO_AUSENTE` / `LISTA_SERVICO_VAZIA` | Lista de itens ausente ou vazia. |
| `ITEM_SERVICO_ORDEM_INVALIDA` | Ordem dos campos do item. |
| `ITEM_SERVICO_SEM_CODIGO` / `ITEM_SERVICO_CODIGO_INVALIDO` | Código da LC 116. |
| `ITEM_SERVICO_SEM_VALOR` / `ITEM_SERVICO_SEM_BC` | Falta `<vServ>` / `<vBC>`. |
| `ITEM_SERVICO_ALIQUOTA_INVALIDA` / `ITEM_SERVICO_ALIQUOTA_DIVERGENTE` | Alíquota fora de 0–100 ou incoerente com `vISS`. |
| `ITEM_SERVICO_ISS_RETIDO_INVALIDO` | `retISS` fora de {1,2}. |
| `LISTA_SERVICO_CODIGO_MUN_DIVERGENTE` | `cMun` do item ≠ do serviço (aviso). |
| `TOTAL_AUSENTE` / `TOTAL_VAZIO` / `TOTAL_ORDEM_INVALIDA` | Estrutura de `<Total>`. |
| `TOTAL_ISS_TRIBUTARIO_AUSENTE` / `TOTAL_ISS_RECOLHIDO_AUSENTE` | `<ISS>` / `<ISSRetido>` faltando. |
| `TOTAL_DECIMAL_INVALIDO` | Valor monetário não numérico. |
| `VALOR_NAO_NUMERICO` / `VALOR_NEGATIVO` | Valor de item inválido. |
| `SOMA_*_DIVERGENTE`, `LIQUIDO_NAO_CONFERE`, `TOTAL_ISS_RECOLHIDO_DIVERGENTE` | Reconciliação (ver tabela acima). |
| `TOTAL_SEM_ITENS` / `TOTAL_SEM_ITENS_NAO_ZERO` | Totais sem itens correspondentes. |

### Assinatura (estrutura, **não** criptografia)

| Código | Significado |
|---|---|
| `INFNFESIG_AUSENTE` / `INFNFESIG_VAZIA` | Bloco de assinatura ausente ou vazio. |
| `ASSINATURA_AUSENTE` / `ASSINATURA_VAZIA` | `<Signature>` ausente ou vazio. |
| `ASSINATURA_REFERENCE_AUSENTE` / `ASSINATURA_REFERENCE_VAZIA` | `<Reference>` ausente ou vazio. |
| `ASSINATURA_URI_INVALIDA` | `URI` de `<Reference>` não começa com `#`. |
| `ASSINATURA_SIGNATUREVALUE_AUSENTE` / `ASSINATURA_SIGNATUREVALUE_VAZIA` | Assinatura ausente/vazia. |
| `ASSINATURA_FORA_DE_INFNFE` | `<Signature>` fora de `<InfNFeSig>`. |

## Limitações — leia antes de confiar

- **Não verifica criptografia da assinatura.** Checamos apenas a *presença e a
  estrutura* do XMLDSig. Validação criptográfica real (XMLDSig/RSA + cadeia de
  certificado) exige uma biblioteca de assinatura — use a do seu provedor/SDK.
- **Não valida o XSD do seu provedor municipal.** Cada prefeitura tem seu
  schema. Isto checa o layout ABRASF/nacional comum, não o schema da sua cidade,
  e a ordem dos elementos é uma heurística desse layout.
- **Não emite NFS-e** e não substitui a homologação do provedor.
- **Não é aconselhamento fiscal ou jurídico.** Nada aqui substitui um contador.
- Não há telemetria, analytics, cookies ou qualquer chamada de rede.

Todos os dados dos fixtures são **sintéticos**, com dígitos verificadores
matematicamente válidos. Nenhuma empresa, pessoa ou endereço real está
representado.

## Desenvolvimento

```bash
make test        # roda a suite (unittest, sem precisar de pytest)
make lint        # usa ruff/flake8 se estiverem instalados; senao compila
make demo        # gera XML sintetico e mostra a CLI funcionando
make fixtures    # gera os XMLs de exemplo em fixtures/
make batch       # valida tudo que estiver em fixtures/
```

A suite usa `unittest.TestCase`, então roda com `unittest` **e** é coletada pelo
`pytest` sem alterações.

## Como contribuir

1. Todo código de erro novo vem com teste (a regra vale para os dois).
2. Dinheiro sempre com `Decimal`. Nunca `float`.
3. Sem dependências novas no runtime — stdlib apenas.
4. Mensagens e dicas em português; todo erro traz um `hint` de como corrigir.
5. Não copie XSD oficial da ABRASF: o projeto é baseado em regras.

## Licença

MIT. Ver [LICENSE](LICENSE).
