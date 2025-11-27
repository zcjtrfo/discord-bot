import ast
import operator
import re
# Assuming numbers_solver.py is importable
from numbers_solver import solve_numbers 
from itertools import combinations

# --- Existing normalize_expression (unchanged) ---
def normalize_expression(expr: str) -> str:
    # ... (content remains the same)
    expr = expr.lower()
    replacements = {
        "p": "+", "+": "+", "−": "-", "-": "-", "x": "*", "×": "*", "*": "*", 
        "÷": "/", "/": "/", "(": "(", "[": "(", "{": "(", ")": ")", "]": ")", "}": ")"
    }
    normalized = "".join(replacements.get(ch, ch) for ch in expr)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def parse_numbers_solution(guess: str, available_numbers: list[int]) -> tuple[int, str] | bool:
    """
    Validate and evaluate a Numbers game guess safely.

    MODIFIED: Handles composite numbers by recursively using the numbers_solver
    to find a construction from unused available numbers, and substitutes the
    composite number with the solver's expression before final evaluation.
    
    Returns (final_result, full_expression) on success, or False on failure.
    """

    # Allowed operations mapping (for safe_eval)
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
        # This safe_eval is for the final, fully-expanded expression.
        # It ensures all intermediate steps are positive integers.
        if isinstance(node, ast.Expression):
            return safe_eval(node.body)
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in ops: raise ValueError("Invalid operator.")
            left = safe_eval(node.left)
            right = safe_eval(node.right)
            if isinstance(node.op, ast.Div) and right == 0: raise ZeroDivisionError
            result = ops[type(node.op)](left, right)
            if not is_positive_integer_value(result):
                raise ValueError("Intermediate result must be a positive integer value.")
            return result
        elif isinstance(node, ast.UnaryOp):
            raise ValueError("Unary operators not allowed.")
        elif isinstance(node, (ast.Constant, ast.Num)):
            value = node.value if isinstance(node, ast.Constant) else node.n
            if not isinstance(value, int): raise ValueError("Only integer numbers are allowed.")
            if not is_positive_integer_value(value): raise ValueError("Numbers must be positive integers.")
            return float(value)
        else:
            raise ValueError(f"Invalid expression component: {type(node).__name__}.")

    # --- Step 1: Normalize input ---
    normalized_guess = normalize_expression(guess.strip())

    # --- Step 2: Identify and substitute composite numbers ---
    
    # Find all standalone numbers (literals) in the normalized expression
    literal_numbers = [
        int(n) for n in re.split(r"[+\-*/()]", normalized_guess) if n.strip().isdigit()
    ]
    
    temp_available = available_numbers.copy()
    
    # Map to store substitutions: { literal_number: (construction_expression, used_numbers_list) }
    substitutions = {}
    
    for n in literal_numbers:
        # 1. Check if the number is an original available number
        if n in available_numbers and n in temp_available:
            try:
                temp_available.remove(n)
                substitutions[n] = (str(n), [n])
            except ValueError:
                # Should not happen if `n in temp_available` is true, but ensures no double counting
                return False 
        
        # 2. Check if the number is already handled (e.g., appears multiple times)
        elif n in substitutions:
             # Already handled/checked; skip
             continue 

        # 3. This is a composite number: use the solver to find a valid construction
        else:
            found_construction = None
            used_by_solver = None
            
            # The solver works best when given a subset of numbers.
            # We must use a subset of `temp_available` to find the solution.
            
            # Search for a construction using combinations of the remaining numbers,
            # starting with 2 and increasing up to the total remaining size.
            
            for k in range(2, len(temp_available) + 1):
                for subset in combinations(temp_available, k):
                    # Call the full solver on the subset
                    solver_result = solve_numbers(n, list(subset))
                    
                    if solver_result["difference"] == 0:
                        # Found an exact construction!
                        # The solver's `expr` is the construction string, e.g., '100 + 50'
                        construction_expr = solver_result["results"][0][1]
                        used_by_solver = list(subset)
                        found_construction = construction_expr
                        break # Found for this number n
                if found_construction:
                    break

            if found_construction:
                # Successfully found construction. Now update the available numbers pool.
                for used_n in used_by_solver:
                    try:
                        temp_available.remove(used_n)
                    except ValueError:
                        # This means the solver returned numbers that were already used elsewhere,
                        # which shouldn't happen if subsetting was correct, but is a safety check.
                        return False 

                # Store the substitution using the solver's full expression
                substitutions[n] = (f"({found_construction})", used_by_solver)
            else:
                # Cannot construct this composite number from available set
                return False

    # --- Step 3: Create the final, fully expanded expression string ---
    
    full_expression = normalized_guess
    
    # Replace literals with their construction expressions.
    # Must replace longest numbers first (e.g., 150 before 15)
    sorted_literals = sorted(substitutions.keys(), key=lambda x: len(str(x)), reverse=True)
    
    for literal in sorted_literals:
        # Use regex to match the whole number only, surrounded by operators/brackets/start/end
        pattern = r"(?<=[+\-*/()]|^)" + re.escape(str(literal)) + r"(?=[+\-*/()]|$)"
        replacement_str = substitutions[literal][0]
        full_expression = re.sub(pattern, replacement_str, full_expression)
        
    # --- Step 4: Final evaluation of the expanded expression ---
    try:
        # The solver's expression uses '×' and '/', but AST needs '*' and '/'.
        # We must normalize the solver's output before parsing.
        # Since `normalize_expression` is only designed to handle user input, 
        # let's manually replace the solver's '×' with '*' in the final expression
        # and re-run the whole normalization for safety.
        
        # NOTE: If we modify `numbers_solver.py` to use '*' instead of '×',
        # this step is unnecessary. Assuming we can't modify the solver file:
        full_expression_for_eval = normalize_expression(full_expression.replace('×', '*'))
        
        tree = ast.parse(full_expression_for_eval, mode='eval')
        final_result = safe_eval(tree)
    except (SyntaxError, ValueError, ZeroDivisionError) as e:
        # print(f"Final Eval Error: {e}") # for debugging
        return False

    if not is_positive_integer_value(final_result):
        return False

    # Return the result AND the readable, fully expanded string
    return int(round(final_result)), full_expression
