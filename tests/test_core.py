"""
tests/test_core.py — Unit tests for TestForge Cloud core logic.

Run with: pytest tests/ -v
Run with coverage: python -m core.coverage
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompt import build_prompt
from core.parser import validate_syntax, extract_test_functions, count_parametrize_cases
from core.generator import _mock_response


# =============================================================================
# core/prompt.py tests
# =============================================================================

class TestBuildPrompt:
    def test_returns_list_of_messages(self):
        """build_prompt returns a list."""
        result = build_prompt("def add(a, b): return a + b")
        assert isinstance(result, list)

    def test_has_system_and_user_roles(self):
        """Messages include both system and user roles."""
        result = build_prompt("def foo(): pass")
        roles = [m["role"] for m in result]
        assert "system" in roles
        assert "user" in roles

    def test_user_message_contains_code(self):
        """The user message includes the submitted code."""
        code = "def multiply(a, b): return a * b"
        result = build_prompt(code)
        user_msg = next(m for m in result if m["role"] == "user")
        assert code in user_msg["content"]

    def test_edge_cases_flag_true(self):
        """When include_edge_cases=True, prompt mentions edge cases."""
        result = build_prompt("def add(a, b): return a + b", include_edge_cases=True)
        user_msg = next(m for m in result if m["role"] == "user")
        assert "edge" in user_msg["content"].lower()

    def test_edge_cases_flag_false(self):
        """When include_edge_cases=False, edge case instruction is omitted."""
        result = build_prompt("def add(a, b): return a + b", include_edge_cases=False)
        user_msg = next(m for m in result if m["role"] == "user")
        assert "edge" not in user_msg["content"].lower()

    def test_framework_included_in_prompt(self):
        """The specified framework name appears in the user message."""
        result = build_prompt("def f(): pass", framework="pytest")
        user_msg = next(m for m in result if m["role"] == "user")
        assert "pytest" in user_msg["content"].lower()

    def test_system_prompt_instructs_no_markdown(self):
        """System prompt explicitly tells model not to use markdown fences."""
        result = build_prompt("def f(): pass")
        system_msg = next(m for m in result if m["role"] == "system")
        assert "markdown" in system_msg["content"].lower() or "```" in system_msg["content"]


# =============================================================================
# core/parser.py tests
# =============================================================================

VALID_TESTS = """\
import pytest

def test_add_basic():
    assert 1 + 1 == 2

def test_add_zero():
    assert 0 + 0 == 0

@pytest.mark.parametrize("a, b, expected", [(1, 2, 3), (0, 0, 0), (-1, 1, 0)])
def test_add_parametrize(a, b, expected):
    assert a + b == expected
"""

INVALID_TESTS = """\
def test_broken(
    assert True  # missing closing paren
"""


class TestValidateSyntax:
    def test_valid_code_passes(self):
        """Well-formed Python passes validation."""
        is_valid, error = validate_syntax(VALID_TESTS)
        assert is_valid is True
        assert error is None

    def test_invalid_code_fails(self):
        """Syntactically broken code returns False with an error message."""
        is_valid, error = validate_syntax(INVALID_TESTS)
        assert is_valid is False
        assert error is not None
        assert "SyntaxError" in error

    def test_empty_string_fails(self):
        """Empty string is not valid."""
        is_valid, error = validate_syntax("")
        assert is_valid is False

    def test_whitespace_only_fails(self):
        """Whitespace-only string is not valid."""
        is_valid, error = validate_syntax("   \n\t  ")
        assert is_valid is False

    def test_simple_expression_is_valid(self):
        """A minimal expression is valid Python."""
        is_valid, _ = validate_syntax("x = 1")
        assert is_valid is True

    @pytest.mark.parametrize("code", [
        "def test_foo(): pass",
        "import pytest\ndef test_bar():\n    assert True",
        "class TestSuite:\n    def test_method(self):\n        pass",
    ])
    def test_valid_test_patterns(self, code):
        """Various valid pytest patterns pass validation."""
        is_valid, _ = validate_syntax(code)
        assert is_valid is True


class TestExtractTestFunctions:
    def test_finds_all_test_functions(self):
        """Correctly identifies all test_ prefixed functions."""
        names = extract_test_functions(VALID_TESTS)
        assert "test_add_basic" in names
        assert "test_add_zero" in names
        assert "test_add_parametrize" in names

    def test_returns_empty_on_syntax_error(self):
        """Returns empty list when code has syntax errors."""
        result = extract_test_functions(INVALID_TESTS)
        assert result == []

    def test_ignores_non_test_functions(self):
        """Functions not starting with test_ are excluded."""
        code = "def helper(): pass\ndef test_real(): pass"
        names = extract_test_functions(code)
        assert "helper" not in names
        assert "test_real" in names

    def test_empty_code(self):
        """Returns empty list for empty input."""
        assert extract_test_functions("") == []


class TestCountParametrizeCases:
    def test_counts_parametrize_entries(self):
        """Correctly counts tuple entries in parametrize decorator."""
        count = count_parametrize_cases(VALID_TESTS)
        assert count == 3  # (1,2,3), (0,0,0), (-1,1,0)

    def test_returns_zero_when_no_parametrize(self):
        """Returns 0 when no parametrize decorators are present."""
        code = "def test_basic():\n    assert True"
        assert count_parametrize_cases(code) == 0


# =============================================================================
# core/generator.py — mock mode tests (no API key needed)
# =============================================================================

class TestMockGenerator:
    def test_mock_returns_dict_with_required_keys(self):
        """Mock response includes all required keys."""
        messages = [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "Generate tests for:\ndef add(a, b): return a + b"},
        ]
        result = _mock_response(messages)
        assert "tests" in result
        assert "tokens_used" in result
        assert "model" in result
        assert "mock_mode" in result

    def test_mock_mode_flag_is_true(self):
        """mock_mode flag is True in mock responses."""
        result = _mock_response([{"role": "user", "content": "def f(): pass"}])
        assert result["mock_mode"] is True

    def test_mock_tests_are_valid_python(self):
        """Mock-generated tests are syntactically valid Python."""
        result = _mock_response([{"role": "user", "content": "def add(a, b): return a + b"}])
        is_valid, error = validate_syntax(result["tests"])
        assert is_valid, f"Mock tests have syntax error: {error}"

    def test_mock_tests_contain_pytest_patterns(self):
        """Mock tests follow pytest conventions."""
        result = _mock_response([{"role": "user", "content": "def multiply(a, b): return a*b"}])
        tests = result["tests"]
        assert "import pytest" in tests
        assert "def test_" in tests

    def test_mock_detects_function_name(self):
        """Mock output is tailored to the function name in the submitted code."""
        result = _mock_response([
            {"role": "user", "content": "Generate tests for:\ndef fibonacci(n): return n"}
        ])
        assert "fibonacci" in result["tests"]

    def test_mock_tokens_used_is_zero(self):
        """Mock responses report 0 tokens used (no API calls)."""
        result = _mock_response([{"role": "user", "content": "def f(): pass"}])
        assert result["tokens_used"] == 0
