"""
Testes automatizados para src/parser.py

Executar com:
    python -m unittest tests.test_parser -v
ou, a partir da raiz do projeto:
    python -m unittest discover -s tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parser import Node, ParseError, parse_markdown  # noqa: E402


class TestParserValidTemplate(unittest.TestCase):
    def test_valid_template_produces_correct_tree(self):
        content = """# MeuProjeto

- src/
  - main.py
  - utils/
    - __init__.py
- tests/
  - test_main.py
- README.md
- requirements.txt
"""
        tree = parse_markdown(content)

        self.assertEqual(tree.name, "MeuProjeto")
        self.assertEqual(tree.type, "folder")

        names = [child.name for child in tree.children]
        self.assertEqual(
            names, ["src", "tests", "README.md", "requirements.txt"]
        )

        src = tree.children[0]
        self.assertEqual(src.type, "folder")
        self.assertEqual([c.name for c in src.children], ["main.py", "utils"])

        utils = src.children[1]
        self.assertEqual(utils.type, "folder")
        self.assertEqual(len(utils.children), 1)
        self.assertEqual(utils.children[0].name, "__init__.py")
        self.assertEqual(utils.children[0].type, "file")

        readme = tree.children[2]
        self.assertEqual(readme.type, "file")


class TestParserBlankLines(unittest.TestCase):
    def test_blank_lines_are_ignored(self):
        content = """# Proj

- src/

  - main.py


- README.md
"""
        tree = parse_markdown(content)
        self.assertEqual([c.name for c in tree.children], ["src", "README.md"])
        self.assertEqual(
            [c.name for c in tree.children[0].children], ["main.py"]
        )

    def test_leading_blank_lines_before_header_are_ignored(self):
        content = "\n\n\n# Proj\n- file.txt\n"
        tree = parse_markdown(content)
        self.assertEqual(tree.name, "Proj")
        self.assertEqual(tree.children[0].name, "file.txt")


class TestParserDeepHierarchy(unittest.TestCase):
    def test_deeply_nested_structure(self):
        content = """# Proj
- a/
  - b/
    - c/
      - d/
        - e.txt
"""
        tree = parse_markdown(content)

        node = tree
        for expected_name in ["a", "b", "c", "d"]:
            node = node.children[0]
            self.assertEqual(node.name, expected_name)
            self.assertEqual(node.type, "folder")

        leaf = node.children[0]
        self.assertEqual(leaf.name, "e.txt")
        self.assertEqual(leaf.type, "file")

    def test_siblings_at_multiple_depths(self):
        content = """# Proj
- a/
  - b1/
    - x.txt
  - b2/
    - y.txt
- c.txt
"""
        tree = parse_markdown(content)
        a = tree.children[0]
        self.assertEqual([c.name for c in a.children], ["b1", "b2"])
        self.assertEqual(a.children[0].children[0].name, "x.txt")
        self.assertEqual(a.children[1].children[0].name, "y.txt")
        self.assertEqual(tree.children[1].name, "c.txt")


class TestParserInvalidIndentation(unittest.TestCase):
    def test_indentation_not_multiple_of_two_raises(self):
        content = """# Proj
- src/
   - main.py
"""
        with self.assertRaises(ParseError):
            parse_markdown(content)

    def test_odd_indentation_single_space_raises(self):
        content = "# Proj\n- src/\n - main.py\n"
        with self.assertRaises(ParseError):
            parse_markdown(content)


class TestParserTabs(unittest.TestCase):
    def test_tabs_in_indentation_raise(self):
        content = "# Proj\n- src/\n\t- main.py\n"
        with self.assertRaises(ParseError):
            parse_markdown(content)


class TestParserLevelSkip(unittest.TestCase):
    def test_skipping_a_level_raises(self):
        content = """# Proj
- src/
    - main.py
"""
        with self.assertRaises(ParseError):
            parse_markdown(content)

    def test_first_item_indented_raises(self):
        content = "# Proj\n  - main.py\n"
        with self.assertRaises(ParseError):
            parse_markdown(content)


class TestParserSecondHeader(unittest.TestCase):
    def test_second_header_line_raises(self):
        content = """# Proj
- src/
# OutroHeader
- README.md
"""
        with self.assertRaises(ParseError):
            parse_markdown(content)


class TestParserMissingHeader(unittest.TestCase):
    def test_file_without_header_raises(self):
        content = "- src/\n  - main.py\n"
        with self.assertRaises(ParseError):
            parse_markdown(content)

    def test_empty_file_raises(self):
        with self.assertRaises(ParseError):
            parse_markdown("")

    def test_only_whitespace_raises(self):
        with self.assertRaises(ParseError):
            parse_markdown("\n\n   \n")

    def test_header_without_name_raises(self):
        with self.assertRaises(ParseError):
            parse_markdown("#   \n- file.txt\n")

    def test_header_with_no_items_raises(self):
        with self.assertRaises(ParseError):
            parse_markdown("# Proj\n")


class TestParserMalformedItems(unittest.TestCase):
    def test_item_without_dash_prefix_raises(self):
        content = "# Proj\nsrc/\n"
        with self.assertRaises(ParseError):
            parse_markdown(content)

    def test_child_of_file_raises(self):
        content = """# Proj
- README.md
  - nested.txt
"""
        with self.assertRaises(ParseError):
            parse_markdown(content)

    def test_empty_folder_name_raises(self):
        content = "# Proj\n- /\n"
        with self.assertRaises(ParseError):
            parse_markdown(content)


if __name__ == "__main__":
    unittest.main()
