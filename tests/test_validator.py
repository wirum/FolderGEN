"""
Testes automatizados para src/validator.py

Executar com:
    python -m unittest tests.test_validator -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parser import Node  # noqa: E402
from validator import (  # noqa: E402
    ValidationError,
    validate_destination,
    validate_tree,
)


def make_tree(root_name: str, children: list[Node]) -> Node:
    return Node(name=root_name, type="folder", children=children)


class TestValidatorPathTraversal(unittest.TestCase):
    def test_dotdot_as_name_raises(self):
        tree = make_tree("Proj", [Node(name="..", type="folder", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_dotdot_inside_name_raises(self):
        tree = make_tree(
            "Proj", [Node(name="../evil.txt", type="file", children=[])]
        )
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_dotdot_nested_deep_raises(self):
        inner = Node(name="../../escape.txt", type="file", children=[])
        folder = Node(name="src", type="folder", children=[inner])
        tree = make_tree("Proj", [folder])
        with self.assertRaises(ValidationError):
            validate_tree(tree)


class TestValidatorAbsolutePaths(unittest.TestCase):
    def test_absolute_unix_path_raises(self):
        tree = make_tree(
            "Proj", [Node(name="/etc/passwd", type="file", children=[])]
        )
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_absolute_windows_style_backslash_raises(self):
        tree = make_tree(
            "Proj", [Node(name="\\Windows\\System32", type="file", children=[])]
        )
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_name_with_path_separator_raises(self):
        tree = make_tree(
            "Proj", [Node(name="a/b.txt", type="file", children=[])]
        )
        with self.assertRaises(ValidationError):
            validate_tree(tree)


class TestValidatorForbiddenChars(unittest.TestCase):
    def test_colon_in_name_raises(self):
        tree = make_tree("Proj", [Node(name="file:name.txt", type="file", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_asterisk_in_name_raises(self):
        tree = make_tree("Proj", [Node(name="wild*card.txt", type="file", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_question_mark_in_name_raises(self):
        tree = make_tree("Proj", [Node(name="what?.txt", type="file", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_pipe_in_name_raises(self):
        tree = make_tree("Proj", [Node(name="a|b.txt", type="file", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)


class TestValidatorReservedNames(unittest.TestCase):
    def test_con_raises(self):
        tree = make_tree("Proj", [Node(name="CON", type="folder", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_con_with_extension_raises(self):
        tree = make_tree("Proj", [Node(name="con.txt", type="file", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_com1_raises(self):
        tree = make_tree("Proj", [Node(name="COM1", type="file", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_lpt9_lowercase_raises(self):
        tree = make_tree("Proj", [Node(name="lpt9", type="folder", children=[])])
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_normal_name_similar_to_reserved_is_allowed(self):
        # "console.py" não deve ser bloqueado (base_name != "con")
        tree = make_tree("Proj", [Node(name="console.py", type="file", children=[])])
        validate_tree(tree)  # não deve levantar


class TestValidatorDuplicates(unittest.TestCase):
    def test_duplicate_files_same_level_raises(self):
        tree = make_tree(
            "Proj",
            [
                Node(name="main.py", type="file", children=[]),
                Node(name="main.py", type="file", children=[]),
            ],
        )
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_duplicate_folders_same_level_raises(self):
        tree = make_tree(
            "Proj",
            [
                Node(name="src", type="folder", children=[]),
                Node(name="src", type="folder", children=[]),
            ],
        )
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_duplicate_case_insensitive_raises(self):
        tree = make_tree(
            "Proj",
            [
                Node(name="README.md", type="file", children=[]),
                Node(name="readme.md", type="file", children=[]),
            ],
        )
        with self.assertRaises(ValidationError):
            validate_tree(tree)

    def test_same_name_different_levels_is_allowed(self):
        # "main.py" em dois níveis diferentes não é duplicata.
        inner = Node(name="main.py", type="file", children=[])
        outer = Node(name="src", type="folder", children=[inner])
        tree = make_tree(
            "Proj",
            [outer, Node(name="main.py", type="file", children=[])],
        )
        validate_tree(tree)  # não deve levantar


class TestValidatorDestination(unittest.TestCase):
    def test_destination_must_exist(self):
        with self.assertRaises(ValidationError):
            validate_destination(Path("/caminho/que/nao/existe/xyz"), "Proj")

    def test_destination_must_be_directory(self):
        with tempfile.NamedTemporaryFile() as tmp_file:
            with self.assertRaises(ValidationError):
                validate_destination(Path(tmp_file.name), "Proj")

    def test_valid_destination_resolves_project_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = validate_destination(Path(tmp_dir), "Proj")
            self.assertEqual(result, (Path(tmp_dir) / "Proj").resolve())


if __name__ == "__main__":
    unittest.main()
