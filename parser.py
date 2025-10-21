import ast
import operator

def parse_numbers_solution(guess: str, available_numbers: list[int]) -> int | bool:
    """
    Validate and evaluate a Numbers game guess safely.

    Rules:
    1) Only +, -, *, / allowed.
    2) All intermediate results must be positive integers (exact integer values).
    3) Only numbers from the available set may be used, each at most once.
    4) Parentheses allowed for grouping.
    5) If invalid, return False. Otherwise return final integer result.
    """

    # Allowed operations mapping
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    def is_integer_value(x: float) -> bool:
        """Return True if x is mathematically an integer."""
        return abs(x - round(x)) < 1e-9

    def is_positive_integer_value(x: float) -> bool:
        """Return True if x is a positive integer (mathematically)."""
        return x > 0 and is_integer_value(x)

    def safe_eval(node):
        """Recursively evaluate AST nodes enforcing Countdown rules."""
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

        elif hasattr(ast, "Num") and isinstance(node, ast.Num):  # backward compat
            if not is_positive_integer_value(node.n):
                raise ValueError("Numbers must be positive integers.")
            return float(node.n)

        else:
            raise ValueError("Invalid expression component.")

    # Normalize and extract used numbers
    guess = guess.strip()
    if not guess:
        return False

    # Only allow digits, operators, parentheses, and spaces
    if not all(ch.isdigit() or ch in "+-*/() " for ch in guess):
        return False

    # Extract used numbers
    used_numbers = [
        int(n) for n in guess.replace('(', ' ').replace(')', ' ')
        .replace('+', ' ').replace('-', ' ')
        .replace('*', ' ').replace('/', ' ').split()
        if n.isdigit()
    ]

    # Validate number usage
    temp_numbers = available_numbers.copy()
    for n in used_numbers:
        if n in temp_numbers:
            temp_numbers.remove(n)
        else:
            return False

    # Evaluate safely
    try:
        tree = ast.parse(guess, mode='eval')
        result = safe_eval(tree)
    except (SyntaxError, ValueError, ZeroDivisionError):
        return False

    if not is_positive_integer_value(result):
        return False

    return int(round(result))
