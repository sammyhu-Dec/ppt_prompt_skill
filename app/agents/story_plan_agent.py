from pathlib import Path

from app.agents.base_llm import OpenAIJsonClient
from app.schemas.models import PresentationSemanticDocument, StoryPlanDocument, StoryPlanSegment
from app.utils.file_utils import read_text
from app.utils.duration_utils import normalize_duration

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "story_plan_prompt.txt"


def _mock_story_plan(psd: PresentationSemanticDocument) -> StoryPlanDocument:
    segments = []
    selected = []
    skipped = []

    for slide in psd.slides:
        if slide.slide_type in {"agenda", "other"} and len(slide.raw_text) > 600:
            skipped.append(slide.page)
            continue

        selected.append(slide.page)
        duration = "3s" if slide.slide_type in {"cover", "summary"} else "5s"
        segments.append(
            StoryPlanSegment(
                segment_id=len(segments) + 1,
                source_slides=[slide.page],
                title=slide.title,
                key_message="、".join(slide.key_points[:3]),
                story_role=slide.narrative_role,
                include_reason="保留该页的核心叙事信息。",
                visual_strategy=slide.visual_direction,
                duration=duration,
            )
        )

    return StoryPlanDocument(
        story_title=psd.deck_title,
        narrative_arc=psd.core_message,
        target_total_duration="60-90s",
        selected_slides=selected,
        skipped_slides=skipped,
        skip_reason="略过信息过密或不适合视频逐条表达的页面。" if skipped else "",
        segments=segments,
    )


def _normalize_story_plan(data: dict) -> dict:
    segments = data.get("segments") or []
    for idx, segment in enumerate(segments, start=1):
        segment["segment_id"] = idx
        segment["duration"] = normalize_duration(segment.get("duration"), default="5s")
        if not segment.get("source_slides"):
            segment["source_slides"] = []
    data["segments"] = segments
    data["selected_slides"] = data.get("selected_slides") or sorted({p for s in segments for p in s.get("source_slides", [])})
    data["skipped_slides"] = data.get("skipped_slides") or []
    return data


def build_story_plan(psd: PresentationSemanticDocument, provider: str = "mock") -> StoryPlanDocument:
    if provider == "mock":
        return _mock_story_plan(psd)

    client = OpenAIJsonClient()
    data = client.chat_json(
        read_text(PROMPT_PATH),
        psd.model_dump(),
        expected_keys=["story_title", "narrative_arc", "target_total_duration", "selected_slides", "skipped_slides", "segments"],
    )
    return StoryPlanDocument.model_validate(_normalize_story_plan(data))
