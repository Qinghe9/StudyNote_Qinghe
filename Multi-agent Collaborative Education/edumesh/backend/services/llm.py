"""LLM服务接口 - 支持OpenAI/Anthropic，同时提供模拟模式"""
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "mock")  # openai, anthropic, mock
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "gpt-4")
        self.mock_mode = self.provider == "mock"

        if self.provider == "openai" and self.api_key:
            try:
                import openai
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai not installed, falling back to mock")
                self.mock_mode = True
        elif self.provider == "anthropic" and self.api_key:
            try:
                import anthropic
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic not installed, falling back to mock")
                self.mock_mode = True
        else:
            self.mock_mode = True

        logger.info(f"LLM Service initialized: provider={self.provider}, mock={self.mock_mode}")

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        if self.mock_mode:
            return self._mock_generate(prompt)

        try:
            if self.provider == "openai":
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=500
                )
                return resp.choices[0].message.content

            elif self.provider == "anthropic":
                resp = await self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                )
                return resp.content[0].text
        except Exception as e:
            logger.error(f"LLM API error: {e}, falling back to mock")
            return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        # 模拟LLM响应，用于测试
        if "苏格拉底" in prompt or "socratic" in prompt.lower():
            return "这是一个很好的思考角度。你能进一步解释你的推理过程吗？"
        elif "hint" in prompt.lower() or "提示" in prompt:
            return "试着从题目给出的条件出发，一步一步推导。"
        else:
            return f"[Mock LLM] 收到提示: {prompt[:50]}..."

    async def generate_socratic_response(self, question: str, student_answer: str, is_correct: bool) -> str:
        system = "你是一位苏格拉底式导师。你不直接给答案，而是通过提问引导学生思考。"
        prompt = f"""
        问题: {question}
        学生答案: {student_answer}
        是否正确: {'是' if is_correct else '否'}

        请用苏格拉底式提问法回复（中文，不超过100字）。
        """
        return await self.generate(prompt, system=system, temperature=0.8)

# 全局实例
llm_service = LLMService()
