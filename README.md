# NFS-e Validador

Validador **offline** de XML de NFS-e (Nota Fiscal de Serviço eletrônica) para
desenvolvedores PHP e Node que precisam testar a integração **antes** de pagar
um provedor de NFS-e.

## O problema

>"muitas dessas APIs só liberam acesso ao ambiente de homologação depois que você
> paga. Ou seja, só dá pra descobrir se funciona para o seu caso quando já
> estiver pagando, e muitas vezes com valores bem altos."

As opções existentes são: uma API paga (que cobra justamente o teste), um
curso + DLL fechada, ou uma biblioteca open-source abandonada há anos.

Esta ferramenta responde à única pergunta que importa antes de pagar:
**meu XML está correto?**

Roda 100% offline, sem API key, sem servidor, sem telemetria, sem dependências.

## Para quem é

- Quem integra NFS-e municipal e não quer descobrir erro de schema em produção
- Quem quer validar o cálculo dos totais (ISS, base, líquido) antes de homologar
- Quem usa PHP/Node e não quer instalar schema XSD gigante nem subir container

## Instalação

Requer **Python 3.8+**. Zero dependências externas.

```bash
git clone https://github.com/SEU-USUARIO/nfse-validator
cd nfse-validator
pip install -e .
```

Sem instalar nada, funciona direto:

```bash
python3 -m nfse_validator minha_nota.xml
```

## Uso rápido

```bash
# um arquivo
nfse-validator nota.xml

# saída para CI
nfse-validator nota.xml --json

# vários arquivos
nfse-validator --batch "./notas/*.xml"

# pipe
cat nota.xml | nfse-validator -

# valida tudo e falha em qualquer aviso
nfse-validator --batch ./notas/ --strict
```

Saída real de um XML com CNPJ inválido:

```
  ERRO EMITENTE_CNPJ_INVALIDO: CNPJ do emitente 11222333000189 tem digito verificador incorreto.
    em NFSe/InfNFeSig/InfNFe/Emitente/CNPJ (linha 1, coluna 652)
    -> Recalcule os dois digitos verificadores do CNPJ. Em PHP, use a funcao de
       validacao do seu SDK ou faca o calculo mod-11.

nota.xml: 1 erro encontrado.
```

## Validador no navegador

Abra `web/index.html` direto no navegador. Sem build, sem CDN, sem rede —
funciona offline e no celular. Valida well-formedness, dígitos de CPF/CNPJ,
campos obrigatórios e a conciliação aritmética dos totais.

## API

```python
from nfse_validator import validate

relatorio = validate(xml_bytes, strict=False)

relatorio.ok          # bool
relatorio.errors      # list[Issue]
relatorio.warnings    # list[Issue]
relatorio.summary()   # str
relatorio.to_dict()   # dict (JSON-ready)
```

`Issue` traz `code`, `severity`, `message`, `path`, `line`, `column`, `hint`.

## Regras aritméticas

Todas as comparações usam `Decimal` — nunca `float`. Tolerância de **0,01**
(um centavo), para não reportar artefato de arredondamento como erro.

- `vServicos` / `vProd` = soma dos itens
- `vBC` = soma de `vBC` dos itens
- `vISS` = soma de `vISS` dos itens
- `vLiq` = `vServicos` − `vDescIncond` (honrando `vDeducao`)
- `vTotTrib` = soma de `vTotTrib` dos itens
- Alíquota implícita (`vISS / vServico`) comparada com a `Aliquota` declarada
- `ListaServico` vazia exige totais zerados — divergência vira erro, não silêncio

## Códigos de erro

96 códigos estáveis. Principais grupos:

| Grupo | Exemplos |
|---|---|
| XML | `XML_MALFORMADO`, `XML_VAZIO`, `XML_RAIZES_MULTIPLAS`, `XML_ENCODING_INVALIDO` |
| Documentos BR | `EMITENTE_CNPJ_INVALIDO`, `EMITENTE_CPF_INVALIDO`, `EMITENTE_UF_INVALIDA`, `DESTINATARIO_CPF_E_CNPJ`, `ENDERECO_CEP_INVALIDO` |
| Estrutura | `IDE_AUSENTE`, `IDE_CSTAT_INVALIDO`, `EMITENTE_AUSENTE`, `LISTA_SERVICO_VAZIA`, `INFNFESIG_AUSENTE` |
| Aritmética | `SOMA_VSERVICO_DIVERGENTE`, `SOMA_VISS_DIVERGENTE`, `SOMA_VBC_DIVERGENTE`, `LIQUIDO_NAO_CONFERE`, `TOTAL_SEM_ITENS_NAO_ZERO` |
| Datas | `IDE_DTEMI_INVALIDO`, `IDE_DTEMI_SEM_FUSO`, `IDE_DTEMI_FUTURO` |
| Assinatura | `ASSINATURA_AUSENTE`, `ASSINATURA_URI_INVALIDA`, `ASSINATURA_REFERENCE_VAZIA` |
| Chave | `IDE_CHAVE_ACESSO_INVALIDA`, `IDE_CHAVE_ACESSO_ANO_DIVERGENTE` |

A lista completa está em `nfse_validator/codes.py` e na tabela do README.

## Limitações — leia antes de confiar

- **Não verifica criptografia da assinatura.** A ferramenta confere a
  *presença e a estrutura* do XMLDSig. Validação criptográfica real exige uma
  biblioteca de assinatura — use a do seu provedor/SDK.
- **Não valida o XSD do provedor municipal.** Cada prefeitura tem seu schema.
  Isto checa o layout ABRASF comum, não o schema da sua cidade.
- **Não emite NFS-e** e não substitui homologação.
- **Não é aconselhamento fiscal ou jurídico.** Nada aqui substitui um contador.
- Valores dos fixtures são **sintéticos**, com dígitos verificadores matematicamente
  válidos. Nenhuma empresa ou pessoa real está representada.

## Testes

```bash
make test
# ou
python3 -m unittest discover -s tests -v
```

69 testes cobrem cada código de erro, a fronteira de tolerância (0,01 passa,
0,02 falha), os dígitos de CPF/CNPJ, a saída JSON e os códigos de saída da CLI.

## Contribuindo

Issues e PRs bem-vindos. Regras:

1. Todo código de erro novo vem com teste.
2. Dinheiro sempre com `Decimal`.
3. Sem dependências novas no runtime.
4. Mensagens em português, com `hint` de como corrigir.

## Licença

MIT. Ver [LICENSE](LICENSE).
