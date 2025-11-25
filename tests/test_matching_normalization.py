import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.utils.matching_normalization import normalize_domain


def test_normalize_domain_preserves_non_www_prefixes() -> None:
    assert normalize_domain("welt.de") == "welt.de"
    assert normalize_domain("wework.com") == "wework.com"


def test_normalize_domain_strips_www_prefix() -> None:
    assert normalize_domain("www.example.com") == "example.com"
    assert normalize_domain("https://www.example.com/path") == "example.com"
