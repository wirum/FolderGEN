"""
validator.py

Responsável por validar a árvore gerada pelo parser antes que qualquer
arquivo ou pasta seja criado no sistema de arquivos.

Validações realizadas:
    * Nomes inválidos de arquivo/pasta (caracteres proibidos, vazios,
      referências a diretório pai "..", caminhos absolutos).
    * Itens duplicados dentro do mesmo nível.
    * Presença da pasta raiz (garantida pelo parser, mas revalidada aqui).
    * Prevenção de escrita fora do diretório de destino (path traversal).

Este módulo não cria nada no disco; apenas analisa a estrutura em
memória e levanta erros claros quando algo está errado.
"""

from __future__ import annotations

from pathlib import Path

from parser import Node


# Caracteres proibidos em nomes de arquivo/pasta (cobre Windows e Unix
# de forma conservadora, já que o projeto pode rodar em qualquer SO).
_FORBIDDEN_CHARS = set('<>:"|?*\\')

_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


class ValidationError(Exception):
    """Erro levantado quando a estrutura é inválida ou insegura."""


def validate_tree(root: Node) -> None:
    """
    Valida a árvore inteira a partir da raiz.

    Levanta ValidationError com uma mensagem clara na primeira
    inconsistência encontrada.
    """
    if root.type != "folder":
        raise ValidationError("a pasta raiz do projeto deve ser uma pasta.")

    _validate_name(root.name, path_hint=root.name)
    _validate_node_recursive(root, path_hint=root.name)


def _validate_node_recursive(node: Node, path_hint: str) -> None:
    if node.type != "folder":
        return

    seen_names: set[str] = set()

    for child in node.children:
        _validate_name(child.name, path_hint=f"{path_hint}/{child.name}")

        # Duplicidade é comparada de forma case-insensitive para evitar
        # problemas em sistemas de arquivos que não diferenciam maiúsculas
        # de minúsculas (Windows, macOS por padrão).
        key = child.name.lower()
        if key in seen_names:
            raise ValidationError(
                f"item duplicado em '{path_hint}/': '{child.name}' "
                "aparece mais de uma vez no mesmo nível."
            )
        seen_names.add(key)

        _validate_node_recursive(child, path_hint=f"{path_hint}/{child.name}")


def _validate_name(name: str, path_hint: str) -> None:
    """Valida um único nome de arquivo ou pasta."""
    if not name or not name.strip():
        raise ValidationError(f"nome vazio encontrado em '{path_hint}'.")

    if name in (".", ".."):
        raise ValidationError(
            f"nome inválido '{name}' em '{path_hint}': referências a "
            "diretório atual/pai não são permitidas."
        )

    if ".." in Path(name).parts:
        raise ValidationError(
            f"nome inválido '{name}' em '{path_hint}': não é permitido "
            "usar '..' para sair do diretório de destino."
        )

    if name.startswith("/") or name.startswith("\\"):
        raise ValidationError(
            f"nome inválido '{name}' em '{path_hint}': caminhos "
            "absolutos não são permitidos."
        )

    if len(Path(name).parts) > 1:
        raise ValidationError(
            f"nome inválido '{name}' em '{path_hint}': o nome não pode "
            "conter separadores de caminho ('/' ou '\\'). Use itens "
            "aninhados via indentação em vez disso."
        )

    forbidden_found = _FORBIDDEN_CHARS.intersection(set(name))
    if forbidden_found:
        chars = ", ".join(sorted(forbidden_found))
        raise ValidationError(
            f"nome inválido '{name}' em '{path_hint}': contém "
            f"caractere(s) não permitido(s): {chars}"
        )

    base_name = name.split(".")[0].lower()
    if base_name in _RESERVED_NAMES:
        raise ValidationError(
            f"nome inválido '{name}' em '{path_hint}': '{base_name}' é "
            "um nome reservado pelo sistema operacional."
        )

    if name != name.strip():
        raise ValidationError(
            f"nome inválido '{name}' em '{path_hint}': não pode "
            "começar ou terminar com espaços."
        )


def validate_destination(destination: Path, project_root_name: str) -> Path:
    """
    Valida o diretório de destino escolhido pelo usuário e retorna o
    caminho absoluto e resolvido onde a pasta raiz do projeto será
    criada.

    Garante que o destino final não escapa do diretório de destino
    original (proteção contra path traversal via nome do projeto).
    """
    destination = destination.expanduser().resolve()

    if not destination.exists():
        raise ValidationError(
            f"o diretório de destino '{destination}' não existe."
        )

    if not destination.is_dir():
        raise ValidationError(
            f"o destino '{destination}' não é um diretório."
        )

    project_path = (destination / project_root_name).resolve()

    try:
        project_path.relative_to(destination)
    except ValueError as exc:
        raise ValidationError(
            "a pasta raiz do projeto resultaria em um caminho fora do "
            "diretório de destino. Operação bloqueada por segurança."
        ) from exc

    return project_path
