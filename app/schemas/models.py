from typing import List, Optional
from pydantic import BaseModel, Field


class SlideExtracted(BaseModel):
    page: int = Field(..., description="PPT页码，从1开始")
    title: str = Field(default="", description="页面标题，第一版中取页面首段文本")
    raw_text: str = Field(default="", description="页面全部文本")
    image_count: int = Field(default=0, description="页面图片数量")
    notes: str = Field(default="", description="演讲者备注，第一版可为空")


class ExtractedDeck(BaseModel):
    file_name: str
    slide_count: int
    slides: List[SlideExtracted]


class SlideSemantic(BaseModel):
    page: int
    slide_type: str = Field(..., description="cover/company_intro/product/technology/application/summary/other")
    title: str
    raw_text: str
    key_points: List[str]
    narrative_role: str = Field(..., description="这一页在视频叙事中的作用")
    visual_direction: str = Field(..., description="这一页适合被视频化表达成什么画面")


class PresentationSemanticDocument(BaseModel):
    deck_title: str
    deck_type: str
    core_message: str
    target_style: str
    slides: List[SlideSemantic]


class StoryPlanSegment(BaseModel):
    segment_id: int
    source_slides: List[int] = Field(default_factory=list, description="这个故事段落参考的PPT页码，可以是一页、多页或空")
    title: str
    key_message: str
    story_role: str = Field(..., description="该段在整条叙事中的作用")
    include_reason: str = Field(..., description="为什么要讲这一段")
    visual_strategy: str = Field(..., description="这一段适合用什么视频画面表达")
    duration: str = Field(default="5s", description="建议时长，范围约2-8s，例如2s/3s/5s/8s")


class StoryPlanDocument(BaseModel):
    story_title: str
    narrative_arc: str = Field(..., description="整支视频的叙事主线")
    target_total_duration: str = Field(default="60-90s")
    selected_slides: List[int] = Field(default_factory=list)
    skipped_slides: List[int] = Field(default_factory=list)
    skip_reason: str = ""
    segments: List[StoryPlanSegment]


class StoryboardScene(BaseModel):
    scene_id: int
    source_slides: List[int]
    duration: str = Field(default="5s", description="分镜时长，范围约2-8s，继承story_plan节奏")
    scene_goal: str
    visual_content: str
    camera: str
    shot_type: str
    transition: str
    subtitle: Optional[str] = None
    voiceover: Optional[str] = None


class StoryboardDocument(BaseModel):
    scenes: List[StoryboardScene]


class VideoPromptItem(BaseModel):
    scene_id: int
    duration: str = Field(..., description="视频prompt时长，范围约2-8s，继承storyboard分镜时长")
    prompt: str
    negative_prompt: Optional[str] = None


class VideoPromptDocument(BaseModel):
    prompts: List[VideoPromptItem]
