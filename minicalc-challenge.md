# QuantBench-1200 · MiniCalc Challenge (v2, validated)

A quantization-discriminating coding challenge. Validated across 10 real submissions
(NVFP4+FP8-KV, FP16-KV). Paste the **Challenge Prompt** section verbatim into each
model in a fresh context, save the output as a `.py` file, then score it with
`grade_minicalc.py` (no human grader needed).

> **⚠️ DELIBERATE TRAP — do not "fix" this:** The worked example in Part D claims
> `sqrt(2) ^ 2` prints `1.999998`. That value **contradicts** the rounding rule and
> the Part A example (`sqrt(2)` → `1.414214`, so the true answer is `2.000001`).
> This contradiction is intentional: it tests whether the model follows the **stated
> rule** or anchors on the **worked example**. Across 10 validation runs, ~40% of
> submissions anchored on the example and built a truncating sqrt to match it — the
> single most discriminating probe in the benchmark. The grader scores `2.000001`
> as correct.

---

# THE CHALLENGE PROMPT (paste everything between the lines, verbatim)

---

You must write a **single Python 3.11 file** named `minicalc.py` implementing a complete
expression language called **MiniCalc**. Hard limits:

- **Maximum 1200 lines** (including blanks and comments).
- **Standard library only**, and you may **NOT** import or use: `decimal`, `fractions`,
  `ctypes`, `numpy`, `eval`, `exec`, or `compile` (the builtin). You may not use Python
  `float` anywhere in the arithmetic core — all math must be exact integer math.
- Fully deterministic: same input → byte-identical output, every run.

## Part A — Fixed-point decimal engine (class `FixedPoint`)

All MiniCalc numbers are fixed-point decimals with **scale = 6** (six fractional digits),
stored internally as a Python `int` of micro-units (e.g., `1.5` → `1500000`).

Required operations: `add`, `sub`, `mul`, `div`, `neg`, `abs`, `pow_int` (integer
exponents only, including negative), `sqrt` (integer Newton's method), and comparison.

**Rounding rule (applies to mul, div, sqrt, pow_int with negative exponents):**
round-half-to-even (**banker's rounding**) at the 6th fractional digit.
Examples your engine MUST reproduce:

- `0.0000005` rounds to `0.000000`
- `0.0000015` rounds to `0.000002`
- `1 / 3` → `0.333333`
- `2 / 3` → `0.666667`
- `sqrt(2)` → `1.414214`
- `10 / 4` → `2.500000` (exact, no rounding needed)

Division by zero must raise the MiniCalc runtime error defined in Part E.

**String formatting rule:** always print exactly six fractional digits, no exponent
notation, with `-` for negatives and no `+` for positives (e.g., `-0.500000`, `42.000000`).

## Part B — Tokenizer and parser

Implement a hand-written tokenizer and **recursive-descent parser** (no regex for the
tokenizer's core loop; character-by-character scanning) for this grammar:

```
program    := statement (";" statement)* [";"]
statement  := "let" IDENT "=" expr | expr
expr       := term (("+" | "-") term)*
term       := unary (("*" | "/" | "%") unary)*
unary      := "-" unary | power
power      := atom ["^" unary]            # right-associative; binds tighter than unary minus
atom       := NUMBER | IDENT | call | "(" expr ")"
call       := IDENT "(" [expr ("," expr)*] ")"
```

Notes you must honor:

- `^` is exponentiation, **right-associative**: `2 ^ 3 ^ 2` = `2 ^ (3 ^ 2)` = `512`.
- Unary minus binds **looser** than `^`: `-2 ^ 2` = `-(2^2)` = `-4.000000`.
- `%` is modulo with the sign of the divisor (Python semantics), exact at scale 6.
- `^` only accepts exponents that are whole numbers at scale 6 (fractional exponent →
  runtime error `E301`).
- Built-in functions: `sqrt(x)`, `abs(x)`, `min(a,b)`, `max(a,b)`, `floor(x)`, `ceil(x)`.
- Numbers: digits with optional single `.` and up to 6 fractional digits; a 7th
  fractional digit in a literal is a **syntax error**, not silently rounded.
- Identifiers: `[a-zA-Z_][a-zA-Z0-9_]*`. `let` is reserved.
- Statements MUST be separated by `;`. Two statements without a separator (e.g. `1 2`)
  is a **syntax error** — never silently accept or discard trailing tokens.
- Every token records 1-based `line` and `col`; every AST node carries the position of
  its first token (needed for error reporting in Part E).

## Part C — Two execution engines that must agree

1. **Tree-walking interpreter** — evaluates the AST directly.
2. **Bytecode compiler + stack VM** — compile the AST to your own bytecode
   (opcodes: `PUSH_CONST`, `LOAD_VAR`, `STORE_VAR`, `ADD`, `SUB`, `MUL`, `DIV`, `MOD`,
   `NEG`, `POW`, `CALL_FN`) and execute it on a stack machine. `let` statements must
   compile to bytecode ending in `STORE_VAR` — do not handle variable storage outside
   the VM.

For every statement, the program runs **both** engines and must verify the results are
identical; if they ever differ, print `ENGINE MISMATCH` and exit with code 3.
(A correct solution never triggers this — but the harness checks it exists.)
Error behavior must also agree: both engines must raise the same error codes for the
same failing inputs, including `E301` checks inside the VM's `POW` opcode.

`let` bindings persist across statements within one program. Using an undefined
variable is runtime error `E302`.

## Part D — CLI behavior (exact)

- `python minicalc.py "expr-program"` → evaluate the argument.
- `python minicalc.py` (no args) → read the whole program from stdin.
- For each **expression statement**, print one line: the formatted result, **as soon as
  that statement completes** — if a later statement errors, output from earlier
  successful statements must already have been printed.
- `let` statements print nothing.
- On success, exit code `0`.

Example: `python minicalc.py "let x = 1/3; x * 3; sqrt(2) ^ 2"` prints:

```
0.999999
1.999998
```

## Part E — Error handling (exact formats, exit code 2)

All errors — including any internal arithmetic exception on any path (e.g. `1 % 0`,
`0 ^ -1`) — print **one line to stderr** and exit with code `2`. A raw Python
traceback on any input is a failure.

- Syntax errors:  `SyntaxError[L{line}:C{col}]: {message}`
- Runtime errors: `RuntimeError[L{line}:C{col}][{code}]: {message}`

Runtime error codes: `E300` division by zero (including modulo by zero and zero to a
negative power) · `E301` non-integer exponent · `E302` undefined variable · `E303`
sqrt of negative · `E304` wrong argument count to a builtin · `E305` unknown function.

The `{line}:{col}` must point at the **operator or call site** that failed
(e.g., for `1/0` the position of `/`; for `foo(1)` the position of `foo`). Positions
must never be placeholder values like `L0:C0`.

## Part F — Self-test

The file must end with a `--selftest` mode (`python minicalc.py --selftest`) that runs
at least 30 internal assertions covering Parts A–E (including at least 4 banker's-rounding
edge cases and at least 3 byte-exact error-string checks) and prints exactly `SELFTEST OK`
— that line and nothing else on stdout — with exit code 0 on success.

**Final reminder of constraints from the top:** ≤1200 lines, no `decimal`/`fractions`/
`eval`/`exec`/float-math, character-by-character tokenizer, both engines verified
against each other on every statement, no raw tracebacks on any input.

---

# END OF CHALLENGE PROMPT

---

## Grading

Run: `python3 grade_minicalc.py solution1.py [solution2.py ...]`

The grader runs ~45 behavioral checks per solution and prints the category table
(max 100 points). Categories (deliberately matching the manual rubric used during
validation):

| # | Category | Pts | What the grader runs |
|---|----------|-----|----------------------|
| 1 | Fixed-point arithmetic | 18 | Golden value tests G1–G10 |
| 2 | Banker's rounding edges | 10 | Four tie cases + the sqrt boundary counterexample `sqrt(0.008248)` → `0.090819` |
| 3 | Parser & precedence | 12 | `2^3^2`, `-2^2`, `%` sign rule, 7-digit literal, missing-`;` rejection, `let` reserved |
| 4 | Engine equivalence | 12 | Heuristic static checks: `ENGINE MISMATCH` string, exit-3 path, named opcodes present |
| 5 | Exact error formats | 12 | Byte-exact E300–E305 strings with positions; `1 % 0` and `0 ^ -1` must not traceback or report `L0:C0` |
| 6 | Constraint compliance | 12 | Line cap, banned imports, float/regex heuristics, determinism |
| 7 | CLI & I/O contract | 8 | Arg + stdin modes, silent `let`, **incremental output** (`"2; 1/0"` must print `2.000000` first), exit codes |
| 8 | Self-test quality | 8 | Runs `--selftest`, requires exactly `SELFTEST OK`, counts assertions (≥30) |
| 9 | Long-range spec fidelity | 8 | The rule-vs-example trap (`sqrt(2)^2` = `2.000001`), E301 position at the `^`, modulo sign |

Notes:
- Category 4 is the one category that can't be fully verified behaviorally without
  fault injection; the grader uses static heuristics there. Spot-check manually if a
  solution scores full marks but looks suspicious.
- Categories 1, 2, and 9 intentionally overlap on sqrt: a truncating sqrt is a
  multi-category failure (wrong values + wrong rounding + example-anchoring), matching
  how the validation runs were scored.

## Validation baselines (same model, 10 runs)

| Config | Scores (manual grading) | Mean |
|---|---|---|
| NVFP4 weights + FP8 KV (model A) | 96, 95, 80 | 90.3 |
| NVFP4 weights + FP8 KV (model B) | 96, 86, 94, 92 | 92.0 |
| NVFP4 weights + FP16 KV (model A) | 86, 98, 84 | 89.3 |

Within-config spread (±7–9) exceeded between-config gaps (~2), i.e. FP8 KV cache was
free at this model scale. Use ≥3 runs per config and compare distributions, never
single scores. A *new* failure class on the golden path (categories 1–2) is the
signal that a weight quant is genuinely degrading — it never occurred in validation.