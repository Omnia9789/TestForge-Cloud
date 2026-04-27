"""
core/prompt.py — Builds the structured system prompt for GPT-4o test generation.
"""

SYSTEM_PROMPT = """You are TestForge, an expert Python test engineer.
Your ONLY job is to generate complete, runnable Pytest test files.

Rules:
- Output ONLY valid Python code. No markdown fences, no explanation.
- Always include: `import pytest` and any imports needed by the code under test.
- Every test function must start with `test_`.
- Cover: happy path, edge cases, type errors, boundary values.
- Use `@pytest.mark.parametrize` for data-driven cases.
- Use `pytest.raises` for exception tests.
- Add docstrings to each test explaining what it verifies.
- Assume the code under test can be imported from a module named after its filename.
  If no filename is given, use `from solution import *` at the top.
- Do NOT use unittest. Pure pytest only.
"""


def build_prompt(
    code: str,
    framework: str = "pytest",
    include_edge_cases: bool = True,
) -> list[dict]:
    """
    Returns the messages list to send to the OpenAI chat completions API.
    """
    edge_case_instruction = (
        "\nMake sure to include comprehensive edge cases, boundary tests, "
        "and negative test scenarios." if include_edge_cases else ""
    )

    user_message = (
        f"Generate a complete {framework} test file for the following Python code."
        f"{edge_case_instruction}\n\n"
        f"```python\n{code}\n```"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
