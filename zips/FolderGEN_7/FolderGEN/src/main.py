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
from license_manager import LicenseError, generate_license_file, list_available_licenses
from parser import Node, ParseError, parse_markdown
from validator import ValidationError, validate_destination, validate_tree


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "licenses"


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


def _discover_categories() -> list[str]:
    """
    Retorna os nomes das subpastas de templates/ que contêm pelo menos
    um arquivo .md, em ordem alfabética. Cada subpasta é uma categoria
    (ex.: python, javascript, web, ...).
    """
    if not TEMPLATES_DIR.is_dir():
        return []

    categories = []
    for entry in sorted(TEMPLATES_DIR.iterdir()):
        if entry.is_dir() and any(entry.glob("*.md")):
            categories.append(entry.name)
    return categories


def _templates_in_category(category: str) -> list[Path]:
    return sorted((TEMPLATES_DIR / category).glob("*.md"))


def _menu_list_templates() -> None:
    categories = _discover_categories()
    if not categories:
        print("Nenhuma categoria de template encontrada em 'templates/'.")
        return

    print("\nTemplates\n")
    for index, category in enumerate(categories, start=1):
        count = len(_templates_in_category(category))
        print(f"  [{index}] {category.capitalize()} ({count})")

    choice = input("\nEscolha uma categoria (Enter para ver todas): ").strip()

    if not choice:
        for category in categories:
            _print_category_templates(category)
        return

    try:
        selected_category = categories[int(choice) - 1]
    except (ValueError, IndexError):
        print("Categoria inválida.")
        return

    _print_category_templates(selected_category)


def _print_category_templates(category: str) -> None:
    templates = _templates_in_category(category)
    print(f"\n{category.capitalize()}:")
    for template in templates:
        print(f"  - {template.stem}")


def _menu_create_from_template() -> None:
    categories = _discover_categories()
    if not categories:
        print("Nenhuma categoria de template encontrada em 'templates/'.")
        return

    print("\nTemplates\n")
    for index, category in enumerate(categories, start=1):
        count = len(_templates_in_category(category))
        print(f"  [{index}] {category.capitalize()} ({count})")

    category_choice = input("\nEscolha uma categoria: ").strip()
    try:
        selected_category = categories[int(category_choice) - 1]
    except (ValueError, IndexError):
        print("Categoria inválida.")
        return

    templates = _templates_in_category(selected_category)
    print(f"\n{selected_category.capitalize()}:")
    for index, template in enumerate(templates, start=1):
        print(f"  [{index}] {template.stem}")

    template_choice = input("\nEscolha o número do template: ").strip()
    try:
        selected = templates[int(template_choice) - 1]
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

    _handle_license_selection(project_path)

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


def _handle_license_selection(project_path: Path) -> None:
    """
    Pergunta ao usuário qual licença deseja e, se aplicável, gera o
    arquivo LICENSE dentro do projeto recém-criado.
    """
    licenses = list_available_licenses()
    labels = list(licenses.keys())

    print("\nEscolha uma licença:\n")
    for index, label in enumerate(labels, start=1):
        print(f"  [{index}] {label}")
    no_license_option = len(labels) + 1
    print(f"  [{no_license_option}] Sem licença")

    choice = input("\n> ").strip()

    try:
        choice_index = int(choice)
    except ValueError:
        print("Escolha inválida. Nenhuma licença foi gerada.")
        return

    if choice_index == no_license_option:
        return

    if not (1 <= choice_index <= len(labels)):
        print("Escolha inválida. Nenhuma licença foi gerada.")
        return

    label = labels[choice_index - 1]
    spdx_id = licenses[label]

    author = input("\nNome do autor:\n> ").strip() or None

    try:
        license_path = generate_license_file(
            spdx_id,
            destination_dir=project_path,
            author=author,
            cache_dir=CACHE_DIR,
            confirm_overwrite=_ask_overwrite,
        )
    except LicenseError as exc:
        print(f"\nErro ao obter a licença '{label}': {exc}")
        print("Nenhum arquivo LICENSE foi criado ou alterado.")
        return

    if license_path is None:
        print("\nArquivo LICENSE existente foi mantido (não sobrescrito).")
    else:
        print(f"\nArquivo LICENSE ({label}) criado em '{license_path}'.")


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
