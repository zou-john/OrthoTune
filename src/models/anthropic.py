import anthropic
from src.core.llm import LLM


class AnthropicModel(LLM):
    """anthropic claude backend."""

    def __init__(self, model: str, api_key: str | None = None):
        super().__init__(model, api_key)
        self._client = anthropic.Anthropic(api_key=api_key)

    def chat(self, messages: list[dict], **kwargs) -> str:
        # anthropic takes system separately from the messages list
        system = kwargs.pop("system", anthropic.NOT_GIVEN)
        response = self._client.messages.create(
            model=self.model,
            max_tokens=kwargs.pop("max_tokens", 1024),
            system=system,
            messages=messages,
            **kwargs,
        )
        # normalize usage to match openai field names
        self.last_usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        return response.content[0].text

    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        if system:
            kwargs["system"] = system
        return self.chat(messages, **kwargs)

    def run_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_handler,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Agentic loop: call tools until stop_reason is end_turn. Returns final text."""
        sys = system if system is not None else anthropic.NOT_GIVEN
        while True:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=sys,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                return "\n".join(b.text for b in response.content if hasattr(b, "text"))

            if response.stop_reason == "tool_use":
                # append assistant turn with tool_use blocks
                messages.append({"role": "assistant", "content": response.content})
                # execute each tool and collect results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = tool_handler(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        })
                messages.append({"role": "user", "content": tool_results})
            else:
                # max_tokens or other terminal stop
                break

        return ""
