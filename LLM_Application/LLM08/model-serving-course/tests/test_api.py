"""
tests/test_api.py — API 통합 테스트 & 수동 테스트 스크립트

사용법:
  # 서버 실행 후
  python tests/test_api.py

pytest 사용:
  pytest tests/test_api.py -v
"""
import io
import sys

import requests
from PIL import Image

API_URL = "http://localhost:8000"
VALID_KEY = "test-key-001"
INVALID_KEY = "invalid-key"


# ── 테스트용 이미지 생성 ───────────────────────────────────────────────────

def make_test_image(color: tuple = (255, 100, 50)) -> bytes:
    """테스트용 이미지 bytes를 생성합니다."""
    img = Image.new("RGB", (224, 224), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── 테스트 함수 ────────────────────────────────────────────────────────────

def test_health():
    """✅ 서버가 정상적으로 실행되는가?"""
    resp = requests.get(f"{API_URL}/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "ok"
    assert "available_label_sets" in data
    print(f"  ✅ /health — model_loaded={data['model_loaded']}")


def test_labels():
    """✅ 라벨 세트 목록 조회가 동작하는가?"""
    resp = requests.get(f"{API_URL}/labels")
    assert resp.status_code == 200
    data = resp.json()
    assert "label_sets" in data
    assert len(data["label_sets"]) > 0
    print(f"  ✅ /labels — {len(data['label_sets'])}개 세트: {list(data['label_sets'].keys())}")


def test_predict_no_key():
    """✅ API Key 없이 요청하면 401이 반환되는가?"""
    resp = requests.post(
        f"{API_URL}/predict",
        files={"image": ("test.jpg", make_test_image(), "image/jpeg")},
        data={"label_set": "일반"},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print(f"  ✅ API Key 없음 → 401 반환")


def test_predict_invalid_key():
    """✅ 잘못된 API Key에 대해 401이 반환되는가?"""
    resp = requests.post(
        f"{API_URL}/predict",
        headers={"X-API-Key": INVALID_KEY},
        files={"image": ("test.jpg", make_test_image(), "image/jpeg")},
        data={"label_set": "일반"},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print(f"  ✅ 잘못된 API Key → 401 반환")


def test_predict_success():
    """✅ 정상 추론이 동작하는가?"""
    resp = requests.post(
        f"{API_URL}/predict",
        headers={"X-API-Key": VALID_KEY},
        files={"image": ("test.jpg", make_test_image(), "image/jpeg")},
        data={"label_set": "일반", "top_k": 3},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["success"] is True
    assert "top_label" in data
    assert len(data["results"]) == 3
    print(f"  ✅ 정상 추론 → top={data['top_label']} ({data['top_score']*100:.1f}%)")
    print(f"     결과: {[(r['label'], f\"{r['score']*100:.1f}%\") for r in data['results']]}")


def test_predict_custom_labels():
    """✅ custom_labels가 동작하는가?"""
    resp = requests.post(
        f"{API_URL}/predict",
        headers={"X-API-Key": VALID_KEY},
        files={"image": ("test.jpg", make_test_image(), "image/jpeg")},
        data={"custom_labels": "빨간색 물체, 파란색 물체, 초록색 물체", "top_k": 2},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert len(data["results"]) == 2
    print(f"  ✅ custom_labels → top={data['top_label']}")


def test_predict_invalid_label_set():
    """✅ 존재하지 않는 label_set에 대해 422가 반환되는가?"""
    resp = requests.post(
        f"{API_URL}/predict",
        headers={"X-API-Key": VALID_KEY},
        files={"image": ("test.jpg", make_test_image(), "image/jpeg")},
        data={"label_set": "존재하지않는세트"},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
    print(f"  ✅ 잘못된 label_set → 422 반환")


def test_predict_invalid_image():
    """✅ 이미지가 아닌 파일에 대해 422가 반환되는가?"""
    resp = requests.post(
        f"{API_URL}/predict",
        headers={"X-API-Key": VALID_KEY},
        files={"image": ("test.txt", b"this is not an image", "text/plain")},
        data={"label_set": "일반"},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
    print(f"  ✅ 잘못된 파일 타입 → 422 반환")


# ── 실행 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_health,
        test_labels,
        test_predict_no_key,
        test_predict_invalid_key,
        test_predict_success,
        test_predict_custom_labels,
        test_predict_invalid_label_set,
        test_predict_invalid_image,
    ]

    print("=" * 50)
    print("🧪 Zero-shot 분류 API 테스트")
    print("=" * 50)

    passed = 0
    failed = 0

    for test in tests:
        print(f"\n[{test.__name__}]")
        print(f"  {test.__doc__}")
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAIL: {e}")
            failed += 1
        except requests.exceptions.ConnectionError:
            print(f"  ⚠️  SKIP: 서버가 실행 중이지 않습니다 ({API_URL})")
            failed += 1

    print(f"\n{'='*50}")
    print(f"결과: {passed}개 통과 / {failed}개 실패")
    print("=" * 50)
    sys.exit(0 if failed == 0 else 1)
