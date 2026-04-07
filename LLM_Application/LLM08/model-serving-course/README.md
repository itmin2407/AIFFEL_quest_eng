# 🔍 Zero-shot 이미지 분류 서비스

> Day 8 자율 프로젝트 — CLIP 기반 Zero-shot 이미지 분류 API + Streamlit UI

---

## 📌 프로젝트 개요

**도메인**: 컴퓨터 비전 / 이미지 분류  
**태스크**: Zero-shot Image Classification  
**모델**: `openai/clip-vit-base-patch32`

### 선택 이유

CLIP은 이미지와 텍스트를 같은 임베딩 공간에 투영해, **모델 재학습 없이** 임의의 라벨로 이미지를 분류할 수 있습니다. 라벨을 자유롭게 변경할 수 있다는 점이 서비스 확장성 면에서 매력적입니다.

---

## 📁 폴더 구조

```
zero-shot-classifier/
├── 📁 app/
│   ├── __init__.py
│   ├── auth.py           ← Day 6 재사용: API Key 인증
│   ├── config.py         ← 라벨 세트 & 모델 설정 중앙 관리 (★ 확장 포인트)
│   ├── schemas.py        ← Pydantic 입출력 스키마
│   ├── model_service.py  ← CLIP 모델 로드 + 추론
│   └── main.py           ← FastAPI 서버
│
├── 📁 frontend/
│   └── app.py            ← Streamlit UI
│
├── 📁 tests/
│   └── test_api.py       ← API 통합 테스트
│
├── requirements.txt
└── README.md
```

---

## 🚀 실행 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. FastAPI 서버 실행

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

### 3. Streamlit 프론트엔드 실행 (별도 터미널)

```bash
streamlit run frontend/app.py
```

### 4. API 테스트

```bash
python tests/test_api.py
```

---

## 📋 평가 기준 체크리스트

| 항목 | 구현 위치 | 상태 |
|------|-----------|------|
| 서버 정상 실행 | `app/main.py` | ✅ |
| Swagger UI 추론 동작 | `POST /predict` | ✅ |
| API Key 없을 시 401 | `app/auth.py` + `Depends` | ✅ |
| 잘못된 입력 에러 처리 | Pydantic + HTTPException | ✅ |
| Streamlit UI | `frontend/app.py` | ✅ |
| 비동기 추론 | `run_in_executor` | ✅ |

---

## 🏷️ 라벨 추가/삭제 방법

`app/config.py`의 `LABEL_SETS`를 수정하면 서버 재시작 후 자동 반영됩니다.

```python
# app/config.py

LABEL_SETS = {
    "일반": ["사람", "자동차", "건물", "음식", ...],

    # 새 세트 추가 예시
    "내가_만든_세트": ["라벨1", "라벨2", "라벨3"],
}
```

API 요청 시 `custom_labels`로 동적으로도 지정 가능합니다:

```bash
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: test-key-001" \
  -F "image=@my_image.jpg" \
  -F "custom_labels=고양이,강아지,새"
```

---

## 🔑 API 명세

### `GET /health`

```json
{
  "status": "ok",
  "model_loaded": true,
  "available_label_sets": ["일반", "동물", "음식", "장소", "교통수단"]
}
```

### `GET /labels`

```json
{
  "label_sets": {
    "일반": ["사람", "자동차", ...],
    "동물": ["고양이", "강아지", ...]
  },
  "default": "일반"
}
```

### `POST /predict` (인증 필요)

**요청**

| 필드 | 타입 | 설명 |
|------|------|------|
| `image` | File | 분류할 이미지 (JPEG/PNG/WEBP) |
| `label_set` | str | 라벨 세트 이름 (기본: `일반`) |
| `custom_labels` | str | 쉼표 구분 라벨 (지정 시 label_set 무시) |
| `top_k` | int | 상위 결과 수 (1~10, 기본: 3) |

**응답**

```json
{
  "success": true,
  "top_label": "고양이",
  "top_score": 0.7823,
  "results": [
    {"label": "고양이", "score": 0.7823},
    {"label": "강아지", "score": 0.1542},
    {"label": "새",     "score": 0.0635}
  ],
  "labels_used": ["고양이", "강아지", "새", ...],
  "model_name": "openai/clip-vit-base-patch32"
}
```

---

## 💡 구현 과정에서 어려웠던 점

1. **CLIP의 입력 형식**: 단순 라벨("고양이")보다 `"a photo of 고양이"` 형태의 프롬프트가 정확도가 높았습니다. `model_service.py`에서 자동 변환합니다.

2. **Form + File 혼합**: FastAPI에서 `UploadFile`과 Pydantic 스키마를 동시에 사용할 수 없어, Form 필드를 개별로 받고 수동으로 검증 로직을 적용했습니다.

3. **라벨 확장성**: `config.py`에 라벨 세트를 중앙 관리하고 `/labels` 엔드포인트로 프론트엔드가 동적으로 가져오도록 설계했습니다.

---

## 🔄 회고

- **잘 된 점**: config.py 중앙화로 라벨 추가/삭제가 매우 쉬워졌습니다.
- **아쉬운 점**: CLIP은 한국어 라벨보다 영어 라벨에서 정확도가 높습니다. 다음에는 한국어 CLIP 모델(klue/clip 등)을 시도해보고 싶습니다.
- **다음에 한다면**: 배치 이미지 처리 엔드포인트(`POST /predict/batch`)를 추가하겠습니다.

---

## ✅ Day 8 최종 체크포인트 답변

**Q1. Pydantic 검증은 어떤 잘못된 입력을 막아줍니까?**  
- 존재하지 않는 `label_set` 이름, `top_k`가 1~10 범위를 벗어나는 경우, `custom_labels`가 1개 이하이거나 50개 초과인 경우를 막습니다.

**Q2. `Depends(verify_api_key)`를 제거하면 어떤 위험이 있습니까?**  
- 누구나 API를 무제한 호출할 수 있어 서버 리소스 남용, 과금 폭증, 악의적 사용이 가능해집니다.

**Q3. `run_in_executor`를 사용한 이유는?**  
- CLIP 추론은 CPU/GPU 집약적인 동기 작업입니다. `async` 함수 안에서 직접 호출하면 이벤트 루프가 블로킹됩니다. `run_in_executor`로 별도 스레드에서 실행해 다른 요청을 동시에 처리할 수 있게 합니다.

**Q4. 가장 많이 참고한 Day는?**  
- Day 6 (파일 업로드 + 인증) — `UploadFile` 처리와 `Depends` 패턴을 그대로 활용했습니다.

**Q5. 실제 배포 시 추가로 필요한 것은?**  
- Docker 컨테이너화, HTTPS/TLS 설정, API Key 데이터베이스화, Rate Limiting, 모델 캐싱 전략(Redis 등).
