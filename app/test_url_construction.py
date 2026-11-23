import unittest

from app.url_utils import build_short_url


class BuildShortUrlTests(unittest.TestCase):
    def test_appends_generated_code_to_public_origin(self):
        self.assertEqual(
            build_short_url("https://shortly-production-9ce7640d.up.railway.app", "cRCuyR"),
            "https://shortly-production-9ce7640d.up.railway.app/cRCuyR",
        )

    def test_removes_hostname_repeated_in_configured_path(self):
        self.assertEqual(
            build_short_url(
                "https://shortly-production-9ce7640d.up.railway.app/shortly-production-9ce7640d.up.railway.app/",
                "cRCuyR",
            ),
            "https://shortly-production-9ce7640d.up.railway.app/cRCuyR",
        )

    def test_normalizes_slashes_and_preserves_base_path_and_custom_alias(self):
        self.assertEqual(
            build_short_url("https://example.com//links///", "my-alias_1"),
            "https://example.com/links/my-alias_1",
        )


if __name__ == "__main__":
    unittest.main()
