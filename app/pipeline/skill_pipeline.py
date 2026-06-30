from pathlib import Path
from typing import Dict, Any

from app.extractor.ppt_extractor import extract_ppt_text
from app.agents.psd_agent import build_psd
from app.agents.story_plan_agent import build_story_plan
from app.agents.storyboard_agent import build_storyboard
from app.agents.prompt_agent import build_video_prompts
from app.utils.file_utils import ensure_dir
from app.utils.json_utils import save_json
from app.utils.markdown_utils import save_video_prompts_markdown


def run_skill_pipeline(pptx_path: Path, output_dir: Path, provider: str = "mock") -> Dict[str, Any]:
    ensure_dir(output_dir)

    # 1. PPT 文本提取
    extracted = extract_ppt_text(pptx_path)
    extracted_path = output_dir / "extracted_slides.json"
    save_json(extracted_path, extracted)

    # 2. 生成 PPT 语义中间态 PSD
    psd = build_psd(extracted, provider=provider)
    psd_path = output_dir / "psd.json"
    save_json(psd_path, psd)

    # 3. 先理解整支介绍片的故事主线，决定讲什么、合并什么、跳过什么
    story_plan = build_story_plan(psd, provider=provider)
    story_plan_path = output_dir / "story_plan.json"
    save_json(story_plan_path, story_plan)

    # 4. 根据故事策划生成分镜脚本，不再强制一页PPT对应一个分镜
    storyboard = build_storyboard(psd, story_plan, provider=provider)
    storyboard_path = output_dir / "storyboard.json"
    save_json(storyboard_path, storyboard)

    # 5. 生成视频 Prompt
    video_prompts = build_video_prompts(storyboard, provider=provider)
    video_prompts_json_path = output_dir / "video_prompts.json"
    video_prompts_md_path = output_dir / "video_prompts.md"
    save_json(video_prompts_json_path, video_prompts)
    save_video_prompts_markdown(video_prompts_md_path, video_prompts)

    return {
        "extracted": extracted,
        "psd": psd,
        "story_plan": story_plan,
        "storyboard": storyboard,
        "video_prompts": video_prompts,
        "files": [
            str(extracted_path),
            str(psd_path),
            str(story_plan_path),
            str(storyboard_path),
            str(video_prompts_json_path),
            str(video_prompts_md_path),
        ],
    }
