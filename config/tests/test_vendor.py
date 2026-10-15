"""Die vendorten Frontend-Bibliotheken passen zu ihrem Vermerk (#501)."""

import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

JS_VERZEICHNIS: Path = Path(settings.BASE_DIR) / "static" / "js"
PRUEFSUMMENZEILE: re.Pattern[str] = re.compile(
    r"^([0-9a-f]{64})  (\S+\.js)$", re.MULTILINE
)


class VendorVermerkTests(SimpleTestCase):
    """static/js/VENDOR.md hält die Prüfsumme jeder vendorten Datei fest."""

    def test_vendorte_dateien_passen_zur_pruefsumme_im_vermerk(self) -> None:
        """Eine still ersetzte Datei fällt an der SHA-256 auf."""
        vermerk: str = (JS_VERZEICHNIS / "VENDOR.md").read_text(encoding="utf-8")
        pruefsummen: dict[str, str] = {
            datei: summe for summe, datei in PRUEFSUMMENZEILE.findall(vermerk)
        }

        self.assertEqual(set(pruefsummen), {"htmx.min.js", "alpine.min.js"})
        for datei, summe in pruefsummen.items():
            with self.subTest(datei=datei):
                inhalt: bytes = (JS_VERZEICHNIS / datei).read_bytes()
                self.assertEqual(hashlib.sha256(inhalt).hexdigest(), summe)
