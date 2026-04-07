"""
main.py — FastAPI 서버 (퀴즈 방식)

엔드포인트:
  GET  /health          → 서버 상태 확인
  GET  /labels          → 사용 가능한 라벨 세트 목록
  GET  /images          → 등록된 이미지 목록
  GET  /quiz/image      → 퀴즈용 이미지 1장 랜덤 반환 (이미지 파일 자체)
  GET  /quiz/info       → 퀴즈용 이미지 정보 반환 (파일명, 선택지)
  POST /quiz/answer     → 사용자 정답 제출 → CLIP 채점 결과 반환

실행 방법:
  uvicorn app.main:app --reload --port 8000
"""
import asyncio
import base64
import logging
import random
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.auth import verify_api_key
from app.config import LABEL_SETS, MODEL_NAME, DEFAULT_LABEL_SET, TOP_K_DEFAULT
from app.image_manager import get_all_images, get_image_by_filename, get_random_image
from app.model_service import load_model, predict
from app.schemas import (
    HealthResponse,
    ImagesResponse,
    LabelScore,
    LabelSetsResponse,
    QuizAnswerResponse,
    QuizImageResponse,
    QuizRequest,
)

# ── 로깅 설정 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 전역 상태 ──────────────────────────────────────────────────────────────
_model_pack = None
_executor = ThreadPoolExecutor(max_workers=2)


# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model_pack
    logger.info("서버 시작 — 모델 로드 중...")
    loop = asyncio.get_event_loop()
    _model_pack = await loop.run_in_executor(_executor, load_model)
    logger.info("모델 로드 완료 ✅")
    yield
    logger.info("서버 종료")
    _executor.shutdown(wait=False)


# ── FastAPI 앱 ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Zero-shot 이미지 분류 퀴즈 API",
    description=(
        "CLIP 모델 기반 이미지 분류 퀴즈 서비스입니다.\n\n"
        "**퀴즈 흐름**\n"
        "1. `GET /quiz/info` — 랜덤 이미지 정보(파일명, 선택지) 조회\n"
        "2. `GET /quiz/image?filename=xxx` — 이미지 파일 다운로드\n"
        "3. `POST /quiz/answer` — 정답 제출 → CLIP 채점 결과 확인\n\n"
        "**인증**: `X-API-Key` 헤더 필요. 테스트 키: `test-key-001`"
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────

def _get_model_pack():
    if _model_pack is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="모델이 아직 로드되지 않았습니다. 잠시 후 다시 시도해 주세요.",
        )
    return _model_pack


def _resolve_labels(label_set: str) -> list[str]:
    """
    label_set 이름으로 라벨 목록을 반환합니다.
    비어있으면 images/ 폴더의 파일명(정답 라벨)을 모두 사용합니다.
    """
    if label_set and label_set in LABEL_SETS:
        return LABEL_SETS[label_set]
    # label_set 미지정 → 이미지 파일명에서 자동 구성
    from app.image_manager import get_image_labels
    labels = get_image_labels()
    if not labels:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="images/ 폴더에 이미지가 없습니다. 이미지를 추가해 주세요.",
        )
    return labels


# ── 엔드포인트 ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["운영"])
async def health_check():
    """서버 및 모델 상태를 확인합니다."""
    images = get_all_images()
    return HealthResponse(
        status="ok",
        model_loaded=_model_pack is not None,
        available_label_sets=list(LABEL_SETS.keys()),
        image_count=len(images),
    )


@app.get("/labels", response_model=LabelSetsResponse, tags=["라벨"])
async def get_label_sets():
    """사용 가능한 모든 라벨 세트를 반환합니다."""
    return LabelSetsResponse(label_sets=LABEL_SETS, default=DEFAULT_LABEL_SET)


@app.get("/images", response_model=ImagesResponse, tags=["이미지"])
async def list_images():
    """
    images/ 폴더에 등록된 이미지 목록을 반환합니다.

    파일명(확장자 제외)이 곧 정답 라벨입니다.
    """
    images = get_all_images()
    return ImagesResponse(
        images=[img["filename"] for img in images],
        labels=[img["label"] for img in images],
        total=len(images),
    )


@app.get("/quiz/info", response_model=QuizImageResponse, tags=["퀴즈"])
async def get_quiz_info(
    label_set: str = Query(
        default="",
        description="선택지로 사용할 라벨 세트. 비워두면 images/ 파일명 기반으로 자동 구성",
    ),
    exclude: str = Query(
        default="",
        description="제외할 파일명 (연속으로 같은 이미지가 나오지 않도록)",
    ),
    user: str = Depends(verify_api_key),
):
    """
    퀴즈에 사용할 랜덤 이미지 정보를 반환합니다.

    - **filename**: 이미지 파일명 → `/quiz/image?filename=xxx` 로 이미지 조회
    - **available_labels**: 사용자가 선택할 수 있는 라벨 목록
    """
    image = get_random_image(exclude_filename=exclude or None)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="images/ 폴더에 이미지가 없습니다. 이미지를 추가해 주세요.",
        )

    labels = _resolve_labels(label_set)

    # 정답이 선택지에 없으면 추가 (퀴즈가 성립하도록)
    if image["label"] not in labels:
        labels = labels + [image["label"]]

    random.shuffle(labels)

    logger.info(f"[{user}] 퀴즈 이미지: {image['filename']} / 선택지: {labels}")

    return QuizImageResponse(
        filename=image["filename"],
        available_labels=labels,
        total_images=len(get_all_images()),
    )


@app.get("/quiz/image", tags=["퀴즈"])
async def get_quiz_image(
    filename: str = Query(..., description="이미지 파일명 (GET /quiz/info 에서 받은 값)"),
    user: str = Depends(verify_api_key),
):
    """
    지정한 파일명의 이미지를 반환합니다.

    `/quiz/info`에서 받은 `filename`을 그대로 사용하세요.
    """
    image = get_image_by_filename(filename)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"이미지를 찾을 수 없습니다: {filename}",
        )
    return FileResponse(
        path=str(image["path"]),
        media_type="image/jpeg",
        filename=image["filename"],
    )


@app.post("/quiz/answer", response_model=QuizAnswerResponse, tags=["퀴즈"])
async def submit_answer(
    req: QuizRequest,
    user: str = Depends(verify_api_key),
):
    """
    사용자의 정답을 제출하고 CLIP 모델의 채점 결과를 받습니다.

    **응답 항목**
    - `correct`: 사용자 정답 여부
    - `correct_label`: 실제 정답 (파일명 기반)
    - `clip_answer`: CLIP이 선택한 라벨
    - `clip_results`: 라벨별 유사도 점수 전체
    """
    logger.info(f"[{user}] 정답 제출 — 파일: {req.filename}, 사용자 답: {req.user_answer}")

    # 이미지 확인
    image = get_image_by_filename(req.filename)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"이미지를 찾을 수 없습니다: {req.filename}",
        )

    # 라벨 목록 결정
    labels = _resolve_labels(req.label_set)
    if image["label"] not in labels:
        labels = labels + [image["label"]]

    # 이미지 읽기
    image_bytes = image["path"].read_bytes()
    model_pack = _get_model_pack()

    # 비동기 추론
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _executor,
            lambda: predict(model_pack, image_bytes, labels, len(labels)),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.exception("추론 중 오류 발생")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    correct_label = image["label"]
    is_correct = req.user_answer.strip() == correct_label

    logger.info(
        f"[{user}] 채점 완료 — 정답: {correct_label}, "
        f"사용자: {req.user_answer} ({'O' if is_correct else 'X'}), "
        f"CLIP: {result['top_label']} ({result['top_score']:.3f})"
    )

    return QuizAnswerResponse(
        correct=is_correct,
        user_answer=req.user_answer,
        correct_label=correct_label,
        clip_answer=result["top_label"],
        clip_score=result["top_score"],
        clip_results=[LabelScore(**r) for r in result["results"]],
        model_name=MODEL_NAME,
    )