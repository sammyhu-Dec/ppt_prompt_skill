import re


def normalize_duration(value: object, default: str = "5s") -> str:
    text = str(value or "").strip().lower().replace("秒", "s")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return default

    seconds = round(float(match.group(1)))
    seconds = max(2, min(8, seconds))
    return f"{seconds}s"
