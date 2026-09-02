# Contribuindo com o FolderGEN

Obrigado por considerar contribuir! Este guia cobre tanto contribuições de
código quanto contribuições de templates para a biblioteca.

## Como contribuir

1. **Faça um fork** do repositório.
2. **Crie uma branch** descritiva:
   ```bash
   git checkout -b feature/nome-da-feature
   ```
3. **Faça suas alterações**, mantendo o estilo do código existente.
4. **Rode a suíte de testes** e garanta que tudo passa:
   ```bash
   python -m unittest discover -s tests
   ```
5. **Crie um commit claro**, explicando o que foi feito e por quê.
6. **Abra um Pull Request** descrevendo a mudança (veja a seção
   [Pull Requests](#pull-requests) abaixo).

## Contribuindo com templates

A biblioteca de templates fica em `templates/`, organizada por categoria
(`python/`, `javascript/`, `typescript/`, `web/`, `dotnet/`, `java/`,
`embedded/`, `data/`, `devops/`, `mobile/`, `game/`, `other/`).

- **Onde colocar o template**: dentro da subpasta da categoria mais
  apropriada. Se nenhuma categoria existente servir, abra uma issue antes
  de propor uma nova categoria.
- **Como escolher a categoria**: pense na tecnologia ou no tipo de projeto
  principal do template (um bot de Discord em Python vai em `python/`, um
  template de landing page estática vai em `web/`, etc.).
- **Convenção de nomes**: use letras minúsculas e hífens, sem espaços —
  por exemplo, `web-scraper.md`, `discord-bot.md`.
- **Sintaxe obrigatória**: siga exatamente a sintaxe descrita em
  [docs/TUTORIAL.md](docs/TUTORIAL.md#criando-um-template-personalizado) —
  cabeçalho único `# Nome`, itens com `- `, pastas terminadas em `/`,
  indentação em múltiplos de 2 espaços, sem tabs, sem pular níveis.
- **Como validar antes de enviar**: execute o template localmente para
  confirmar que ele é interpretado sem erros:
  ```bash
  python src/main.py templates/<categoria>/<seu-template>.md --dest /tmp/teste-template
  ```
  Em seguida, rode a suíte de testes — `tests/test_templates.py` valida
  automaticamente todos os arquivos `.md` encontrados em `templates/`
  (incluindo o novo):
  ```bash
  python -m unittest discover -s tests
  ```
- **Evite templates duplicados ou inúteis**: antes de propor um novo
  template, verifique se já não existe algo equivalente na mesma
  categoria. Prefira estruturas coerentes e enxutas em vez de listar
  arquivos que raramente seriam usados juntos.

## Contribuindo com código

- **Mantenha a arquitetura modular**: `parser.py`, `validator.py`,
  `generator.py` e `license_manager.py` não devem depender da CLI
  (`main.py`) — isso permite reaproveitar essa lógica em outras interfaces
  no futuro (por exemplo, uma GUI).
- **Não quebre funcionalidades existentes**: rode a suíte completa de
  testes antes de abrir o PR e confirme que nada que já funcionava parou
  de funcionar.
- **Adicione testes para novas funcionalidades**: qualquer novo
  comportamento (uma nova regra de validação, uma nova opção na CLI, etc.)
  deve vir acompanhado de testes em `tests/`.
- **Mantenha compatibilidade com a suíte atual**: evite alterar
  comportamentos e mensagens já cobertos por testes existentes, a menos
  que a mudança seja intencional e os testes sejam atualizados junto.
- Use Python moderno com type hints quando fizer sentido, funções
  pequenas com responsabilidade única, e prefira `pathlib` a manipulação
  manual de strings de caminho.
- Erros devem sempre ter mensagens claras, indicando a linha ou o item
  problemático quando possível.
- Não adicione dependências externas — o projeto usa apenas a biblioteca
  padrão do Python.

## Testes

O projeto usa exclusivamente `unittest` da biblioteca padrão. Para rodar
toda a suíte:

```bash
python -m unittest discover -s tests
```

A mesma suíte roda automaticamente no GitHub Actions (Python 3.11 e 3.12)
a cada `push` e `pull request`.

## Pull Requests

Para facilitar a revisão, cada PR deve:

- Ter uma **descrição clara** do que foi alterado e por quê.
- **Explicar as mudanças** relevantes (novo comportamento, correção de
  bug, novo template, etc.), especialmente se não forem óbvias pelo diff.
- **Informar quais testes foram executados** (por exemplo, "rodei
  `python -m unittest discover -s tests` e todos os testes passaram").
- **Manter o escopo focado** — prefira PRs pequenos e objetivos a mudanças
  grandes que misturam vários assuntos diferentes.

## Reportando bugs ou sugerindo features

Abra uma issue descrevendo:

- O comportamento esperado.
- O comportamento observado.
- Um exemplo mínimo de arquivo Markdown que reproduz o problema (se
  aplicável).

## Ideias futuras (fora do escopo atual)

- Interface gráfica (GUI).
- Suporte a templates com variáveis (ex: `{{nome_do_pacote}}`).
- Exportar/importar estruturas existentes de um diretório para Markdown.
