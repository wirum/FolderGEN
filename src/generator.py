"""
generator.py

Responsável por receber uma árvore já validada (Node) e criar
efetivamente as pastas e arquivos correspondentes no sistema de
arquivos, a partir de um diretório de destino.

Este módulo não faz parsing nem validação de segurança — assume que a
árvore recebida já passou por validator.validate_tree(). Ainda assim,
por segurança em profundidade, evita sobrescrever arquivos existentes
sem confirmação explícita.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from parser import Node


@dataclass
class GenerationResult:
    """Resumo do que foi criado, já existia, ignorado ou sobrescrito."""

    created_folders: list[str] = field(default_factory=list)
    existing_folders: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    overwritten_files: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "FolderGEN Summary",
            "",
            f"Folders created: {len(self.created_folders)}",
            f"Folders already existing: {len(self.existing_folders)}",
            f"Files created: {len(self.created_files)}",
            f"Files skipped: {len(self.skipped_files)}",
            f"Files overwritten: {len(self.overwritten_files)}",
        ]
        return "\n".join(lines)


# Callback chamado quando um arquivo já existe, para decidir se deve
# sobrescrever. Recebe o caminho do arquivo e retorna True (sobrescreve)
# ou False (mantém o arquivo original).
ConfirmOverwriteFn = Callable[[Path], bool]


def _default_confirm_overwrite(_path: Path) -> bool:
    """Comportamento padrão: nunca sobrescreve sem confirmação explícita."""
    return False


def generate_structure(
    root: Node,
    destination: Path,
    confirm_overwrite: ConfirmOverwriteFn = _default_confirm_overwrite,
) -> GenerationResult:
    """
    Cria a estrutura de pastas e arquivos representada por `root`
    dentro de `destination`.

    `destination` deve ser o caminho completo onde a pasta raiz do
    projeto (root.name) será criada — normalmente o retorno de
    validator.validate_destination().

    `confirm_overwrite` é chamado sempre que um arquivo já existe no
    destino, permitindo que a camada de CLI (ou futuramente GUI)
    decida se sobrescreve ou não.
    """
    result = GenerationResult()
    _create_node(root, parent_path=destination.parent, result=result,
                 confirm_overwrite=confirm_overwrite)
    return result


def _create_node(
    node: Node,
    parent_path: Path,
    result: GenerationResult,
    confirm_overwrite: ConfirmOverwriteFn,
) -> None:
    current_path = parent_path / node.name

    if node.type == "folder":
        already_exists = current_path.exists()

        current_path.mkdir(parents=True, exist_ok=True)

        if already_exists:
            result.existing_folders.append(str(current_path))
        else:
            result.created_folders.append(str(current_path))

        for child in node.children:
            _create_node(
                child,
                parent_path=current_path,
                result=result,
                confirm_overwrite=confirm_overwrite,
            )
    else:
        _create_file(current_path, result, confirm_overwrite)


def _create_file(
    path: Path,
    result: GenerationResult,
    confirm_overwrite: ConfirmOverwriteFn,
) -> None:
    if path.exists():
        if confirm_overwrite(path):
            path.write_text("", encoding="utf-8")
            result.overwritten_files.append(str(path))
        else:
            result.skipped_files.append(str(path))
        return

    path.touch()
    result.created_files.append(str(path))
