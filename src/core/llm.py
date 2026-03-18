from abc import ABC, abstractmethod


class LLM(ABC):
    """Abstract base class for all LLM backends.

    Usage:
        llm = create_llm("gpt-4o")
        reply = llm.complete("Summarise this text: ...")
        reply = llm.chat([{"role": "user", "content": "Hello"}])
    """

    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """Send a messages list and return the assistant reply."""

    @abstractmethod
    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """Send a single user prompt and return the reply."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"


def create_llm(model: str, api_key: str | None = None) -> LLM:
    """Factory that returns the right LLM subclass for a given model name."""
    if model.startswith(("gpt-", "o1", "o3", "o4")):
        from src.models.openai import OpenAIModel
        return OpenAIModel(model, api_key=api_key)
    raise ValueError(f"Unknown model {model!r}. Add its prefix to create_llm().")
