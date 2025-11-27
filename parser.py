import ast
import operator
import re

# --- Move normalize_expression to top level ---
def normalize_expression(expr: str) -> str:
    """
    Normalize a math expression to a consistent, parseable form.
    Handles alternate operators and removes whitespace.
    """
    expr = expr.lower()  # case-insensitive
    replacements = {
        "p": "+",
        "+": "+",
        "−": "-",
        "-": "-",
        "x": "*",
        "×": "*",
        "*": "*",
        "÷": "/",
        "/": "/",
        "(": "(",
        "[": "(",
        "{": "(",
        ")": ")",
        "]": ")",
        "}": ")"
    }
    normalized = "".join(replacements.get(ch, ch) for ch in expr)
    normalized = re.sub(r"\s+", "", normalized)  # remove all spaces
    return normalized


def parse_numbers_solution(guess: str, available_numbers: list[int]) -> int | bool:
    """
    Validate and evaluate a Numbers game guess safely.

    Rules:
    1) Only +, -, *, / allowed.
       Accepts these equivalents:
         + : +, p, P
         - : -, −
         * : *, x, X, ×
         / : /, ÷
         brackets : (), {}, []
    2) All intermediate results must be positive integers.
    3) Only numbers from the available set may be used, each at most once.
    4) If invalid, return False. Otherwise return final integer result.
    5) Ignores all spaces in the input.
    """

    # Allowed operations mapping
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv
    }

    def is_integer_value(x):
        return abs(x - round(x)) < 1e-9

    def is_positive_integer_value(x):
        return x > 0 and is_integer_value(x)

    def safe_eval(node):
        if isinstance(node, ast.Expression):
            return safe_eval(node.body)

        elif isinstance(node, ast.BinOp):
            if type(node.op) not in ops:
                raise ValueError("Invalid operator.")
            left = safe_eval(node.left)
            right = safe_eval(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ZeroDivisionError
            result = ops[type(node.op)](left, right)
            if not is_positive_integer_value(result):
                raise ValueError("Intermediate result must be a positive integer value.")
            return result

        elif isinstance(node, ast.UnaryOp):
            raise ValueError("Unary operators not allowed.")

        elif isinstance(node, ast.Constant):  # Python 3.8+
            value = node.value
            if not is_positive_integer_value(value):
                raise ValueError("Numbers must be positive integers.")
            return float(value)

        elif isinstance(node, ast.Num):  # Python < 3.8
            if not is_positive_integer_value(node.n):
                raise ValueError("Numbers must be positive integers.")
            return float(node.n)

        else:
            raise ValueError("Invalid expression component.")

    # Step 1: normalize input
    guess = normalize_expression(guess.strip())

    # Step 2: extract used numbers
    used_numbers = [
        int(n) for n in re.split(r"[+\-*/()]", guess) if n.strip().isdigit()
    ]

    # Check number count and valid usage
    if len(used_numbers) > len(available_numbers):
        return False

    temp_numbers = available_numbers.copy()
    for n in used_numbers:
        if n in temp_numbers:
            temp_numbers.remove(n)
        else:
            return False

    # Step 3: parse and evaluate safely
    try:
        tree = ast.parse(guess, mode='eval')
        result = safe_eval(tree)
    except (SyntaxError, ValueError, ZeroDivisionError):
        return False

    if not is_positive_integer_value(result):
        return False

    return int(round(result))
