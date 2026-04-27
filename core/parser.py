"""
core/parser.py — Validates that AI-generated test code is syntactically correct Python.
Uses ast.parse() so no code is ever executed during validation.
"""

import ast
import re
import logging

logger = logging.getLogger(__name__)


def validate_syntax(code: str) -> tuple[bool, str | None]:
    """
    Parse the generated test code without executing it.

    Returns:
        (True, None)         — code is syntactically valid
        (False, error_msg)   — syntax error with description
    """
    if not code or not code.strip():
        return False, "Empty code string"

    try:
        ast.parse(code)
        return True, None
    except SyntaxError as exc:
        error_msg = f"SyntaxError at line {exc.lineno}: {exc.msg}"
        logger.warning(f"Syntax validation failed: {error_msg}")
        return False, error_msg


def extract_test_functions(code: str) -> list[str]:
    """
    Returns a list of test function names found in the generated code.
    Useful for reporting how many tests were generated.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]


def count_parametrize_cases(code: str) -> int:
    """
    Counts the number of @pytest.mark.parametrize entries across all test functions.
    Useful for coverage reporting.
    """
    pattern = r"@pytest\.mark\.parametrize\(\s*[\"'][^\"']+[\"']\s*,\s*\[([^\]]+)\]"
    total = 0
    for match in re.finditer(pattern, code, re.DOTALL):
        cases_block = match.group(1)
        # Count tuple entries: each (x, y, ...) is one case
        total += len(re.findall(r"\(", cases_block))
    return total
