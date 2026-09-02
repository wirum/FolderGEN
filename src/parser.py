"""
parser.py

Responsável por ler e interpretar arquivos Markdown que descrevem a
estrutura de um projeto, transformando-os em uma representação interna
(em árvore) que pode ser validada e depois usada para gerar pastas e
arquivos reais no sistema de arquivos.

A sintaxe suportada:

    # NomeDoProjeto

    - src/
      - main.py
      - utils/
        - helpers.py
    - README.md

Regras:
    * A primeira linha não vazia do arquivo deve ser "# NomeDoProjeto".
    * Itens são linhas iniciadas por "- " (após indentação).
    * Um item terminado em "/" representa uma pasta.
    * Um item sem "/" no final representa um arquivo.
    * A indentação (múltiplos de 2 espaços) define a hierarquia.
    * Linhas em branco são ignoradas.
"""

from __future__ import annotations

from dataclasses import dataclass, field


INDENT_SIZE = 2


class ParseError(Exception):
    """Erro levantado quando o Markdown não pode ser interpretado."""

    def __init__(self, message: str, line_number: int | None = None):
        self.line_number = line_number
        if line_number is not None:
            message = f"Linha {line_number}: {message}"
        super().__init__(message)


@dataclass
class Node:
    """Representa um item da estrutura (arquivo ou pasta)."""

    name: str
    type: str  # "file" ou "folder"
    children: list["Node"] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {"name": self.name, "type": self.type}
        if self.type == "folder":
            result["children"] = [child.to_dict() for child in self.children]
        return result


@dataclass
class _RawItem:
    """Linha de item já interpretada, antes de virar Node na árvore."""

    name: str
    is_folder: bool
    level: int
    line_number: int


def parse_markdown(content: str) -> Node:
    """
    Interpreta o conteúdo de um arquivo Markdown de estrutura e retorna
    o Node raiz (a pasta do projeto).

    Levanta ParseError se o conteúdo estiver mal formado.
    """
    lines = content.splitlines()

    root_name, header_line_index = _extract_root_name(lines)
    raw_items = _extract_raw_items(lines, start_index=header_line_index + 1)

    root = Node(name=root_name, type="folder", children=[])
    _build_tree(raw_items, root)

    return root


def _extract_root_name(lines: list[str]) -> tuple[str, int]:
    """
    Encontra a primeira linha não vazia do arquivo e garante que ela
    seja um cabeçalho "# NomeDoProjeto". Retorna o nome e o índice
    (0-based) dessa linha na lista original.
    """
    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped == "":
            continue

        if not stripped.startswith("# "):
            raise ParseError(
                "a primeira linha do arquivo deve ser o cabeçalho "
                "'# NomeDoProjeto', representando a pasta raiz.",
                line_number=index + 1,
            )

        name = stripped[2:].strip()
        if not name:
            raise ParseError(
                "o nome da pasta raiz não pode estar vazio.",
                line_number=index + 1,
            )

        return name, index

    raise ParseError("o arquivo está vazio ou não contém conteúdo válido.")


def _extract_raw_items(lines: list[str], start_index: int) -> list[_RawItem]:
    """
    Percorre as linhas após o cabeçalho e extrai os itens (arquivos e
    pastas), calculando indentação e detectando um segundo cabeçalho
    "#" (que não é permitido).
    """
    raw_items: list[_RawItem] = []

    for offset, raw_line in enumerate(lines[start_index:]):
        line_number = start_index + offset + 1

        if raw_line.strip() == "":
            continue

        if raw_line.lstrip().startswith("#"):
            raise ParseError(
                "encontrado um segundo cabeçalho '#'. Apenas a primeira "
                "linha do arquivo pode definir a pasta raiz.",
                line_number=line_number,
            )

        raw_items.append(_parse_item_line(raw_line, line_number))

    if not raw_items:
        raise ParseError(
            "nenhum item de estrutura encontrado após o cabeçalho da "
            "pasta raiz."
        )

    return raw_items


def _parse_item_line(raw_line: str, line_number: int) -> _RawItem:
    """Interpreta uma única linha de item, retornando um _RawItem."""
    leading_whitespace = raw_line[: len(raw_line) - len(raw_line.lstrip())]

    if "\t" in leading_whitespace:
        raise ParseError(
            "indentação com tabs não é suportada; use espaços "
            f"(múltiplos de {INDENT_SIZE}).",
            line_number=line_number,
        )

    leading_spaces = len(raw_line) - len(raw_line.lstrip(" "))

    if leading_spaces % INDENT_SIZE != 0:
        raise ParseError(
            f"indentação inconsistente ({leading_spaces} espaços). "
            f"Use múltiplos de {INDENT_SIZE} espaços.",
            line_number=line_number,
        )

    level = leading_spaces // INDENT_SIZE
    content = raw_line.strip()

    if not content.startswith("- "):
        raise ParseError(
            "item mal formado; itens devem começar com '- '.",
            line_number=line_number,
        )

    item_text = content[2:].strip()

    if not item_text:
        raise ParseError("nome de item vazio.", line_number=line_number)

    is_folder = item_text.endswith("/")
    name = item_text[:-1] if is_folder else item_text

    if not name:
        raise ParseError(
            "nome de pasta vazio (apenas '/' informado).",
            line_number=line_number,
        )

    return _RawItem(
        name=name, is_folder=is_folder, level=level, line_number=line_number
    )


def _build_tree(raw_items: list[_RawItem], root: Node) -> None:
    """
    Constrói a árvore de Nodes a partir da lista linear de _RawItem,
    usando uma pilha para controlar a hierarquia via níveis de
    indentação.
    """
    # Cada entrada da pilha é (nível, node)
    stack: list[tuple[int, Node]] = [(-1, root)]

    for item in raw_items:
        if item.level > stack[-1][0] + 1:
            raise ParseError(
                "indentação inválida: o item pulou um nível na "
                "hierarquia (verifique se não faltou um item pai).",
                line_number=item.line_number,
            )

        # Desempilha até achar o pai correto para este nível
        while item.level <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if parent.type != "folder":
            raise ParseError(
                f"o item '{item.name}' tenta ser filho de um arquivo "
                f"('{parent.name}'); apenas pastas podem ter filhos.",
                line_number=item.line_number,
            )

        node = Node(
            name=item.name,
            type="folder" if item.is_folder else "file",
            children=[],
        )
        parent.children.append(node)

        if item.is_folder:
            stack.append((item.level, node))
