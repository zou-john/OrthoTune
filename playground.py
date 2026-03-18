import os

from dotenv import load_dotenv

from src.core.llm import create_llm
from src.core.entry import LLMEntry, LLMResponse

load_dotenv()

llm = create_llm("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

entry = LLMEntry(id="example", prompt="Hello, who are you?")
response = LLMResponse(entry=entry, response=llm.complete(entry.prompt))
print(response.response)
