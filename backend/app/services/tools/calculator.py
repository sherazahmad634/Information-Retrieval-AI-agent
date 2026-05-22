"""Safe arithmetic calculator tool.

Implemented via :mod:`ast` parsing so that arbitrary code execution is
impossible — only a whitelisted subset of numeric Python is permitted.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from app.services.tools.base import Tool, ToolError, ToolResult

_BINOPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARYOPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_FUNCS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
}

_ALLOWED_CONSTS: dict[str, Any] = {"pi": math.pi, "e": math.e}


class CalculatorTool(Tool):
    """Evaluate a numeric expression. No variables, no side effects."""

    name = "calculator"
    description = (
        "Evaluate a numeric expression. Supports + - * / ** % // and the functions "
        "sqrt, log, log2, log10, exp, sin, cos, tan, abs, round, min, max, plus the "
        "constants pi and e. Use this whenever the user asks for arithmetic, unit "
        "conversion, or other deterministic calculation — do not guess."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "A pure numeric Python expression, e.g. '2 * (3 + 4)' or 'sqrt(2)'.",
            }
        },
        "required": ["expression"],
        "additionalProperties": False,
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        expression = kwargs.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            raise ToolError("`expression` is required.")
        try:
            tree = ast.parse(expression, mode="eval")
            result = _eval_node(tree.body)
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(f"Invalid expression: {exc}") from exc
        return ToolResult(
            content=f"{expression} = {result}",
            data={"expression": expression, "result": result},
        )


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate an AST node using only whitelisted operations."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ToolError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_CONSTS:
            return float(_ALLOWED_CONSTS[node.id])
        raise ToolError(f"Unknown identifier: {node.id}")
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise ToolError(f"Operator not allowed: {type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _UNARYOPS.get(type(node.op))
        if op is None:
            raise ToolError(f"Unary operator not allowed: {type(node.op).__name__}")
        return op(_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise ToolError("Only whitelisted math functions are allowed.")
        args = [_eval_node(a) for a in node.args]
        return float(_ALLOWED_FUNCS[node.func.id](*args))
    raise ToolError(f"Unsupported node: {type(node).__name__}")
