# FolderGEN

Crie estruturas inteiras de projetos — pastas e arquivos — a partir de uma
descrição simples em Markdown, com uma biblioteca de templates prontos e
geração automática de arquivos `LICENSE`.

## Features

- **Sintaxe simples baseada em Markdown** para descrever qualquer estrutura
  de projeto.
- **Biblioteca com 53 templates** organizados em 12 categorias, prontos
  para uso.
- **CLI interativa** com navegação por categoria, visualização da árvore
  antes de criar e resumo do que foi gerado.
- **Geração de arquivos `LICENSE`** para 6 licenças, buscando o texto
  oficial diretamente da SPDX, com cache local.
- **Validações de segurança** contra path traversal, caminhos absolutos,
  nomes inválidos e duplicatas.
- **Sem dependências externas** — apenas a biblioteca padrão do Python.
- **183 testes automatizados** rodando em CI a cada push/PR.

## Categorias de templates

| Categoria | Templates |
|---|---|
| python | 14 |
| javascript | 7 |
| web | 7 |
| dotnet | 4 |
| java | 4 |
| typescript | 3 |
| embedded | 3 |
| data | 3 |
| devops | 3 |
| mobile | 2 |
| game | 1 |
| other | 1 |

Guia completo de uso e da sintaxe de templates em
[docs/TUTORIAL.md](docs/TUTORIAL.md).

## Como executar

Requer apenas Python 3.10+ (nenhuma dependência externa).

```bash
# Criar projeto a partir de um template da biblioteca
python src/main.py templates/python/fastapi.md --dest ./meu-destino

# Ou abrir o menu interativo (navega por categoria, licença, etc.)
python src/main.py
```

## Exemplo rápido

```bash
python src/main.py templates/python/basic.md --dest ./meu-destino
```

```text
Estrutura interpretada:

BasicProject/
├── src/
│   └── main.py
├── tests/
│   └── test_main.py
├── README.md
├── requirements.txt
└── .gitignore

Criar projeto em './meu-destino/BasicProject'? [s/N]: s
```

## Sintaxe dos templates

```md
# MeuProjeto

- src/
  - main.py
- tests/
  - test_main.py
- README.md
```

- A primeira linha deve ser `# NomeDoProjeto` — define a pasta raiz.
- Itens usam `- `; pastas terminam em `/`, arquivos não.
- A hierarquia é definida por indentação (múltiplos de 2 espaços, sem tabs).

Sintaxe completa, regras de segurança e como criar templates próprios em
[docs/TUTORIAL.md](docs/TUTORIAL.md).

## Testes

```bash
python -m unittest discover -s tests
```

O projeto usa apenas `unittest` da biblioteca padrão — nenhuma dependência
de teste externa.

## CI (GitHub Actions)

Todo `push` e `pull request` executa automaticamente a suíte de testes em
Python 3.11 e 3.12 (`.github/workflows/tests.yml`). O resultado aparece na
aba **Actions** do repositório e no status do commit/PR.

## Contribuindo

Contribuições são bem-vindas — desde correções de bugs até novos templates.
Veja o guia completo em [CONTRIBUTING.md](CONTRIBUTING.md).

## Licença

Este projeto (o próprio FolderGEN) é distribuído sob a licença MIT. Veja
[LICENSE](LICENSE).
