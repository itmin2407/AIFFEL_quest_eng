# 로컬 LLM(RAG + LangServe) & Gemini MCP 핵심 정리

## 1. 로컬 한국어 LLM + RAG + LangServe

### 목표
- 무료 한국어 파인튜닝 모델(GGUF, 예: EEVE-Korean-Instruct)을 로컬에서 호스팅.
- Ollama + LangChain + LangServe로 **API·웹 UI·RAG**까지 한 번에 구성.

### 아키텍처 개요
- **모델 계층**  
  - Hugging Face에서 한국어 instruct/파인튜닝 GGUF 모델 다운로드.  
  - Ollama에 `ollama create / ollama run`으로 등록, OpenAI 유사 API 제공.

- **애플리케이션 계층**  
  - LangChain  
    - `ChatOllama`로 Ollama LLM 사용.  
    - Chroma(Vector DB) + `create_retrieval_chain`으로 RAG 체인 구성.  
  - LangServe  
    - 완성된 LangChain RAG 체인을 `/invoke`, `/stream` 등의 REST/WS 엔드포인트로 서빙.  
  - UI  
    - Streamlit, Next.js, SDD 에이전트 등이 LangServe 엔드포인트를 그대로 호출.

### RAG 파이프라인 핵심 흐름
1. **문서 전처리**  
   - PDF, 텍스트 등을 chunk 단위로 분할 후 임베딩 생성.
2. **벡터DB 구성**  
   - Chroma 등에 저장하고 `.as_retriever()`로 retriever 생성.
3. **질의 처리 체인**
   - 히스토리 인지형 retriever: 대화 히스토리를 반영해 질문 재작성.  
   - QA 체인: 검색된 컨텍스트 기반으로 한국어 답변 생성, “모르면 모른다고 답하기” 등 시스템 프롬프트 설정.
4. **세션 관리**
   - `RunnableWithMessageHistory`로 세션별 대화 히스토리 유지.

### 실무적 이점
- 클라우드 비용 없이 로컬에서 **한국어 특화 LLM + RAG** 환경 구축.  
- 모델(GGUF), 프롬프트, RAG 설정만 교체해 다양한 도메인 챗봇/어시스턴트 빠른 제작.  
- LangServe 덕분에 FastAPI를 직접 짜지 않고도 체인을 서비스로 배포·관리 가능.

---

## 2. Gemini CLI + MCP 서버

### 목표
- Gemini CLI에 MCP(Model Context Protocol) 서버를 붙여 외부 도구·서비스(GitHub, Snyk, Web, 파일시스템 등)를 안전하게 사용.

### MCP 기본 개념
- MCP 서버: LLM이 사용할 도구·리소스를 표준 인터페이스로 제공하는 서버 (로컬/원격 모두 가능).  
- Gemini CLI에서 `/mcp` 또는 `gemini mcp list`로 등록된 MCP 서버 목록 확인.

### 설정 절차 핵심
1. **사전 준비**
   - Gemini CLI 설치, 로그인/인증, 기본 명령(`/help`, `/tools`) 사용 가능한 상태.
2. **settings.json 수정**
   - 위치 예: `~/.gemini/settings.json`  
   - `mcpServers` 섹션에 MCP 서버 추가:
     ```json
     {
       "mcpServers": {
         "my-server": {
           "command": "node",
           "args": ["path/to/server.js"],
           "transport": "stdio",
           "env": {
             "API_KEY": "..."
           },
           "trust": true
         }
       }
     }
     ```
   - 저장 후 `/mcp` 또는 `gemini mcp list`로 인식 여부 확인.

### 대표 사용 예시

- **보안 스캔 MCP(Snyk 등)**  
  - CLI에서 “현재 프로젝트 취약점 분석해줘” → Gemini가 Snyk MCP 도구 사용 제안.  
  - 사용자 권한 승인 → 브라우저로 Snyk 로그인 및 “Trust path” 설정.  
  - 스캔 결과(취약점 목록·심각도·업데이트 권장 버전)를 Gemini가 요약해 제시.

- **VS Code Gemini Code Assist 연동**  
  - 동일한 `settings.json` 기반 MCP 설정을 VS Code 확장에서 재사용.  
  - IDE 내에서 버튼/UI로 같은 Snyk 스캔·수정 워크플로 실행 → 수정 후 재스캔으로 검증.

- **기타 MCP 아이디어**
  - GitHub MCP: PR/이슈 조회, 코드 리뷰, 브랜치 상태 확인.  
  - Web MCP: 특정 웹페이지의 실시간 스크래핑·요약 자동화.  
  - 파일시스템 MCP: 로컬 파일 탐색·읽기·요약 등 개발 보조.

### 핵심 메시지
- MCP는 Gemini의 기능을 확장하는 **표준 플러그인 시스템** 역할.  
- JSON 설정만으로 MCP 서버를 유연하게 추가·삭제할 수 있고, 서버별 신뢰(trust)·권한을 명시적으로 관리해 보안과 재사용성을 동시에 확보.
