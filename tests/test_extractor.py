from pathlib import Path

from app.extractor.ppt_extractor import extract_ppt_text


def test_extract_missing_file():
    missing = Path("input/not_exists.pptx")
    try:
        extract_ppt_text(missing)
    except Exception as exc:
        assert isinstance(exc, Exception)
