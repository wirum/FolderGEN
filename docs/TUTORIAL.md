# Tutorial do FolderGEN

## Índice

1. [O que é o FolderGEN](#o-que-é-o-foldergen)
2. [Como executar](#como-executar)
3. [Usando a CLI](#usando-a-cli)
4. [Usando os templates](#usando-os-templates)
5. [Criando um template personalizado](#criando-um-template-personalizado)
6. [Regras de segurança](#regras-de-segurança)
7. [Exemplo passo a passo](#exemplo-passo-a-passo)
8. [Licenças](#licenças)
9. [Erros comuns](#erros-comuns)
10. [Criando templates para contribuir](#criando-templates-para-contribuir)

---

## O que é o FolderGEN

O FolderGEN é uma ferramenta de linha de comando, escrita em Python, que cria
estruturas inteiras de projetos — pastas e arquivos — a partir de uma
descrição simples escrita em Markdown.

Em vez de criar manualmente cada pasta e arquivo de um novo projeto, você
descreve a estrutura desejada em um arquivo `.md` (ou escolhe um dos
templates prontos da biblioteca) e o FolderGEN cria tudo automaticamente no
seu sistema de arquivos, com a opção de gerar também um arquivo `LICENSE`
oficial.

## Como executar

O FolderGEN não tem dependências externas — só precisa de Python 3.10+.

Existem duas formas de executar, ambas a partir da raiz do repositório:

**1. Passando um arquivo Markdown diretamente:**

```bash
python src/main.py templates/python/fastapi.md --dest ./meu-destino
```

O parâmetro `--dest` é opcional; se omitido, o projeto é criado no
diretório atual (`.`).

**2. Sem argumentos, abrindo o menu interativo:**

```bash
python src/main.py
```

Isso mostra o menu principal da CLI, descrito na próxima seção.

## Usando a CLI

Ao executar `python src/main.py` sem argumentos, o menu principal aparece:

```text
FolderGEN CLI

[1] Criar projeto a partir de template
[2] Criar projeto a partir de arquivo Markdown
[3] Listar templates
[4] Sair
```

### [1] Criar projeto a partir de template

Este fluxo navega pela biblioteca de templates em duas etapas:

1. **Escolher categoria** — a CLI lista as categorias existentes em
   `templates/` (cada subpasta com pelo menos um arquivo `.md` vira uma
   opção), com a quantidade de templates de cada uma.
2. **Escolher template** — dentro da categoria escolhida, a CLI lista os
   templates disponíveis pelo nome do arquivo (sem a extensão `.md`).

Depois disso, o fluxo é o mesmo de qualquer criação de projeto:

3. **Escolher o destino** — você informa o diretório onde o projeto será
   criado (Enter usa o diretório atual).
4. **Visualizar a estrutura** — antes de criar qualquer coisa, o FolderGEN
   mostra a árvore completa que será gerada, no formato:

   ```text
   MeuProjeto/
   ├── src/
   │   └── main.py
   └── README.md
   ```

5. **Confirmar a criação** — você responde `s` ou `N` para prosseguir ou
   cancelar.
6. **Geração** — se confirmado, o FolderGEN cria as pastas e arquivos e
   mostra um resumo (quantas pastas/arquivos foram criados, quantos já
   existiam, quantos foram ignorados ou sobrescritos).
7. **Escolher licença** — por fim, a CLI pergunta qual licença gerar (ou
   "Sem licença"). Veja a seção [Licenças](#licenças) para os detalhes.

### [2] Criar projeto a partir de arquivo Markdown

Mesmo fluxo (destino → visualização → confirmação → geração → licença),
mas você informa diretamente o caminho de um arquivo `.md` próprio, em vez
de escolher um template da biblioteca.

### [3] Listar templates

Mostra as categorias disponíveis e permite escolher uma para ver os nomes
dos templates dentro dela, ou apertar Enter para listar todas as
categorias de uma vez — sem criar nenhum projeto.

### [4] Sair

Encerra a CLI.

## Usando os templates

Os templates ficam organizados por categoria dentro de `templates/`:

```text
templates/
├── python/
├── javascript/
├── typescript/
├── web/
├── dotnet/
├── java/
├── embedded/
├── data/
├── devops/
├── mobile/
├── game/
└── other/
```

Cada categoria é uma subpasta contendo um ou mais arquivos `.md`, cada um
representando um tipo de projeto. Por exemplo, `templates/python/` inclui
templates como `basic.md`, `cli.md`, `fastapi.md`, `flask.md`,
`django.md`, `discord-bot.md`, entre outros.

Exemplo real — `templates/python/fastapi.md`:

```md
# FastApiProject

- app/
  - __init__.py
  - main.py
  - api/
    - __init__.py
    - routes.py
  - models/
    - __init__.py
    - schemas.py
  - core/
    - __init__.py
    - config.py
- tests/
  - test_main.py
- requirements.txt
- README.md
- .env.example
- .gitignore
```

Você pode usar qualquer template diretamente pela opção `[1]` do menu
(navegando por categoria) ou apontando para o arquivo com a opção `[2]` ou
pela linha de comando (`python src/main.py templates/python/fastapi.md`).

Um template legado, `templates/python_basic.md`, também continua disponível
na raiz de `templates/` por compatibilidade com versões anteriores do
FolderGEN.

## Criando um template personalizado

Esta é a parte mais importante para tirar proveito do FolderGEN: qualquer
arquivo `.md` que siga a sintaxe abaixo pode ser usado como template.

Exemplo:

```md
# MeuProjeto

- src/
  - main.py
  - utils.py

- tests/
  - test_main.py

- README.md
```

### Regras da sintaxe

* **A primeira linha não vazia do arquivo deve ser o cabeçalho**
  `# NomeDoProjeto`. Esse nome se torna a pasta raiz do projeto criado.
* **Itens usam `- `** (hífen seguido de um espaço). Cada linha de item
  representa um arquivo ou uma pasta.
* **Pastas terminam com `/`** — por exemplo, `src/`.
* **Arquivos não terminam com `/`** — por exemplo, `main.py`.
* **A hierarquia é definida pela indentação.** Um item indentado em
  relação ao anterior é filho dele (e só pode ser filho de uma pasta, não
  de um arquivo).
* **A indentação deve usar múltiplos de 2 espaços** (2, 4, 6, ...). Uma
  quantidade de espaços que não seja múltiplo de 2 é rejeitada.
* **Tabs não são permitidos** na indentação; use apenas espaços.
* **Não pode haver "pulo de nível"** — um item não pode aparecer mais de
  um nível mais indentado que o item anterior (por exemplo, ir direto do
  nível 0 para o nível 2, sem passar pelo nível 1).
* **Linhas vazias são ignoradas** e podem ser usadas livremente para
  separar visualmente seções do template, como no exemplo acima.
* **Não pode existir outro cabeçalho `#`** em nenhuma linha depois do
  primeiro — apenas a primeira linha do arquivo define a pasta raiz.

## Regras de segurança

Antes de criar qualquer pasta ou arquivo, o FolderGEN valida a estrutura
interpretada. As regras de segurança realmente aplicadas são:

* **Bloqueio de path traversal** — nomes contendo `..` (por exemplo,
  `../fora-do-projeto`) são rejeitados, para impedir que o template saia
  do diretório de destino.
* **Bloqueio de caminhos absolutos** — nomes começando com `/` ou `\` são
  rejeitados.
* **Nomes perigosos ou inválidos** — são rejeitados nomes vazios, nomes
  contendo caracteres proibidos (`< > : " | ? * \`), nomes reservados do
  Windows (como `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`) e
  nomes com espaços no início ou no fim.
* **Duplicatas** — dois itens com o mesmo nome no mesmo nível da
  hierarquia são rejeitados (a comparação ignora maiúsculas/minúsculas,
  para evitar problemas em sistemas de arquivos que não diferenciam
  `README.md` de `readme.md`).
* **Proteção contra criação fora do destino escolhido** — mesmo que a
  estrutura em si seja válida, o FolderGEN confirma que a pasta raiz final
  do projeto continua dentro do diretório de destino informado, antes de
  criar qualquer coisa.

Se qualquer uma dessas regras for violada, o FolderGEN interrompe a
operação com uma mensagem de erro clara e **nenhum arquivo ou pasta é
criado**.

## Exemplo passo a passo

```text
Criar arquivo Markdown
        ↓
Definir estrutura
        ↓
Executar FolderGEN
        ↓
Selecionar o arquivo
        ↓
Visualizar árvore
        ↓
Confirmar
        ↓
Projeto criado
```

Na prática, usando a CLI:

```bash
python src/main.py
```

```text
FolderGEN CLI

[1] Criar projeto a partir de template
[2] Criar projeto a partir de arquivo Markdown
[3] Listar templates
[4] Sair

Escolha uma opção: 2
Caminho do arquivo Markdown: meu-projeto.md
Diretório de destino (Enter para diretório atual):

Estrutura interpretada:

MeuProjeto/
├── src/
│   ├── main.py
│   └── utils.py
├── tests/
│   └── test_main.py
└── README.md

Criar projeto em '/caminho/atual/MeuProjeto'? [s/N]: s

Concluído!

FolderGEN Summary

Folders created: 3
Folders already existing: 0
Files created: 4
Files skipped: 0
Files overwritten: 0
```

Depois do resumo, a CLI pergunta qual licença gerar (veja a seção
seguinte).

## Licenças

O FolderGEN pode gerar automaticamente um arquivo `LICENSE` dentro do
projeto recém-criado.

### Licenças disponíveis

```text
[1] MIT
[2] Apache License 2.0
[3] GNU GPLv2
[4] GNU GPLv3
[5] BSD 3-Clause
[6] The Unlicense
[7] Sem licença
```

### Escolha pela CLI

Depois de gerar a estrutura de pastas e arquivos, a CLI pergunta
automaticamente qual licença você deseja:

```text
Escolha uma licença:

[1] MIT
[2] Apache License 2.0
[3] GNU GPLv2
[4] GNU GPLv3
[5] BSD 3-Clause
[6] The Unlicense
[7] Sem licença

> 1

Nome do autor:
>
```

Escolhendo a opção `[7] Sem licença`, nenhum arquivo `LICENSE` é gerado e o
fluxo termina normalmente.

### Busca usando a fonte SPDX

Ao escolher uma licença (1 a 6), o FolderGEN **não** mantém os textos das
licenças embutidos no código. Em vez disso, ele busca o texto oficial em
tempo real na fonte pública da SPDX (Software Package Data Exchange),
usando o SPDX ID correspondente à licença escolhida.

### Cache local

Para evitar buscar repetidamente a mesma licença, o FolderGEN mantém um
cache local em `.cache/licenses/` (um arquivo de texto por licença). Da
segunda vez em diante, se o texto da licença já estiver em cache, ele é
reaproveitado sem uma nova requisição. A pasta `.cache/` está listada no
`.gitignore` e não deve ser versionada.

### O que acontece quando não há conexão

Se não houver conexão com a internet (ou a fonte da SPDX não responder a
tempo) e a licença também não estiver em cache, o FolderGEN mostra um erro
claro informando qual licença não pôde ser obtida, e **não cria nenhum
arquivo `LICENSE` incompleto**. O restante do projeto (pastas e arquivos já
gerados) não é afetado.

### Proteção contra sobrescrita do arquivo LICENSE

Se já existir um arquivo `LICENSE` no destino, o FolderGEN pergunta antes
de sobrescrevê-lo. Se a resposta for negativa (ou nenhuma confirmação for
dada), o arquivo existente é mantido intacto.

## Erros comuns

Abaixo, exemplos reais de estruturas inválidas e como corrigi-las.

### Tabs na indentação

Errado (a linha usa um caractere de tabulação):

```md
# Projeto
- src/
	- main.py
```

Correto (usar espaços):

```md
# Projeto
- src/
  - main.py
```

### Indentação inválida (não é múltiplo de 2)

Errado:

```md
# Projeto
- src/
   - main.py
```

Correto:

```md
# Projeto
- src/
  - main.py
```

### Pulo de nível

Errado (o item `main.py` pula direto do nível 0 para o nível 2):

```md
# Projeto
- src/
    - main.py
```

Correto:

```md
# Projeto
- src/
  - main.py
```

### Segundo cabeçalho

Errado (existe um segundo `#` depois do cabeçalho inicial):

```md
# Projeto
- src/
# OutroTitulo
- README.md
```

Correto (apenas um `#`, no início do arquivo):

```md
# Projeto
- src/
- README.md
```

### Arquivo sem cabeçalho

Errado (a primeira linha não é um cabeçalho `# Nome`):

```md
- src/
  - main.py
```

Correto:

```md
# Projeto
- src/
  - main.py
```

### Caminho absoluto

Errado:

```md
# Projeto
- /etc/config.txt
```

Correto (usar apenas nomes relativos, sem barra no início):

```md
# Projeto
- config.txt
```

### `../` (path traversal)

Errado:

```md
# Projeto
- ../fora-do-projeto.txt
```

Correto:

```md
# Projeto
- fora-do-projeto.txt
```

### Arquivos duplicados

Errado (dois itens `main.py` no mesmo nível):

```md
# Projeto
- src/
  - main.py
  - main.py
```

Correto (nomes únicos dentro do mesmo nível):

```md
# Projeto
- src/
  - main.py
  - helpers.py
```

## Criando templates para contribuir

Quer adicionar um novo template à biblioteca? Siga os passos abaixo:

1. **Escolher uma categoria existente** dentro de `templates/` (`python/`,
   `javascript/`, `typescript/`, `web/`, `dotnet/`, `java/`, `embedded/`,
   `data/`, `devops/`, `mobile/`, `game/` ou `other/`). Se nenhuma
   categoria existente for apropriada, discuta a criação de uma nova
   categoria em uma issue antes de enviar o template.
2. **Criar o arquivo `.md`** dentro da categoria escolhida, com um nome
   descritivo em minúsculas e hífens (por exemplo, `web-scraper.md`).
3. **Seguir a sintaxe do FolderGEN**, descrita na seção
   [Criando um template personalizado](#criando-um-template-personalizado)
   — cabeçalho único, itens com `- `, pastas terminadas em `/`, indentação
   de 2 espaços, sem tabs.
4. **Validar o template**, executando-o localmente para confirmar que ele
   é interpretado corretamente:

   ```bash
   python src/main.py templates/<categoria>/<seu-template>.md --dest /tmp/teste-template
   ```

5. **Rodar a suíte de testes** para garantir que o novo template passa na
   validação automática (veja a seção de testes em
   [CONTRIBUTING.md](../CONTRIBUTING.md)):

   ```bash
   python -m unittest discover -s tests
   ```

6. **Enviar a contribuição** seguindo o processo descrito em
   [CONTRIBUTING.md](../CONTRIBUTING.md).
