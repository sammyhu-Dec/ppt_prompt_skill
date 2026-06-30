from pathlib import Path

from app.agents.base_llm import OpenAIJsonClient
from app.schemas.models import StoryboardDocument, VideoPromptDocument, VideoPromptItem
from app.utils.file_utils import read_text
from app.utils.duration_utils import normalize_duration

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "video_prompt.txt"

DEFAULT_NEGATIVE_PROMPT = "不要卡通风格，不要低清晰度，不要乱码文字，不要过度炫光，不要夸张科幻，不要画面抖动，不要人物畸形。"


def _mock_prompt(scene) -> VideoPromptItem:
    prompt = (
        f"{scene.visual_content} 画面风格为真实企业宣传片，科技感、专业可信、电影感。"
        f"镜头采用{scene.camera}，以{scene.shot_type}呈现主体细节。"
        "环境干净明亮，柔和自然光线，画面质感高级，运动平稳，细节清晰。"
    )
    return VideoPromptItem(
        scene_id=scene.scene_id,
        duration=scene.duration,
        prompt=prompt,
        negative_prompt=DEFAULT_NEGATIVE_PROMPT,
    )


def _build_prompt(scene, client: OpenAIJsonClient) -> VideoPromptItem:
    system_prompt = (
        read_text(PROMPT_PATH)
        + "\n\n本次只为一个分镜生成一个视频Prompt。只输出单个JSON对象，不要输出prompts数组。"
        + "duration必须继承输入分镜时长，并保持在2-8s之间。"
        + "顶层字段必须为 scene_id、duration、prompt、negative_prompt。"
    )
    data = client.chat_json(
        system_prompt,
        scene.model_dump(),
        expected_keys=["scene_id", "duration", "prompt", "negative_prompt"],
    )
    data["scene_id"] = scene.scene_id
    data["duration"] = normalize_duration(data.get("duration"), default=scene.duration)
    return VideoPromptItem.model_validate(data)


def build_video_prompts(storyboard: StoryboardDocument, provider: str = "mock") -> VideoPromptDocument:
    if provider == "mock":
        prompts = [_mock_prompt(scene) for scene in storyboard.scenes]
        return VideoPromptDocument(prompts=prompts)

    client = OpenAIJsonClient()
    prompts = [_build_prompt(scene, client) for scene in storyboard.scenes]
    return VideoPromptDocument(prompts=prompts)
