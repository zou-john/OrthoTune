from openai import OpenAI
from src.core.llm import LLM


class OpenAIModel(LLM):
    """OpenAI chat completions backend."""

    def __init__(self, model: str, api_key: str | None = None):
        super().__init__(model, api_key)
        self._client = OpenAI(api_key=api_key)

    def chat(self, messages: list[dict], **kwargs) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        self.last_usage = response.usage
        return response.choices[0].message.content

    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)
