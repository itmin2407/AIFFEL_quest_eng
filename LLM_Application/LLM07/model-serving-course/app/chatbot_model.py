"""
Day 7 - 한국어 GPT 챗봇 모델
"""
import torch
from transformers import PreTrainedTokenizerFast, GPT2LMHeadModel


class ChatbotModel:
    """Hugging Face 한국어 GPT 모델을 로드하고 텍스트를 생성합니다."""

    def __init__(self, model_name: str = "skt/kogpt2-base-v2"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = PreTrainedTokenizerFast.from_pretrained(model_name)
        self.model = GPT2LMHeadModel.from_pretrained(model_name, use_safetensors=True)
        self.model = self.model.to(self.device)
        self.model.eval()

        self.model_name = model_name

    def generate_response(
        self,
        messages: list[dict],
        max_new_tokens: int = 100,
        temperature: float = 0.8,
        top_k: int = 50,
        top_p: float = 0.9,
    ) -> str:
        """
        대화 기록을 받아 응답을 생성합니다.

        Args:
            messages: [{"role": "user", "content": "안녕"}, {"role": "bot", "content": "안녕하세요!"}, ...]
            max_new_tokens: 최대 생성 토큰 수
            temperature: 생성 다양성
        Returns:
            생성된 응답 텍스트
        """
        # 대화 기록 → 프롬프트 구성
        prompt = self._build_prompt(messages)              # *your code* — 프롬프트 구성

        # 토크나이징
        input_ids = self.tokenizer.encode(
            prompt, return_tensors="pt"
        ).to(self.device)

        # 토큰 수 제한 (모델 최대 길이 초과 방지)
        max_length = getattr(self.model.config, "n_positions", 1024)
        if input_ids.shape[1] > max_length - max_new_tokens:
            # 최근 대화만 유지
            input_ids = input_ids[:, -(max_length - max_new_tokens):]

        # 텍스트 생성
        with torch.no_grad():
            output_ids = self.model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,             # *your code* — 생성 파라미터
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # 디코딩: 생성된 부분만 추출
        full_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        response = full_text[len(prompt):].strip()

        # "사용자:" 이후 텍스트가 나오면 거기까지만 자름
        if "사용자:" in response:
            response = response.split("사용자:")[0].strip()

        return response if response else "(응답을 생성하지 못했습니다)"

    def _build_prompt(self, messages: list[dict]) -> str:
        """대화 기록을 프롬프트 문자열로 변환합니다."""
        lines = []
        for msg in messages:
            role = "사용자" if msg["role"] == "user" else "봇"
            lines.append(f"{role}: {msg['content']}")
        lines.append("봇:")  # 모델이 이어서 생성하도록
        return "\n".join(lines)
