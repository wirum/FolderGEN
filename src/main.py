"""
main.py

Interface de linha de comando (CLI) do FolderGEN.

Este módulo é responsável apenas pela interação com o usuário: ler
argumentos/entradas, chamar os módulos parser, validator e generator,
e exibir resultados. Nenhuma lógica de parsing/validação/geração vive
aqui — isso permite reaproveitar esses módulos futuramente em uma GUI.

Uso:
    python src/main.py <caminho_para_arquivo.md> [--dest DIRETORIO]

Se nenhum argumento for passado, um menu interativo é exibido.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator import generate_structure, GenerationResult
from parser import Node, ParseError, parse_markdown
from validator import ValidationError, validate_destination, validate_tree


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.markdown_file is None:
        return _run_interactive_menu()

    return _run_from_file(
        markdown_path=Path(args.markdown_file),
        destination=Path(args.dest),
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser_cli = argparse.ArgumentParser(
        prog="FolderGEN",
        description=(
            "Cria estruturas de pastas e arquivos a partir de uma "
            "descrição em Markdown."
        ),
    )
    parser_cli.add_argument(
        "markdown_file",
        nargs="?",
        help="Caminho para o arquivo .md com a estrutura do projeto.",
    )
    parser_cli.add_argument(
        "--dest",
        default=".",
        help="Diretório onde o projeto será criado (padrão: diretório atual).",
    )
    return parser_cli.parse_args(argv)


def _run_interactive_menu() -> int:
    while True:
        print("\nFolderGEN CLI\n")
        print("[1] Criar projeto a partir de template")
        print("[2] Criar projeto a partir de arquivo Markdown")
        print("[3] Listar templates")
        print("[4] Sair")

        choice = input("\nEscolha uma opção: ").strip()

        if choice == "1":
            _menu_create_from_template()
        elif choice == "2":
            _menu_create_from_file()
        elif choice == "3":
            _menu_list_templates()
        elif choice == "4":
            print("Até mais!")
            return 0
        else:
            print("Opção inválida. Tente novamente.")


def _menu_list_templates() -> None:
    templates = sorted(TEMPLATES_DIR.glob("*.md"))
    if not templates:
        print("Nenhum template encontrado em 'templates/'.")
        return

    print("\nTemplates disponíveis:")
    for template in templates:
        print(f"  - {template.name}")


def _menu_create_from_template() -> None:
    templates = sorted(TEMPLATES_DIR.glob("*.md"))
    if not templates:
        print("Nenhum template encontrado em 'templates/'.")
        return

    print("\nTemplates disponíveis:")
    for index, template in enumerate(templates, start=1):
        print(f"  [{index}] {template.name}")

    choice = input("Escolha o número do template: ").strip()
    try:
        selected = templates[int(choice) - 1]
    except (ValueError, IndexError):
        print("Escolha inválida.")
        return

    dest = input("Diretório de destino (Enter para diretório atual): ").strip()
    dest = dest or "."

    _run_from_file(markdown_path=selected, destination=Path(dest))


def _menu_create_from_file() -> None:
    path_str = input("Caminho do arquivo Markdown: ").strip()
    dest = input("Diretório de destino (Enter para diretório atual): ").strip()
    dest = dest or "."

    _run_from_file(markdown_path=Path(path_str), destination=Path(dest))


def _run_from_file(markdown_path: Path, destination: Path) -> int:
    """
    Executa o fluxo completo: ler -> parsear -> validar -> mostrar
    estrutura -> confirmar -> gerar.
    """
    content = _read_markdown_file(markdown_path)
    if content is None:
        return 1

    tree = _parse(content)
    if tree is None:
        return 1

    if not _validate(tree):
        return 1

    print("\nEstrutura interpretada:\n")
    _print_tree(tree)

    project_path = _resolve_destination(tree, destination)
    if project_path is None:
        return 1

    if not _confirm(f"\nCriar projeto em '{project_path}'? [s/N]: "):
        print("Operação cancelada.")
        return 0

    result = _generate(tree, project_path)
    if result is None:
        return 1

    print("\nConcluído!\n")
    print(result.summary())
    return 0


def _read_markdown_file(path: Path) -> str | None:
    if not path.exists():
        print(f"Erro: arquivo '{path}' não encontrado.")
        return None

    if not path.is_file():
        print(f"Erro: '{path}' não é um arquivo.")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Erro ao ler o arquivo '{path}': {exc}")
        return None


def _parse(content: str) -> Node | None:
    try:
        return parse_markdown(content)
    except ParseError as exc:
        print(f"Erro de sintaxe: {exc}")
        return None


def _validate(tree: Node) -> bool:
    try:
        validate_tree(tree)
        return True
    except ValidationError as exc:
        print(f"Erro de validação: {exc}")
        return False


def _resolve_destination(tree: Node, destination: Path) -> Path | None:
    try:
        return validate_destination(destination, tree.name)
    except ValidationError as exc:
        print(f"Erro no destino: {exc}")
        return None


def _generate(tree: Node, project_path: Path) -> GenerationResult | None:
    try:
        return generate_structure(
            tree,
            destination=project_path,
            confirm_overwrite=_ask_overwrite,
        )
    except OSError as exc:
        print(f"Erro ao criar arquivos/pastas: {exc}")
        return None


def _ask_overwrite(path: Path) -> bool:
    return _confirm(f"Arquivo '{path}' já existe. Sobrescrever? [s/N]: ")


def _confirm(prompt: str) -> bool:
    answer = input(prompt).strip().lower()
    return answer in ("s", "sim", "y", "yes")


def _print_tree(node: Node, prefix: str = "", is_last: bool = True, is_root: bool = True) -> None:
    """Imprime a árvore no formato visual estilo 'tree'."""
    if is_root:
        print(f"{node.name}/")
        children_prefix = ""
    else:
        connector = "└── " if is_last else "├── "
        suffix = "/" if node.type == "folder" else ""
        print(f"{prefix}{connector}{node.name}{suffix}")
        children_prefix = prefix + ("    " if is_last else "│   ")

    if node.type == "folder":
        for index, child in enumerate(node.children):
            is_last_child = index == len(node.children) - 1
            _print_tree(
                child,
                prefix=children_prefix,
                is_last=is_last_child,
                is_root=False,
            )


if __name__ == "__main__":
    sys.exit(main())
