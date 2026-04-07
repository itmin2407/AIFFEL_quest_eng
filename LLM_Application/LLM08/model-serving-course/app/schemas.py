"""
schemas.py — 입력/출력 Pydantic 스키마 정의 (퀴즈 방식)
"""
from pydantic import BaseModel, Field


# ── 퀴즈 요청/응답 스키마 ──────────────────────────────────────────────────

class QuizRequest(BaseModel):
    """
    POST /quiz/answer 요청 바디.
    사용자가 정답이라고 생각하는 라벨을 제출합니다.
    """
    filename: str = Field(
        description="맞힐 이미지 파일명 (GET /quiz/image 에서 받은 값)",
        examples=["고양이.jpg"],
    )
    user_answer: str = Field(
        description="사용자가 선택한 정답 라벨",
        examples=["고양이"],
        min_length=1,
    )
    label_set: str = Field(
        default="",
        description="사용할 라벨 세트 이름 (비워두면 images/ 폴더의 파일명 기반으로 자동 구성)",
        examples=["동물"],
    )


class LabelScore(BaseModel):
    """개별 라벨과 CLIP 유사도 점수."""
    label: str
    score: float = Field(ge=0.0, le=1.0)


class QuizImageResponse(BaseModel):
    """GET /quiz/image 응답 — 사용자에게 보여줄 이미지 정보."""
    filename: str = Field(description="이미지 파일명 (answer 요청 시 다시 사용)")
    available_labels: list[str] = Field(description="선택 가능한 라벨 목록")
    total_images: int = Field(description="전체 이미지 수")


class QuizAnswerResponse(BaseModel):
    """POST /quiz/answer 응답 — 채점 결과."""
    correct: bool = Field(description="사용자 정답 여부")
    user_answer: str = Field(description="사용자가 선택한 라벨")
    correct_label: str = Field(description="실제 정답 (파일명 기반)")
    clip_answer: str = Field(description="CLIP 모델이 선택한 라벨")
    clip_score: float = Field(description="CLIP 모델의 최상위 점수")
    clip_results: list[LabelScore] = Field(description="CLIP의 전체 라벨별 점수")
    model_name: str


# ── 유틸리티 스키마 ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    available_label_sets: list[str]
    image_count: int


class LabelSetsResponse(BaseModel):
    label_sets: dict[str, list[str]]
    default: str


class ImagesResponse(BaseModel):
    """GET /images 응답 — 등록된 이미지 목록."""
    images: list[str] = Field(description="파일명 목록")
    labels: list[str] = Field(description="정답 라벨 목록 (파일명 기반)")
    total: int
