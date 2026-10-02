---
name: calculator
description: >
    Evaluates mathematical expressions safely, covering arithmetic, powers, roots, trigonometric
    functions, and mathematical constants. Use this skill whenever the user asks to calculate,
    compute, evaluate, or solve a numeric expression (e.g. "what is 2^10?", "calculate sqrt(144) + sin(pi/2)").
---

# Calculator Skill

Evaluates a mathematical expression using a safe AST-based evaluator (no raw `eval` on untrusted input)
and returns the numeric result.

## Quick Start

Run the script with the expression as a single command-line argument:

```
python /skills/calculator/scripts/calculate.py "<expression>"
```

Example:

```
python /skills/calculator/scripts/calculate.py "2^10 + sqrt(144)"
```

## Supported Operations

- Arithmetic: `+`, `-`, `*`, `/`
- Power / exponentiation: `^` or `**` (e.g. `2^10`)
- Floor division and modulo: `//`, `%`
- Trigonometric functions: `sin(x)`, `cos(x)`, `tan(x)`
- Other functions: `sqrt(x)`, `abs(x)`, `round(x)`, `floor(x)`, `ceil(x)`, `log(x)`, `log10(x)`
- Mathematical constants: `pi`, `e`
- Grouping with parentheses: `(...)`

## Workflow

1. Take the user's request and translate it into a single valid math expression using the operators above.
2. Run the Quick Start command, passing the expression as the argument (quote it so the shell treats it as one
   argument).
3. Read the script's output — it prints the normalized expression and the result on separate lines.
4. Report the final numeric result to the user. If the script prints an `Error:` line (e.g. division by zero,
   unknown name, invalid syntax), explain the error instead of guessing a result.