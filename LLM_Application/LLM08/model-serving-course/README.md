# 🔍 Zero-shot 이미지 분류 서비스

> Day 8 자율 프로젝트 — CLIP 기반 Zero-shot 이미지 분류 API + Streamlit UI

---

## 📌 프로젝트 개요

**도메인**: 이미지 분류  
**태스크**: Zero-shot Image Classification  
**모델**: `openai/clip-vit-base-patch32`

### 선택 이유

특정 데이터셋으로 재학습 없이도, 텍스트와 이미지 간의 유사도를 계산하여 즉시 분류가 가능

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



---

## 💡 구현 과정에서 어려웠던 점

바이브 코딩으로 진행하여 빠르게 시작할 수 있었지만, 구조 또는 코드가 크게 바뀔 때 흐름을 쫓아가기 어려운 지점이 있었습니다.

이와 같은 상황을 최소화하기 위해 많이 사용해보고 경험을 쌓아 잘 짜여진 구조 안에서 편의를 위한 목적으로 사용한다면 더 잘 사용할 수 있을 것 같다는 생각이 들었습니다.


---

## 🔄 회고

- **잘 된 점**: 라벨의 추가, 삭제 등 관리 용이
- **아쉬운 점**: 모델에 대한 이해가 좀 더 필요한 것 같음
- **다음에 한다면**: 이미지 생성 모델을 추가하여 생성한 이미지를 분류하는 것도 좋을 듯함.

---

## ✅ Day 8 최종 체크포인트 답변

**Q1. Pydantic 검증은 어떤 잘못된 입력을 막아줍니까?**  
- 라벨에 대한 이름과 개수의 유효성 검증

**Q2. `Depends(verify_api_key)`를 제거하면 어떤 위험이 있습니까?**  
- 누구나 API 활용 가능

**Q3. `run_in_executor`를 사용한 이유는?**  
- 이벤트 루프가 블로킹을 막기 위해 별도 스레드에서 실행하기 위함

**Q4. 가장 많이 참고한 Day는?**  
- 파일업로드와 인증 패턴을 그대로 활용

**Q5. 실제 배포 시 추가로 필요한 것은?**  
- 컨테이너화, 보안 프로토콜 설정, API Key 관리, 사용자 개별 세션 관리, 자원 관리, 모델 캐싱 전략 등
