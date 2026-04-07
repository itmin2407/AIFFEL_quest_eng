"""
model_service.py — CLIP 모델 로드 및 Zero-shot 이미지 분류 추론

CLIP(Contrastive Language-Image Pretraining)을 사용하여
이미지와 텍스트 라벨의 유사도를 계산합니다.

흐름:
  1. load_model()    → CLIP processor + model 반환
  2. predict(...)    → 이미지 bytes + 라벨 목록 → 유사도 점수 dict 반환
"""
import logging
from io import BytesIO

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app.config import MODEL_NAME

logger = logging.getLogger(__name__)


# ── 모델 로드 ──────────────────────────────────────────────────────────────

def load_model() -> tuple[CLIPModel, CLIPProcessor]:
    """
    CLIP 모델과 프로세서를 로드합니다.

    Returns:
        (model, processor) 튜플
    """
    logger.info(f"모델 로드 시작: {MODEL_NAME}")
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model = CLIPModel.from_pretrained(MODEL_NAME)
    model.eval()  # 추론 모드

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    logger.info(f"모델 로드 완료 (device={device})")

    return model, processor


# ── 추론 함수 ──────────────────────────────────────────────────────────────

def predict(
    model_pack: tuple[CLIPModel, CLIPProcessor],
    image_bytes: bytes,
    labels: list[str],
    top_k: int = 3,
) -> dict:
    """
    이미지와 라벨 목록을 받아 Zero-shot 분류를 수행합니다.

    Args:
        model_pack: load_model()이 반환한 (model, processor) 튜플
        image_bytes: 업로드된 이미지의 raw bytes
        labels:     비교할 텍스트 라벨 목록 (최소 2개)
        top_k:      반환할 상위 결과 수

    Returns:
        {
            "top_label": str,
            "top_score": float,
            "results": [{"label": str, "score": float}, ...],
            "labels_used": [str, ...],
        }
    """
    model, processor = model_pack
    device = next(model.parameters()).device

    # ── 이미지 전처리 ──────────────────────────────────────────────────────
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(f"이미지를 열 수 없습니다: {e}") from e

    # ── CLIP 입력 준비 ─────────────────────────────────────────────────────
    # 라벨을 자연어 문장으로 변환하면 정확도가 높아집니다.
    text_prompts = [f"a photo of {label}" for label in labels]

    inputs = processor(
        text=text_prompts,
        images=image,
        return_tensors="pt",
        padding=True,
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # ── 추론 ──────────────────────────────────────────────────────────────
    with torch.no_grad():
        outputs = model(**inputs)
        # logits_per_image: [1, num_labels]
        logits = outputs.logits_per_image  # shape: (1, len(labels))
        probs = logits.softmax(dim=-1).squeeze(0)  # shape: (len(labels),)

    # ── 결과 정렬 ─────────────────────────────────────────────────────────
    scores = probs.cpu().tolist()
    label_scores = sorted(
        zip(labels, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    top_k = min(top_k, len(label_scores))
    results = [
        {"label": lbl, "score": round(score, 4)}
        for lbl, score in label_scores[:top_k]
    ]

    return {
        "top_label": results[0]["label"],
        "top_score": results[0]["score"],
        "results": results,
        "labels_used": labels,
    }
