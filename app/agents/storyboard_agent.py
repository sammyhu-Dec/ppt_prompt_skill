from pathlib import Path

from app.agents.base_llm import OpenAIJsonClient
from app.schemas.models import PresentationSemanticDocument, StoryPlanDocument, StoryPlanSegment, StoryboardDocument, StoryboardScene
from app.utils.file_utils import read_text
from app.utils.duration_utils import normalize_duration

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "storyboard_prompt.txt"


def _slides_by_page(psd: PresentationSemanticDocument) -> dict[int, object]:
    return {slide.page: slide for slide in psd.slides}


def _mock_scene(segment: StoryPlanSegment) -> StoryboardScene:
    return StoryboardScene(
        scene_id=segment.segment_id,
        source_slides=segment.source_slides,
        duration=segment.duration,
        scene_goal=segment.story_role,
        visual_content=segment.visual_strategy,
        camera="根据内容节奏使用平稳推进、轻微横移或快速过渡镜头。",
        shot_type="核心段落用中景与特写结合，过渡段落用短镜头建立信息。",
        transition="柔和转场，必要时使用节奏性剪辑。",
        subtitle=segment.title,
        voiceover=segment.key_message,
    )


def _build_scene(segment: StoryPlanSegment, psd: PresentationSemanticDocument, client: OpenAIJsonClient) -> StoryboardScene:
    slide_map = _slides_by_page(psd)
    source_slides = [slide_map[p].model_dump() for p in segment.source_slides if p in slide_map]
    system_prompt = (
        read_text(PROMPT_PATH)
        + "\n\n本次只根据一个故事段落生成一个分镜。不要机械复述PPT页内容，要服务整条叙事。"
        + "必须尊重 story_segment.duration，最终duration必须在2-8s之间，可根据2s/3s/4s/5s/6s/7s/8s写出对应节奏。"
        + "只输出单个分镜JSON对象，不要输出scenes数组。"
    )
    payload = {
        "deck_title": psd.deck_title,
        "core_message": psd.core_message,
        "target_style": psd.target_style,
        "story_segment": segment.model_dump(),
        "source_slide_details": source_slides,
    }
    data = client.chat_json(
        system_prompt,
        payload,
        expected_keys=["scene_id", "source_slides", "duration", "scene_goal", "visual_content", "camera", "shot_type", "transition"],
    )
    data["scene_id"] = segment.segment_id
    data["source_slides"] = data.get("source_slides") or segment.source_slides
    data["duration"] = normalize_duration(data.get("duration"), default=segment.duration)
    return StoryboardScene.model_validate(data)


def build_storyboard(
    psd: PresentationSemanticDocument,
    story_plan: StoryPlanDocument,
    provider: str = "mock",
) -> StoryboardDocument:
    if provider == "mock":
        return StoryboardDocument(scenes=[_mock_scene(segment) for segment in story_plan.segments])

    client = OpenAIJsonClient()
    scenes = [_build_scene(segment, psd, client) for segment in story_plan.segments]
    return StoryboardDocument(scenes=scenes)
