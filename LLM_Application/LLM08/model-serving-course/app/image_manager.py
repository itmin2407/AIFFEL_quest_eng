"""
image_manager.py — 프로젝트 내부 이미지 폴더 관리

images/ 폴더를 스캔하여 사용 가능한 이미지 목록을 반환합니다.

📁 폴더 규칙:
  - 파일명(확장자 제외)이 곧 정답 라벨입니다.
  - 예: images/고양이.jpg → 정답 라벨 = "고양이"

  images/
  ├── 고양이.jpg
  ├── 강아지.png
  ├── 피자.jpg
  └── 해변.webp
"""
import random
from pathlib import Path

from app.config import ALLOWED_EXTENSIONS, IMAGES_DIR


def get_all_images() -> list[dict]:
    """
    images/ 폴더의 모든 이미지를 스캔하여 반환합니다.

    Returns:
        [{"filename": "고양이.jpg", "label": "고양이", "path": Path(...)}, ...]
    """
    if not IMAGES_DIR.exists():
        IMAGES_DIR.mkdir(parents=True)
        return []

    images = []
    for file in sorted(IMAGES_DIR.iterdir()):
        if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
            images.append({
                "filename": file.name,
                "label": file.stem,        # 확장자 제거한 파일명 = 정답
                "path": file,
            })
    return images


def get_image_by_filename(filename: str) -> dict | None:
    """
    파일명으로 이미지를 찾아 반환합니다.

    Returns:
        {"filename": str, "label": str, "path": Path} 또는 None
    """
    target = IMAGES_DIR / filename
    if not target.exists() or target.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    return {
        "filename": target.name,
        "label": target.stem,
        "path": target,
    }


def get_random_image(exclude_filename: str | None = None) -> dict | None:
    """
    이미지 중 하나를 무작위로 반환합니다.

    Args:
        exclude_filename: 제외할 파일명 (연속으로 같은 이미지가 나오지 않도록)

    Returns:
        {"filename": str, "label": str, "path": Path} 또는 None
    """
    images = get_all_images()
    if not images:
        return None

    candidates = [img for img in images if img["filename"] != exclude_filename]
    if not candidates:
        candidates = images  # 이미지가 1개뿐이면 그냥 반환

    return random.choice(candidates)


def get_image_labels() -> list[str]:
    """images/ 폴더에 있는 이미지의 정답 라벨 목록을 반환합니다."""
    return [img["label"] for img in get_all_images()]
