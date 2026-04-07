"""
frontend/app.py — Streamlit 퀴즈 UI

흐름:
  1. 사이드바에서 API Key + 라벨 세트 설정
  2. '새 문제 받기' 버튼 → /quiz/info 호출 → 이미지 표시
  3. 라디오 버튼으로 라벨 선택
  4. '정답 제출' 버튼 → /quiz/answer 호출 → 결과 표시

실행:
  streamlit run frontend/app.py
"""
import requests
import streamlit as st

API_URL = "http://localhost:8000"


def render_loading_overlay(message: str, progress: int = 0) -> str:
    return f"""
    <style>
        #stLoadingOverlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(8px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        #stLoadingOverlay .inner {{
            text-align: center;
            padding: 2.5rem;
            border-radius: 24px;
            background: white;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            width: 85%;
        }}
        
        /* 달리는 캐릭터 컨테이너 */
        .runner-container {{
            position: relative;
            display: inline-block;
            height: 80px;
            width: 100px;
        }}

        .runner {{
            font-size: 4rem;
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            animation: runner-sprint 0.6s infinite linear;
        }}

        /* 잔상 효과 */
        .runner-ghost {{
            font-size: 4rem;
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0.3;
            filter: blur(2px);
            animation: runner-sprint 0.6s infinite linear;
            animation-delay: -0.1s; /* 약간 뒤처지게 */
        }}

        @keyframes runner-sprint {{
            0% {{ 
                transform: translate(-50%, 0) rotate(0deg); 
            }}
            25% {{ 
                transform: translate(-55%, -8px) rotate(-5deg); 
            }}
            50% {{ 
                transform: translate(-50%, 0) rotate(0deg); 
            }}
            75% {{ 
                transform: translate(-45%, -6px) rotate(5deg); 
            }}
            100% {{ 
                transform: translate(-50%, 0) rotate(0deg); 
            }}
        }}

        #stLoadingOverlay progress {{
            width: 100%;
            height: 12px;
            margin-top: 1.5rem;
            accent-color: #4f46e5;
            border-radius: 10px;
        }}
        
        #stLoadingOverlay .message {{
            margin-top: 1.2rem;
            font-size: 1.1rem;
            color: #1f2937;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
    </style>
    <div id="stLoadingOverlay">
        <div class="inner">
            <div class="runner-container">
                <div class="runner-ghost">🏃‍♂️</div>
                <div class="runner">🏃‍♂️</div>
            </div>
            <div class="message">{message}</div>
            <progress value="{progress}" max="100"></progress>
        </div>
    </div>
    """

@st.cache_data(ttl=300)
def fetch_label_sets(api_url: str, api_key: str) -> list[str]:
    """API 서버에서 라벨 세트 목록을 가져옵니다. 재실행 시 캐시 처리됩니다."""
    headers = {"X-API-Key": api_key} if api_key else {}
    response = requests.get(f"{api_url}/labels", headers=headers, timeout=5)
    response.raise_for_status()
    return list(response.json().get("label_sets", {}).keys())

st.set_page_config(page_title="🧠 이미지 분류 퀴즈", page_icon="🧠", layout="wide")
st.title("🧠 Zero-shot 이미지 분류 퀴즈")
st.caption("CLIP 모델과 함께 이미지를 맞춰보세요!")

# ── 사이드바 ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    api_url = st.text_input("API 서버", value=API_URL)
    api_key = st.text_input("X-API-Key", value="test-key-001", type="password")
    headers = {"X-API-Key": api_key}

    st.divider()

    # 라벨 세트 선택
    try:
        label_sets = fetch_label_sets(api_url, api_key)
    except Exception:
        label_sets = []

    selected_set = st.selectbox(
        "라벨 세트",
        options=["(전체 랜덤)"] + label_sets,
    )
    top_k = st.slider("Top-K 결과", 1, 10, 3)

    st.divider()

    # 서버 상태
    if st.button("🔌 서버 상태 확인"):
        try:
            h = requests.get(f"{api_url}/health", timeout=5).json()
            if h.get("status") == "ok":
                model_loaded = h.get("model_loaded", False)
                image_count = h.get("image_count", 0)
                label_sets = h.get("available_label_sets", [])
                st.success(
                    f"✅ 서버 정상. 모델 상태: {'LOAD' if model_loaded else 'UNLOAD'} | "
                    f"이미지: {image_count}개 | 라벨 세트: {len(label_sets)}개"
                )
                if label_sets:
                    st.info(f"사용 가능한 라벨 세트: {', '.join(label_sets)}")
            else:
                st.error("❌ 서버 상태가 비정상입니다.")
        except Exception:
            st.error("❌ 서버 연결 실패")

    st.divider()
    st.markdown(
        "**이미지 구조**\n\n"
        "```\n"
        "images/\n"
        "├── 동물/\n"
        "│   ├── cat.jpg\n"
        "│   └── dog.jpg\n"
        "└── 음식/\n"
        "    └── pizza.jpg\n"
        "```"
    )

# ── 세션 상태 초기화 ──────────────────────────────────────────────────────
if "quiz" not in st.session_state:
    st.session_state.quiz = None       # 현재 퀴즈 데이터
if "result" not in st.session_state:
    st.session_state.result = None     # 추론 결과
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# ── 메인 레이아웃 ─────────────────────────────────────────────────────────
col_img, col_quiz = st.columns([1, 1], gap="large")

with col_img:
    st.subheader("📸 문제 이미지")
    img_placeholder = st.empty()
    caption_placeholder = st.empty()

    if st.button("🎲 새 문제 받기", type="primary", use_container_width=True):
        params = {}
        if selected_set != "(전체 랜덤)":
            params["label_set"] = selected_set
        overlay = st.empty()
        progress = st.empty()
        try:
            overlay.markdown(
                render_loading_overlay("새 문제 로딩 중입니다...", 20),
                unsafe_allow_html=True,
            )
            progress.progress(20)
            resp = requests.get(
                f"{api_url}/quiz/info",
                headers=headers,
                params=params,
                timeout=10,
            )
            progress.progress(70)
            if resp.status_code == 200:
                quiz_data = resp.json()
                quiz_data["label_set"] = selected_set if selected_set != "(전체 랜덤)" else ""
                st.session_state.quiz = quiz_data
                st.session_state.result = None
                st.session_state.submitted = False
                progress.progress(100)
            elif resp.status_code == 401:
                st.error("❌ API Key가 올바르지 않습니다.")
            elif resp.status_code == 404:
                st.error("❌ 등록된 이미지가 없습니다. images/ 폴더를 확인하세요.")
            else:
                st.error(f"❌ 오류 ({resp.status_code}): {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error(f"❌ 서버({api_url})에 연결할 수 없습니다.")
        except Exception as e:
            st.error(f"❌ 새 문제 로딩 실패: {e}")
        finally:
            overlay.empty()
            progress.empty()

    if st.session_state.quiz:
        quiz = st.session_state.quiz
        img_url = f"{api_url}/quiz/image"
        try:
            img_resp = requests.get(
                img_url,
                headers=headers,
                params={"filename": quiz["filename"]},
                timeout=10,
            )
            if img_resp.status_code == 200:
                img_placeholder.image(img_resp.content, use_container_width=True)
                caption_placeholder.caption(
                    f"라벨 세트: **{quiz['label_set'] or '(전체 랜덤)'}**"
                )
            elif img_resp.status_code == 401:
                img_placeholder.empty()
                caption_placeholder.empty()
                st.warning("❌ 이미지 요청에 필요한 API Key가 올바르지 않습니다.")
            elif img_resp.status_code == 404:
                img_placeholder.empty()
                caption_placeholder.empty()
                st.warning("❌ 이미지 파일을 찾을 수 없습니다. filename 파라미터를 확인하세요.")
            else:
                img_placeholder.empty()
                caption_placeholder.empty()
                st.warning(f"이미지를 불러올 수 없습니다: {img_url} (status={img_resp.status_code})")
        except requests.exceptions.ConnectionError:
            img_placeholder.empty()
            caption_placeholder.empty()
            st.error(f"❌ 서버({api_url})에 연결할 수 없습니다.")
        except Exception as e:
            img_placeholder.empty()
            caption_placeholder.empty()
            st.warning(f"이미지를 불러올 수 없습니다: {img_url} ({e})")
    else:
        img_placeholder.empty()
        caption_placeholder.empty()
        st.info("'새 문제 받기' 버튼을 눌러 시작하세요!")

with col_quiz:
    st.subheader("🏷️ 정답을 선택하세요")

    if st.session_state.quiz:
        quiz = st.session_state.quiz
        choices = quiz["available_labels"]

        with st.form("answer_form"):
            user_choice = st.radio(
                "이 이미지는 무엇일까요?",
                options=choices,
                key=f"radio_{quiz['filename']}",
            )
            button_label = "✅ 제출 완료" if st.session_state.submitted else "✅ 정답 제출"
            submitted = st.form_submit_button(
                button_label,
                type="primary",
                use_container_width=True,
                disabled=st.session_state.submitted,
            )

        if st.session_state.submitted:
            st.info("✅ 이미 한번 제출하셨습니다. 새 문제 받기를 눌러주세요.")

        if submitted and not st.session_state.submitted:
            overlay = st.empty()
            progress = st.empty()
            try:
                overlay.markdown(
                    render_loading_overlay("정답 제출 중입니다...", 20),
                    unsafe_allow_html=True,
                )
                progress.progress(20)
                resp = requests.post(
                    f"{api_url}/quiz/answer",
                    headers=headers,
                    json={
                        "filename": quiz["filename"],
                        "user_answer": user_choice,
                        "label_set": quiz.get("label_set", ""),
                    },
                    timeout=30,
                )
                progress.progress(70)
                if resp.status_code == 200:
                    st.session_state.result = resp.json()
                    st.session_state.submitted = True
                else:
                    st.error(f"❌ 오류 ({resp.status_code}): {resp.text}")
            except Exception as e:
                st.error(f"❌ 요청 실패: {e}")
            finally:
                overlay.empty()
                progress.empty()
        # 결과 표시
        if st.session_state.submitted and st.session_state.result:
            result = st.session_state.result

            # 정답/오답 배너
            if result["correct"]:
                if result["clip_answer"] == result["user_answer"]:
                    st.success(
                        f"🎉 정답! 모델도 **{result['clip_answer']}** 라고 예측했습니다."
                    )
                else:
                    st.success(
                        f"🎉 정답! 하지만 모델은 **{result['clip_answer']}** 라고 예측했습니다."
                    )
            else:
                st.error(
                    f"❌ 오답. 당신: **{result['user_answer']}** "
                    f"/ 실제 정답: **{result['correct_label']}** "
                    f"/ 모델: **{result['clip_answer']}**"
                )

            st.divider()
            st.markdown("**📊 모델의 상위 예측 결과**")

            import pandas as pd
            df = pd.DataFrame(result["clip_results"]).rename(
                columns={"label": "라벨", "score": "유사도"}
            )
            st.bar_chart(df.set_index("라벨")["유사도"])

            with st.expander("🔍 상세 점수"):
                for i, r in enumerate(result["clip_results"], 1):
                    pct = r["score"] * 100
                    st.progress(r["score"], text=f"#{i} {r['label']} — {pct:.1f}%")
                st.caption(f"모델: `{result['model_name']}`")

    else:
        st.info("← 먼저 새 문제를 받아오세요.")