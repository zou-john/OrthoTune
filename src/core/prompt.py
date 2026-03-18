LIMITATIONS_TEMPLATE = """You are an orthopedic researcher critically evaluating a study.

Given the title and full text below, identify the limitations of this study.

Focus ONLY on limitations that affect the interpretation of the results (e.g. study design flaws, small sample size, selection bias, confounding variables, short follow-up, lack of control group, measurement issues).

Do NOT include:
- Suggestions for future work
- Strengths of the study
- General observations unrelated to result interpretation

Title: {title}

Full Text:
{full_text}

Provide a concise paragraph summarizing only the relevant limitations."""


def build_limitations_prompt(title: str, full_text: str) -> str:
    return LIMITATIONS_TEMPLATE.format(title=title, full_text=full_text)
