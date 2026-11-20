import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_x_index as archive


class URLPolicyTests(unittest.TestCase):
    def test_stable_routes_allow_product_numbers(self):
        for route in ("cloudflare-net-investment/", "http2/", "layer-7/index.html"):
            archive.validate_route(route)

    def test_rejects_dates_and_non_english_slugs(self):
        for route in (
            "report-2026-11-18/", "2026/11/18/report.html", "report-2026/",
            "report-20261118/", "report-202611/", "报告/", "Report/",
        ):
            with self.subTest(route=route), self.assertRaises(ValueError):
                archive.validate_route(route)

    def test_build_lists_only_stable_pages_and_generates_redirects(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / "static/x", root / "public"
            (source / "report").mkdir(parents=True)
            (source / "report/index.html").write_text(
                '<head><title>Report</title><meta name="date" content="2026-11-18"></head>'
                '<body>Report dated 2026-11-18</body>', encoding="utf-8"
            )
            (output / "x").mkdir(parents=True)
            (output / "x/index.html").write_text('{"archivePages":[]}', encoding="utf-8")
            with patch.object(archive, "ARCHIVE", source), patch.object(
                archive, "REDIRECTS", {"report-2026-11-18": "report"}
            ):
                archive.main(output)
                pages = json.loads((output / "x/index.html").read_text())["archivePages"]
                self.assertEqual([p["path"] for p in pages], ["/x/report/"])
                self.assertEqual(pages[0]["date"], "2026-11-18")
                redirect = (output / "x/report-2026-11-18/index.html").read_text()
                self.assertIn('href="/x/report/"', redirect)
                self.assertIn("location.search + location.hash", redirect)
                self.assertIn('content="noindex"', redirect)
                (source / "bad-2026").mkdir()
                (source / "bad-2026/index.html").write_text("<title>Bad</title>")
                with self.assertRaisesRegex(ValueError, "Dates are not allowed"):
                    archive.main(output)


if __name__ == "__main__":
    unittest.main()
