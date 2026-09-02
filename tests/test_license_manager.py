"""
Testes automatizados para src/license_manager.py

Todos os testes usam mocks para simular respostas de rede — nenhum
teste depende de acesso real à internet.

Executar com:
    python -m unittest tests.test_license_manager -v
"""

import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import license_manager as lm  # noqa: E402


def make_json_response(payload: dict) -> MagicMock:
    """
    Cria um objeto mock que se comporta como o retorno de
    urllib.request.urlopen usado em um bloco `with`.
    """
    body = json.dumps(payload).encode("utf-8")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = body
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return mock_response


class TestListAvailableLicenses(unittest.TestCase):
    def test_returns_expected_labels_and_ids(self):
        licenses = lm.list_available_licenses()

        self.assertEqual(licenses["MIT"], "MIT")
        self.assertEqual(licenses["Apache License 2.0"], "Apache-2.0")
        self.assertEqual(licenses["GNU GPLv2"], "GPL-2.0-only")
        self.assertEqual(licenses["GNU GPLv3"], "GPL-3.0-only")
        self.assertEqual(licenses["BSD 3-Clause"], "BSD-3-Clause")
        self.assertEqual(licenses["The Unlicense"], "Unlicense")

    def test_returns_a_copy_not_the_internal_dict(self):
        licenses = lm.list_available_licenses()
        licenses["Hacked"] = "NotReal"
        self.assertNotIn("Hacked", lm.list_available_licenses())


class TestFetchValidResponse(unittest.TestCase):
    @patch("license_manager.urllib.request.urlopen")
    def test_valid_response_returns_license_text(self, mock_urlopen):
        mock_urlopen.return_value = make_json_response(
            {"licenseId": "MIT", "licenseText": "MIT License text here"}
        )

        result = lm.get_license_text("MIT")

        self.assertEqual(result.spdx_id, "MIT")
        self.assertEqual(result.text, "MIT License text here")
        self.assertFalse(result.from_cache)

    @patch("license_manager.urllib.request.urlopen")
    def test_request_url_is_built_from_allowed_id_only(self, mock_urlopen):
        mock_urlopen.return_value = make_json_response(
            {"licenseId": "Apache-2.0", "licenseText": "Apache text"}
        )

        lm.get_license_text("Apache-2.0")

        called_request = mock_urlopen.call_args[0][0]
        self.assertEqual(
            called_request.full_url,
            "https://spdx.org/licenses/Apache-2.0.json",
        )


class TestFetchNonExistentLicense(unittest.TestCase):
    def test_unknown_spdx_id_is_rejected_before_any_request(self):
        with patch("license_manager.urllib.request.urlopen") as mock_urlopen:
            with self.assertRaises(lm.LicenseError):
                lm.get_license_text("TotallyMadeUpLicense-9000")
            mock_urlopen.assert_not_called()

    def test_arbitrary_url_like_id_is_rejected(self):
        with patch("license_manager.urllib.request.urlopen") as mock_urlopen:
            with self.assertRaises(lm.LicenseError):
                lm.get_license_text("http://evil.example.com/payload")
            mock_urlopen.assert_not_called()


class TestFetchTimeout(unittest.TestCase):
    @patch("license_manager.urllib.request.urlopen")
    def test_timeout_raises_license_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")

        with self.assertRaises(lm.LicenseError) as ctx:
            lm.get_license_text("MIT")

        self.assertIn("MIT", str(ctx.exception))

    @patch("license_manager.urllib.request.urlopen")
    def test_urlerror_from_timeout_raises_license_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("timed out")

        with self.assertRaises(lm.LicenseError):
            lm.get_license_text("MIT")


class TestFetchHttpError(unittest.TestCase):
    @patch("license_manager.urllib.request.urlopen")
    def test_http_404_raises_license_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://spdx.org/licenses/MIT.json",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

        with self.assertRaises(lm.LicenseError) as ctx:
            lm.get_license_text("MIT")

        self.assertIn("MIT", str(ctx.exception))

    @patch("license_manager.urllib.request.urlopen")
    def test_network_unreachable_raises_license_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(
            "Network is unreachable"
        )

        with self.assertRaises(lm.LicenseError):
            lm.get_license_text("Apache-2.0")

    @patch("license_manager.urllib.request.urlopen")
    def test_invalid_json_raises_license_error(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"not valid json {{{"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        mock_urlopen.return_value = mock_response

        with self.assertRaises(lm.LicenseError):
            lm.get_license_text("MIT")

    @patch("license_manager.urllib.request.urlopen")
    def test_missing_license_text_field_raises_license_error(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = make_json_response(
            {"licenseId": "MIT"}  # sem "licenseText"
        )

        with self.assertRaises(lm.LicenseError):
            lm.get_license_text("MIT")


class TestCacheExisting(unittest.TestCase):
    def test_cached_text_is_used_without_network_call(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = Path(tmp_dir)
            (cache_dir / "MIT.txt").write_text(
                "cached MIT text", encoding="utf-8"
            )

            with patch(
                "license_manager.urllib.request.urlopen"
            ) as mock_urlopen:
                result = lm.get_license_text("MIT", cache_dir=cache_dir)

            self.assertEqual(result.text, "cached MIT text")
            self.assertTrue(result.from_cache)
            mock_urlopen.assert_not_called()


class TestCacheMissing(unittest.TestCase):
    def test_missing_cache_falls_back_to_network_and_saves_cache(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = Path(tmp_dir) / "licenses"

            with patch(
                "license_manager.urllib.request.urlopen"
            ) as mock_urlopen:
                mock_urlopen.return_value = make_json_response(
                    {"licenseId": "MIT", "licenseText": "fresh MIT text"}
                )
                result = lm.get_license_text("MIT", cache_dir=cache_dir)

            self.assertEqual(result.text, "fresh MIT text")
            self.assertFalse(result.from_cache)

            cached_file = cache_dir / "MIT.txt"
            self.assertTrue(cached_file.is_file())
            self.assertEqual(
                cached_file.read_text(encoding="utf-8"), "fresh MIT text"
            )


class TestCacheWriteFailure(unittest.TestCase):
    @patch("license_manager.Path.mkdir")
    def test_cache_write_failure_does_not_break_license_fetch(
        self, mock_mkdir
    ):
        mock_mkdir.side_effect = OSError("disk full")

        with patch("license_manager.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = make_json_response(
                {"licenseId": "MIT", "licenseText": "MIT text despite cache fail"}
            )
            result = lm.get_license_text(
                "MIT", cache_dir=Path("/some/unwritable/dir")
            )

        self.assertEqual(result.text, "MIT text despite cache fail")
        self.assertFalse(result.from_cache)


class TestRenderLicenseText(unittest.TestCase):
    def test_replaces_year_marker_when_present(self):
        raw = "Copyright (c) <year> <copyright holders>"
        rendered = lm.render_license_text(raw, author="Lucas", year="2026")
        self.assertIn("2026", rendered)
        self.assertIn("Lucas", rendered)
        self.assertNotIn("<year>", rendered)
        self.assertNotIn("<copyright holders>", rendered)

    def test_uses_current_year_when_not_provided(self):
        from datetime import datetime, timezone

        raw = "Copyright (c) <year> Someone"
        rendered = lm.render_license_text(raw, author=None, year=None)
        expected_year = str(datetime.now(timezone.utc).year)
        self.assertIn(expected_year, rendered)

    def test_does_not_alter_text_without_placeholders(self):
        raw = "This is free and unencumbered software..."
        rendered = lm.render_license_text(raw, author="Lucas", year="2026")
        self.assertEqual(rendered, raw)

    def test_author_marker_untouched_when_no_author_given(self):
        raw = "Copyright (c) <year> <copyright holders>"
        rendered = lm.render_license_text(raw, author=None, year="2026")
        self.assertIn("<copyright holders>", rendered)
        self.assertNotIn("<year>", rendered)


class TestGenerateLicenseFileNoLicenseOption(unittest.TestCase):
    def test_no_license_option_means_caller_never_invokes_generation(self):
        # "Sem licença" é tratado inteiramente na camada de CLI: o
        # license_manager nunca é chamado nesse caso. Aqui garantimos
        # que não existe nenhum SPDX ID reservado para essa opção.
        self.assertNotIn("Sem licença", lm.SUPPORTED_LICENSES)
        self.assertNotIn("None", lm.ALLOWED_SPDX_IDS)


class TestGenerateLicenseFileCreation(unittest.TestCase):
    @patch("license_manager.urllib.request.urlopen")
    def test_creates_license_file_with_rendered_content(self, mock_urlopen):
        mock_urlopen.return_value = make_json_response(
            {
                "licenseId": "MIT",
                "licenseText": "MIT License\n\nCopyright (c) <year> <copyright holders>\n",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "Proj"
            project_dir.mkdir()

            license_path = lm.generate_license_file(
                "MIT",
                destination_dir=project_dir,
                author="Lucas",
                year="2026",
            )

            self.assertEqual(license_path, project_dir / "LICENSE")
            content = license_path.read_text(encoding="utf-8")
            self.assertIn("2026", content)
            self.assertIn("Lucas", content)


class TestGenerateLicenseFileExisting(unittest.TestCase):
    @patch("license_manager.urllib.request.urlopen")
    def test_existing_license_without_confirmation_is_kept(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = make_json_response(
            {"licenseId": "MIT", "licenseText": "new MIT text"}
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "Proj"
            project_dir.mkdir()
            existing = project_dir / "LICENSE"
            existing.write_text("original content", encoding="utf-8")

            result = lm.generate_license_file(
                "MIT", destination_dir=project_dir
            )

            self.assertIsNone(result)
            self.assertEqual(
                existing.read_text(encoding="utf-8"), "original content"
            )

    @patch("license_manager.urllib.request.urlopen")
    def test_existing_license_declined_via_confirm_callback(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = make_json_response(
            {"licenseId": "MIT", "licenseText": "new MIT text"}
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "Proj"
            project_dir.mkdir()
            existing = project_dir / "LICENSE"
            existing.write_text("keep me", encoding="utf-8")

            result = lm.generate_license_file(
                "MIT",
                destination_dir=project_dir,
                confirm_overwrite=lambda _p: False,
            )

            self.assertIsNone(result)
            self.assertEqual(
                existing.read_text(encoding="utf-8"), "keep me"
            )

    @patch("license_manager.urllib.request.urlopen")
    def test_existing_license_overwrite_confirmed(self, mock_urlopen):
        mock_urlopen.return_value = make_json_response(
            {"licenseId": "MIT", "licenseText": "brand new MIT text"}
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "Proj"
            project_dir.mkdir()
            existing = project_dir / "LICENSE"
            existing.write_text("old content", encoding="utf-8")

            result = lm.generate_license_file(
                "MIT",
                destination_dir=project_dir,
                confirm_overwrite=lambda _p: True,
            )

            self.assertEqual(result, existing)
            self.assertEqual(
                existing.read_text(encoding="utf-8"), "brand new MIT text"
            )


class TestGenerateLicenseFileFetchFailureLeavesNoFile(unittest.TestCase):
    @patch("license_manager.urllib.request.urlopen")
    def test_fetch_failure_does_not_create_partial_license(
        self, mock_urlopen
    ):
        mock_urlopen.side_effect = urllib.error.URLError("no network")

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "Proj"
            project_dir.mkdir()

            with self.assertRaises(lm.LicenseError):
                lm.generate_license_file("MIT", destination_dir=project_dir)

            self.assertFalse((project_dir / "LICENSE").exists())


class TestNoUnauthorizedUrls(unittest.TestCase):
    @patch("license_manager.urllib.request.urlopen")
    def test_only_spdx_org_licenses_urls_are_ever_requested(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = make_json_response(
            {"licenseId": "GPL-3.0-only", "licenseText": "GPLv3 text"}
        )

        for spdx_id in lm.ALLOWED_SPDX_IDS:
            mock_urlopen.reset_mock()
            mock_urlopen.return_value = make_json_response(
                {"licenseId": spdx_id, "licenseText": f"{spdx_id} text"}
            )
            lm.get_license_text(spdx_id)

            called_request = mock_urlopen.call_args[0][0]
            self.assertTrue(
                called_request.full_url.startswith(
                    "https://spdx.org/licenses/"
                )
            )
            self.assertTrue(called_request.full_url.endswith(".json"))

    def test_disallowed_id_never_reaches_urlopen(self):
        with patch("license_manager.urllib.request.urlopen") as mock_urlopen:
            with self.assertRaises(lm.LicenseError):
                lm.get_license_text("../../etc/passwd")
            mock_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
