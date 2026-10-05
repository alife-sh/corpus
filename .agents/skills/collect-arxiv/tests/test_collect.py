import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect.py"
SPEC = importlib.util.spec_from_file_location("collect_arxiv", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)

BASE = "https://arxiv.org/html/2206.01134v2"
PDF_URL = "https://arxiv.org/pdf/2206.01134v2"
PDF = b"%PDF-1.7\nmock PDF fixture\n"
HTML = b'''<!doctype html><article class="ltx_document">
<img src="/static/logo.svg">
<figure><object data="2206.01134v2/figure1.svg"></object></figure>
<figure><img src="data:image/png;base64,AAAA"></figure>
</article>'''
SVG = b'''<svg xmlns="http://www.w3.org/2000/svg">
<image href="images/pixel.png"/><use href="#internal"/>
<a href="https://example.org/not-an-asset"><text>link</text></a>
</svg>'''
PNG = b"\x89PNG\r\n\x1a\nmock image fixture"


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.responses = {
            PDF_URL: (PDF, "application/pdf"),
            BASE: (HTML, "text/html"),
            BASE + "/figure1.svg": (SVG, "image/svg+xml"),
            BASE + "/images/pixel.png": (PNG, "image/png"),
        }

    def tearDown(self):
        self.temp.cleanup()

    def fetch(self, url):
        if url not in self.responses:
            raise HTTPError(url, 404, "Not found", {}, None)
        return self.responses[url]

    def collect(self):
        with patch.object(collector, "fetch", side_effect=self.fetch):
            return collector.Collector(BASE, self.root).run()

    def test_versioned_inputs(self):
        for value in ["2206.01134v2", "arXiv:2206.01134v2", BASE,
                      PDF_URL + ".pdf", "https://arxiv.org/abs/2206.01134v2"]:
            self.assertEqual(collector.normalize_id(value), "2206.01134v2")
        self.assertEqual(collector.normalize_id("hep-th/9901001v1"), "hep-th/9901001v1")

    def test_rejects_unversioned_and_non_arxiv_input(self):
        for value in ["2206.01134", "https://example.org/html/2206.01134v2",
                      "../../escapev2", "2206.01134v0"]:
            with self.assertRaises(ValueError):
                collector.normalize_id(value)

    def test_collects_originals_and_recursive_figures(self):
        report = self.collect()
        self.assertEqual(report["status"], "collected")
        self.assertEqual(report["gaps"], [])
        folder = Path(report["directory"])
        self.assertEqual((folder / "paper.html").read_bytes(), HTML)
        self.assertEqual((folder / "paper.pdf").read_bytes(), PDF)
        self.assertEqual((folder / "2206.01134v2/figure1.svg").read_bytes(), SVG)
        self.assertEqual((folder / "2206.01134v2/images/pixel.png").read_bytes(), PNG)
        self.assertEqual(len(report["files"]), 4)
        for item in report["files"]:
            self.assertEqual(item["sha256"], hashlib.sha256((folder / item["path"]).read_bytes()).hexdigest())
        self.assertIn("Ingestion: Not performed", (folder / "metadata.md").read_text())
        self.assertFalse((self.root / "wiki").exists())

    def test_rerun_never_overwrites_or_redownloads_existing_files(self):
        first = self.collect()
        folder = Path(first["directory"])
        before = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
        with patch.object(collector, "fetch", side_effect=AssertionError("Unexpected network request")):
            second = collector.Collector(BASE, self.root).run()
        self.assertTrue(all(item["reused"] for item in second["files"]))
        self.assertNotEqual(first["record"], second["record"])
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)

    def test_missing_html_preserves_pdf_and_reports_gap(self):
        del self.responses[BASE]
        report = self.collect()
        self.assertEqual(report["status"], "partial")
        self.assertTrue((Path(report["directory"]) / "paper.pdf").exists())
        self.assertFalse((Path(report["directory"]) / "paper.html").exists())
        self.assertTrue(any(BASE in gap for gap in report["gaps"]))

    def test_missing_figure_is_recorded(self):
        del self.responses[BASE + "/figure1.svg"]
        report = self.collect()
        self.assertEqual(report["status"], "partial")
        self.assertTrue(any("figure1.svg" in gap for gap in report["gaps"]))
        saved = json.loads(Path(report["record"]).read_text())
        self.assertEqual(saved["gaps"], report["gaps"])

    def test_abstract_or_error_page_is_not_saved_as_paper(self):
        self.responses[BASE] = (b"<html><p>Abstract or error page</p></html>", "text/html")
        report = self.collect()
        self.assertEqual(report["status"], "partial")
        self.assertFalse((Path(report["directory"]) / "paper.html").exists())

    def test_fake_pdf_is_rejected(self):
        self.responses[PDF_URL] = (b"<html>Error</html>", "text/html")
        report = self.collect()
        self.assertEqual(report["status"], "partial")
        self.assertFalse((Path(report["directory"]) / "paper.pdf").exists())

    def test_path_escape_is_rejected(self):
        self.responses[BASE] = (b'<article class="ltx_document"><figure><img src="../escape.png"></figure></article>', "text/html")
        report = self.collect()
        self.assertTrue(any("escapes paper folder" in gap for gap in report["gaps"]))
        self.assertFalse((self.root / "raw/papers/escape.png").exists())

    def test_external_host_is_not_fetched(self):
        self.responses[BASE] = (b'<article class="ltx_document"><figure><img src="https://example.org/figure.png"></figure></article>', "text/html")
        with patch.object(collector, "fetch", side_effect=self.fetch) as fetch:
            report = collector.Collector(BASE, self.root).run()
        self.assertTrue(any("External" in gap for gap in report["gaps"]))
        self.assertEqual(fetch.call_count, 2)

    def test_absolute_arxiv_asset_is_archived_with_offline_gap(self):
        url = "https://arxiv.org/html/2206.01134v2/figure.svg"
        self.responses[BASE] = (f'<article class="ltx_document"><figure><object data="{url}"></object></figure></article>'.encode(), "text/html")
        self.responses[url] = (b'<svg xmlns="http://www.w3.org/2000/svg"/>', "image/svg+xml")
        report = self.collect()
        self.assertEqual(report["status"], "partial")
        asset = next(item for item in report["files"] if item["url"] == url)
        self.assertTrue(asset["path"].startswith("assets/external/"))
        self.assertTrue(any("non-local" in gap for gap in report["gaps"]))

    def test_css_dependencies(self):
        self.responses[BASE + "/figure1.svg"] = (
            b'<svg xmlns="http://www.w3.org/2000/svg"><style>@import "styles.css";</style></svg>', "image/svg+xml")
        self.responses[BASE + "/styles.css"] = (b".figure { background: url(images/pixel.png) }", "text/css")
        report = self.collect()
        self.assertEqual(report["gaps"], [])
        self.assertTrue(any(item["path"].endswith("styles.css") for item in report["files"]))

    def test_base_element_is_reported(self):
        self.responses[BASE] = (b'<base href="https://arxiv.org/html/"><article class="ltx_document"></article>', "text/html")
        report = self.collect()
        self.assertTrue(any("base element" in gap for gap in report["gaps"]))

    def test_mixed_embedded_and_external_srcset(self):
        self.responses[BASE] = (
            b'<article class="ltx_document"><figure><img srcset="data:image/png;base64,AAAA 1x, image.png 2x"></figure></article>',
            "text/html")
        self.responses["https://arxiv.org/html/image.png"] = (PNG, "image/png")
        report = self.collect()
        self.assertEqual(report["gaps"], [])
        self.assertTrue(any(item["path"] == "image.png" for item in report["files"]))

    def test_svg_dependency_cycle_terminates(self):
        self.responses[BASE + "/figure1.svg"] = (
            b'<svg xmlns="http://www.w3.org/2000/svg"><use href="figure1.svg#part"/></svg>',
            "image/svg+xml")
        report = self.collect()
        self.assertEqual(report["gaps"], [])
        self.assertEqual(len(report["files"]), 3)

    def test_invalid_existing_source_is_preserved(self):
        folder = self.root / "raw/papers/2206.01134v2"
        folder.mkdir(parents=True)
        existing = folder / "paper.pdf"
        existing.write_bytes(b"do not replace this file")
        report = self.collect()
        self.assertEqual(report["status"], "partial")
        self.assertEqual(existing.read_bytes(), b"do not replace this file")

    def test_legacy_id_folder(self):
        instance = collector.Collector("hep-th/9901001v1", self.root)
        self.assertEqual(instance.folder.name, "hep-th-9901001v1")

    def test_rejects_dangerous_redirects(self):
        handler = collector.ArxivRedirects()
        for url in ["http://arxiv.org/figure.svg", "https://example.org/figure.svg", "https://arxiv.org:8080/figure.svg"]:
            with self.assertRaises(ValueError):
                handler.redirect_request(None, None, 302, "redirect", {}, url)


if __name__ == "__main__":
    unittest.main()
