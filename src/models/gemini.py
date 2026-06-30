from google import genai
from google.genai import types

from src.core.llm import LLM

_TYPE_MAP = {
    "object": "OBJECT",
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
}


def _to_schema(schema: dict) -> types.Schema:
    """Recursively convert JSON Schema dict to google-genai Schema."""
    kwargs = {}
    if "type" in schema:
        kwargs["type"] = _TYPE_MAP.get(schema["type"], schema["type"].upper())
    if "description" in schema:
        kwargs["description"] = schema["description"]
    if "enum" in schema:
        kwargs["enum"] = schema["enum"]
    if "properties" in schema:
        kwargs["properties"] = {k: _to_schema(v) for k, v in schema["properties"].items()}
    if "required" in schema:
        kwargs["required"] = schema["required"]
    if "minimum" in schema:
        kwargs["minimum"] = float(schema["minimum"])
    if "maximum" in schema:
        kwargs["maximum"] = float(schema["maximum"])
    return types.Schema(**kwargs)


class GeminiModel(LLM):
    """Google Gemini backend via google-genai SDK."""

    def __init__(self, model: str, api_key: str | None = None):
        super().__init__(model, api_key)
        self._client = genai.Client(api_key=api_key)

    def chat(self, messages: list[dict], **kwargs) -> str:
        system = kwargs.pop("system", None)
        max_tokens = kwargs.pop("max_tokens", 1024)
        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            system_instruction=system,
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=self._to_contents(messages),
            config=config,
        )
        return response.text

    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        if system:
            kwargs["system"] = system
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def run_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_handler,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Agentic loop using Gemini function calling. tools must use Anthropic input_schema format."""
        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            system_instruction=system,
            tools=[self._to_gemini_tools(tools)],
        )
        contents = self._to_contents(messages)

        while True:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            candidate = response.candidates[0]
            parts = candidate.content.parts
            fn_calls = [p for p in parts if p.function_call is not None]

            if not fn_calls:
                return "\n".join(p.text for p in parts if hasattr(p, "text") and p.text)

            contents.append(candidate.content)

            results = []
            for part in fn_calls:
                fc = part.function_call
                result = tool_handler(fc.name, dict(fc.args))
                results.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": str(result)},
                    )
                ))
            contents.append(types.Content(role="user", parts=results))

    def _to_contents(self, messages: list[dict]) -> list[types.Content]:
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]
            if isinstance(content, str):
                contents.append(types.Content(role=role, parts=[types.Part(text=content)]))
            else:
                contents.append(types.Content(role=role, parts=content))
        return contents

    def _to_gemini_tools(self, tools: list[dict]) -> types.Tool:
        decls = [
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=_to_schema(t["input_schema"]),
            )
            for t in tools
        ]
        return types.Tool(function_declarations=decls)
