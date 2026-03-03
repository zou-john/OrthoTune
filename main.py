import json
import os
import textwrap
from src.scipdf_parser import PDFParser
from src.llm import create_llm

from dotenv import load_dotenv
load_dotenv()

llm = create_llm("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))                                                                      
llm_response = llm.complete(prompt="what is the captial of China", system="you are a helpful medical assistant")                                  
print(llm_response)
# PDF_PATH = "data/systematic_review_3.pdf"
# WRAP_WIDTH = 115

# def wrap_strings(obj):
#     """Recursively wrap long strings in a dict/list at WRAP_WIDTH characters."""
#     if isinstance(obj, dict):
#         return {k: wrap_strings(v) for k, v in obj.items()}
#     if isinstance(obj, list):
#         return [wrap_strings(item) for item in obj]
#     if isinstance(obj, str) and len(obj) > WRAP_WIDTH:
#         return "\n".join(textwrap.wrap(obj, width=WRAP_WIDTH))
#     return obj

# p = PDFParser(PDF_PATH)
# print(p.title)
# print(p.abstract)
# methods = p.get_section("methods")
# print(p.summary())

# os.makedirs("output", exist_ok=True)
# output_filename = os.path.splitext(os.path.basename(PDF_PATH))[0] + ".json"
# output_path = os.path.join("output", output_filename)
# json_str = json.dumps(wrap_strings(p.data), indent=2)
# json_str = json_str.replace("\\n", "\n")
# with open(output_path, "w") as f:
#     f.write(json_str)
# print(f"\nOutput saved to {output_path}")


