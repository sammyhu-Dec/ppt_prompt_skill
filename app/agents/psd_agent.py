from pathlib import Path

from app.agents.base_llm import OpenAIJsonClient
from app.schemas.models import ExtractedDeck, PresentationSemanticDocument, SlideSemantic
from app.utils.file_utils import read_text

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "psd_prompt.txt"


def _guess_slide_type(title: str, raw_text: str) -> str:
    text = f"{title}\n{raw_text}".lower()
    if any(k in text for k in ["目录", "contents", "agenda"]):
        return "agenda"
    if any(k in text for k in ["公司", "介绍", "about"]):
        return "company_intro"
    if any(k in text for k in ["产品", "芯片", "模组", "开发板", "终端"]):
        return "product"
    if any(k in text for k in ["技术", "架构", "risc-v", "ai"]):
        return "technology"
    if any(k in text for k in ["应用", "场景", "智慧", "物流", "能源", "工厂", "城市"]):
        return "application"
    if any(k in text for k in ["谢谢", "总结", "愿景"]):
        return "summary"
    return "cover" if len(raw_text) < 80 else "other"


def _mock_slide_semantic(slide) -> SlideSemantic:
    slide_type = _guess_slide_type(slide.title, slide.raw_text)
    raw_lines = [line.strip() for line in slide.raw_text.splitlines() if line.strip()]
    key_points = raw_lines[:5] if raw_lines else [slide.title]

    return SlideSemantic(
        page=slide.page,
        slide_type=slide_type,
        title=slide.title or f"第{slide.page}页",
        raw_text=slide.raw_text,
        key_points=key_points,
        narrative_role=f"用于说明{slide.title or '该页面核心信息'}",
        visual_direction="采用真实企业宣传片画面表达，结合办公空间、研发实验室、产品特写或行业应用场景。",
    )


def _mock_psd(extracted: ExtractedDeck) -> PresentationSemanticDocument:
    slides = [_mock_slide_semantic(slide) for slide in extracted.slides]
    return PresentationSemanticDocument(
        deck_title=extracted.slides[0].title if extracted.slides else extracted.file_name,
        deck_type="企业介绍PPT",
        core_message="根据PPT内容提炼企业定位、产品能力和应用场景。",
        target_style="真实企业宣传片，科技感，专业可信，电影感，柔和光线，平稳镜头。",
        slides=slides,
    )


def _build_deck_summary(extracted: ExtractedDeck, client: OpenAIJsonClient) -> dict:
    payload = {
        "file_name": extracted.file_name,
        "slide_count": extracted.slide_count,
        "slide_titles": [slide.title for slide in extracted.slides],
    }
    system_prompt = (
        "你是一名企业宣传片策划专家。请根据PPT标题列表概括整份PPT。"
        "只输出JSON对象，字段必须为 deck_title、deck_type、core_message、target_style。"
    )
    return client.chat_json(
        system_prompt,
        payload,
        expected_keys=["deck_title", "deck_type", "core_message", "target_style"],
    )


def _build_slide_semantic(slide, deck_summary: dict, client: OpenAIJsonClient) -> SlideSemantic:
    system_prompt = (
        read_text(PROMPT_PATH)
        + "\n\n本次只处理一页PPT。只输出单页语义JSON对象，不要输出整份slides数组。"
        + "顶层字段必须为 page、slide_type、title、raw_text、key_points、narrative_role、visual_direction。"
    )
    payload = {
        "deck_summary": deck_summary,
        "slide": slide.model_dump(),
    }
    data = client.chat_json(
        system_prompt,
        payload,
        expected_keys=["page", "slide_type", "title", "raw_text", "key_points", "narrative_role", "visual_direction"],
    )
    data["page"] = slide.page
    data["raw_text"] = data.get("raw_text") or slide.raw_text
    return SlideSemantic.model_validate(data)


def build_psd(extracted: ExtractedDeck, provider: str = "mock") -> PresentationSemanticDocument:
    if provider == "mock":
        return _mock_psd(extracted)

    client = OpenAIJsonClient()
    deck_summary = _build_deck_summary(extracted, client)
    slides = [_build_slide_semantic(slide, deck_summary, client) for slide in extracted.slides]

    return PresentationSemanticDocument(
        deck_title=deck_summary["deck_title"],
        deck_type=deck_summary["deck_type"],
        core_message=deck_summary["core_message"],
        target_style=deck_summary["target_style"],
        slides=slides,
    )
