"""
Testes automatizados para src/generator.py

Executar com:
    python -m unittest tests.test_generator -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from generator import generate_structure  # noqa: E402
from parser import Node  # noqa: E402


def make_sample_tree() -> Node:
    """
    Proj/
    ├── src/
    │   ├── main.py
    │   └── utils/
    │       └── helpers.py
    └── README.md
    """
    return Node(
        name="Proj",
        type="folder",
        children=[
            Node(
                name="src",
                type="folder",
                children=[
                    Node(name="main.py", type="file", children=[]),
                    Node(
                        name="utils",
                        type="folder",
                        children=[
                            Node(name="helpers.py", type="file", children=[])
                        ],
                    ),
                ],
            ),
            Node(name="README.md", type="file", children=[]),
        ],
    )


class TestGeneratorFullCreation(unittest.TestCase):
    def test_creates_all_folders_and_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tree = make_sample_tree()
            destination = tmp_path / "Proj"

            result = generate_structure(tree, destination)

            self.assertTrue((tmp_path / "Proj").is_dir())
            self.assertTrue((tmp_path / "Proj" / "src").is_dir())
            self.assertTrue((tmp_path / "Proj" / "src" / "main.py").is_file())
            self.assertTrue(
                (tmp_path / "Proj" / "src" / "utils").is_dir()
            )
            self.assertTrue(
                (tmp_path / "Proj" / "src" / "utils" / "helpers.py").is_file()
            )
            self.assertTrue((tmp_path / "Proj" / "README.md").is_file())

            self.assertEqual(len(result.created_folders), 3)  # Proj, src, utils
            self.assertEqual(
                len(result.created_files), 3
            )  # main.py, helpers.py, README.md
            self.assertEqual(result.existing_folders, [])
            self.assertEqual(result.skipped_files, [])
            self.assertEqual(result.overwritten_files, [])


class TestGeneratorExistingFolder(unittest.TestCase):
    def test_existing_folder_is_reported_separately(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            destination = tmp_path / "Proj"
            # Pré-cria a pasta raiz e a subpasta "src" antes de gerar.
            (destination / "src").mkdir(parents=True)

            tree = make_sample_tree()
            result = generate_structure(tree, destination)

            self.assertIn(str(destination), result.existing_folders)
            self.assertIn(str(destination / "src"), result.existing_folders)
            # "utils" ainda não existia, então deve estar em created_folders.
            self.assertIn(
                str(destination / "src" / "utils"), result.created_folders
            )
            self.assertNotIn(str(destination), result.created_folders)


class TestGeneratorExistingFile(unittest.TestCase):
    def test_existing_file_without_confirmation_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            destination = tmp_path / "Proj"
            destination.mkdir()
            existing_readme = destination / "README.md"
            existing_readme.write_text("conteúdo original", encoding="utf-8")

            tree = make_sample_tree()
            result = generate_structure(
                tree, destination, confirm_overwrite=lambda _p: False
            )

            self.assertIn(str(existing_readme), result.skipped_files)
            self.assertEqual(
                existing_readme.read_text(encoding="utf-8"),
                "conteúdo original",
            )


class TestGeneratorSkippedFiles(unittest.TestCase):
    def test_default_behavior_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            destination = tmp_path / "Proj"
            destination.mkdir()
            (destination / "README.md").write_text("original", encoding="utf-8")

            tree = make_sample_tree()
            # Sem passar confirm_overwrite -> usa o padrão (nunca sobrescreve)
            result = generate_structure(tree, destination)

            self.assertEqual(len(result.skipped_files), 1)
            self.assertEqual(len(result.overwritten_files), 0)
            self.assertEqual(
                (destination / "README.md").read_text(encoding="utf-8"),
                "original",
            )


class TestGeneratorOverwriteConfirmed(unittest.TestCase):
    def test_overwrite_confirmed_clears_file_content(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            destination = tmp_path / "Proj"
            destination.mkdir()
            readme = destination / "README.md"
            readme.write_text("conteúdo antigo", encoding="utf-8")

            tree = make_sample_tree()
            result = generate_structure(
                tree, destination, confirm_overwrite=lambda _p: True
            )

            self.assertIn(str(readme), result.overwritten_files)
            self.assertNotIn(str(readme), result.skipped_files)
            self.assertEqual(readme.read_text(encoding="utf-8"), "")


class TestGeneratorOverwriteDeclined(unittest.TestCase):
    def test_overwrite_declined_keeps_original_content(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            destination = tmp_path / "Proj"
            destination.mkdir()
            readme = destination / "README.md"
            readme.write_text("não mexa aqui", encoding="utf-8")

            tree = make_sample_tree()
            result = generate_structure(
                tree, destination, confirm_overwrite=lambda _p: False
            )

            self.assertIn(str(readme), result.skipped_files)
            self.assertEqual(
                readme.read_text(encoding="utf-8"), "não mexa aqui"
            )


class TestGeneratorStaysWithinDestination(unittest.TestCase):
    def test_all_created_paths_are_inside_destination(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).resolve()
            destination = tmp_path / "Proj"

            tree = make_sample_tree()
            result = generate_structure(tree, destination)

            all_paths = (
                result.created_folders
                + result.existing_folders
                + result.created_files
                + result.skipped_files
                + result.overwritten_files
            )

            self.assertTrue(all_paths, "esperava pelo menos um caminho gerado")

            for path_str in all_paths:
                resolved = Path(path_str).resolve()
                self.assertTrue(
                    str(resolved).startswith(str(tmp_path)),
                    f"caminho '{resolved}' está fora do destino '{tmp_path}'",
                )


if __name__ == "__main__":
    unittest.main()
