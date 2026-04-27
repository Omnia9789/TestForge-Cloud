import logging
import json
import azure.functions as func
from core.prompt import build_prompt
from core.generator import generate_tests
from core.parser import validate_syntax

logger = logging.getLogger(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("TestForge: received test generation request")

    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    try:
        body = req.get_json()
    except ValueError:
        return _error("Invalid JSON body", 400)

    code = body.get("code", "").strip()
    framework = body.get("framework", "pytest")
    include_edge_cases = body.get("include_edge_cases", True)

    if not code:
        return _error("'code' field is required", 400)

    if len(code) > 10_000:
        return _error("Code exceeds 10,000 character limit", 400)

    try:
        prompt = build_prompt(code, framework=framework, include_edge_cases=include_edge_cases)
        result = generate_tests(prompt)

        is_valid, syntax_error = validate_syntax(result["tests"])
        if not is_valid:
            logger.warning(f"Generated tests failed syntax validation: {syntax_error}")

        payload = {
            "tests": result["tests"],
            "status": "success",
            "tokens_used": result.get("tokens_used", 0),
            "syntax_valid": is_valid,
            "model": result.get("model", "unknown"),
            "mock_mode": result.get("mock_mode", False),
        }

        return func.HttpResponse(
            body=json.dumps(payload),
            mimetype="application/json",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    except Exception as exc:
        logger.exception("Unhandled error in test generation")
        return _error(f"Internal server error: {str(exc)}", 500)


def _error(message: str, status: int) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps({"status": "error", "message": message}),
        mimetype="application/json",
        status_code=status,
        headers={"Access-Control-Allow-Origin": "*"},
    )
