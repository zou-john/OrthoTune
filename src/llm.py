from abc import ABC, abstractmethod


class LLM(ABC):
    """Abstract base class for all LLM backends.

    Subclasses must implement `chat` and `complete`.

    Usage:
        llm = OpenAIModel("gpt-4o")
        reply = llm.complete("Summarise this text: ...")
        reply = llm.chat([{"role": "user", "content": "Hello"}])
    """

    def __init__(self, model: str, api_key: str | None = None):
        """
        Args:
            model:   Model identifier, e.g. "gpt-4o", "gpt-4o-mini".
            api_key: Optional API key for the provider.
        """
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """Send a messages list and return the assistant reply.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            **kwargs: Backend-specific parameters (temperature, max_tokens, …).
        """

    @abstractmethod
    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """Send a single user prompt and return the reply.

        Args:
            prompt: The user message text.
            system: Optional system prompt prepended to the conversation.
            **kwargs: Forwarded to chat().
        """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"


def create_llm(model: str, api_key: str | None = None) -> LLM:
    """Factory that returns the right LLM subclass for a given model name.

    Args:
        model:   Model identifier, e.g. "gpt-4o", "gpt-4o-mini".
        api_key: Optional API key for the provider.
    """
    if model.startswith(("gpt-", "o1", "o3", "o4")):
        from src.model.openai import OpenAIModel
        return OpenAIModel(model, api_key=api_key)
    raise ValueError(f"Unknown model {model!r}. Add its prefix to create_llm().")
