import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.utils.file_utils import ensure_dir


def to_plain_data(data: Any):
    if isinstance(data, BaseModel):
        return data.model_dump()
    if isinstance(data, list):
        return [to_plain_data(item) for item in data]
    if isinstance(data, dict):
        return {key: to_plain_data(value) for key, value in data.items()}
    return data


def save_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(to_plain_data(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
