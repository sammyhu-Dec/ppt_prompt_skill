from pathlib import Path

from app.schemas.models import VideoPromptDocument
from app.utils.file_utils import write_text


def save_video_prompts_markdown(path: Path, doc: VideoPromptDocument) -> None:
    lines = ["# 视频分镜 Prompt", ""]

    for item in doc.prompts:
        lines.append(f"## 分镜 {item.scene_id}")
        lines.append("")
        lines.append(f"**时长：** {item.duration}")
        lines.append("")
        lines.append("**Prompt：**")
        lines.append("")
        lines.append(item.prompt.strip())
        lines.append("")

        if item.negative_prompt:
            lines.append("**Negative Prompt：**")
            lines.append("")
            lines.append(item.negative_prompt.strip())
            lines.append("")

        lines.append("---")
        lines.append("")

    write_text(path, "\n".join(lines))
