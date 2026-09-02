"""
Testes automatizados para a biblioteca de templates em templates/.

Garantem que:
    * Existe pelo menos um número mínimo de templates na biblioteca.
    * TODOS os arquivos .md em templates/ (incluindo subpastas de
      categoria) podem ser parseados com sucesso pelo parser real do
      FolderGEN.
    * TODOS os templates passam na validação de segurança/estrutura.
    * As categorias esperadas existem e contêm pelo menos um template.
    * Nenhum arquivo de template está vazio ou malformado.

Executar com:
    python -m unittest tests.test_templates -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parser import ParseError, parse_markdown  # noqa: E402
from validator import ValidationError, validate_tree  # noqa: E402


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

EXPECTED_CATEGORIES = [
    "python",
    "javascript",
    "typescript",
    "web",
    "dotnet",
    "java",
    "mobile",
    "game",
    "data",
    "devops",
    "embedded",
    "other",
]

# Número mínimo de templates que a biblioteca deve conter no total.
MINIMUM_TEMPLATE_COUNT = 50


def _all_template_files() -> list[Path]:
    return sorted(TEMPLATES_DIR.rglob("*.md"))


class TestTemplateLibrarySize(unittest.TestCase):
    def test_at_least_minimum_number_of_templates_exist(self):
        templates = _all_template_files()
        self.assertGreaterEqual(
            len(templates),
            MINIMUM_TEMPLATE_COUNT,
            f"Esperava pelo menos {MINIMUM_TEMPLATE_COUNT} templates, "
            f"encontrados {len(templates)}.",
        )


class TestTemplateCategoriesExist(unittest.TestCase):
    def test_each_expected_category_directory_exists(self):
        for category in EXPECTED_CATEGORIES:
            category_dir = TEMPLATES_DIR / category
            self.assertTrue(
                category_dir.is_dir(),
                f"Categoria esperada '{category}' não encontrada em "
                f"'{TEMPLATES_DIR}'.",
            )

    def test_each_category_has_at_least_one_template(self):
        for category in EXPECTED_CATEGORIES:
            category_dir = TEMPLATES_DIR / category
            templates_in_category = list(category_dir.glob("*.md"))
            self.assertGreaterEqual(
                len(templates_in_category),
                1,
                f"Categoria '{category}' não possui nenhum template .md.",
            )


class TestAllTemplatesAreParseable(unittest.TestCase):
    """
    Um teste é gerado dinamicamente para cada arquivo .md encontrado em
    templates/, garantindo que falhas apontem exatamente para o
    template problemático (em vez de um único teste genérico que só
    diz "algum template falhou").
    """


def _make_parse_test(template_path: Path):
    def test(self):
        content = template_path.read_text(encoding="utf-8")
        try:
            tree = parse_markdown(content)
        except ParseError as exc:
            self.fail(
                f"Falha ao parsear '{template_path}': {exc}"
            )
        self.assertEqual(tree.type, "folder")
        self.assertTrue(
            tree.name, f"Template '{template_path}' tem nome de raiz vazio."
        )

    return test


def _make_validate_test(template_path: Path):
    def test(self):
        content = template_path.read_text(encoding="utf-8")
        tree = parse_markdown(content)
        try:
            validate_tree(tree)
        except ValidationError as exc:
            self.fail(
                f"Falha ao validar '{template_path}': {exc}"
            )

    return test


# Registra dinamicamente um teste de parse e um de validação para cada
# arquivo de template encontrado no momento em que este módulo é
# carregado.
for _template_path in _all_template_files():
    _relative = _template_path.relative_to(TEMPLATES_DIR)
    _safe_name = str(_relative).replace("/", "_").replace(".", "_").replace("-", "_")

    setattr(
        TestAllTemplatesAreParseable,
        f"test_parse_{_safe_name}",
        _make_parse_test(_template_path),
    )
    setattr(
        TestAllTemplatesAreParseable,
        f"test_validate_{_safe_name}",
        _make_validate_test(_template_path),
    )


class TestTemplatesAreNotEmpty(unittest.TestCase):
    def test_no_template_file_is_empty(self):
        for template_path in _all_template_files():
            content = template_path.read_text(encoding="utf-8")
            self.assertTrue(
                content.strip(),
                f"Template '{template_path}' está vazio.",
            )

    def test_every_template_has_at_least_one_item_besides_root(self):
        for template_path in _all_template_files():
            content = template_path.read_text(encoding="utf-8")
            tree = parse_markdown(content)
            self.assertGreater(
                len(tree.children),
                0,
                f"Template '{template_path}' não possui itens além da "
                "pasta raiz.",
            )


class TestLegacyTemplateStillWorks(unittest.TestCase):
    """
    Garante que o template legado usado antes da biblioteca por
    categorias (templates/python_basic.md) continua funcionando, para
    não quebrar quem já dependia dele.
    """

    def test_python_basic_template_still_parses(self):
        legacy_path = TEMPLATES_DIR / "python_basic.md"
        self.assertTrue(
            legacy_path.is_file(),
            "templates/python_basic.md não deveria ter sido removido.",
        )
        content = legacy_path.read_text(encoding="utf-8")
        tree = parse_markdown(content)
        validate_tree(tree)
        self.assertEqual(tree.name, "MeuProjeto")


if __name__ == "__main__":
    unittest.main()
