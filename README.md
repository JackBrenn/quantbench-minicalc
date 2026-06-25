# QuantBench-1200 · MiniCalc Challenge

*Built by Anthropic Fable 5.*

A hard, deterministic single-file coding task for probing how much a quantization
degrades a model. Fully auto-graded — no human grader in the loop.

Built to test local AI deploymemnts.

## What it measures

This is a high-variance capability stress test, not a clean readout of "quant quality."
In validation, run-to-run spread (±7–9) exceeded the gap between quant configs (~2), so
a single score — or even a mean — is mostly noise.

Quantization damage tends to appear as occasional catastrophic runs rather than a lower
average. The signal is therefore the **floor**: the worst result over many runs. A Q4
build often has a much lower floor than BF16 even when typical runs look similar.

The task is also dense enough to serve as a general capability probe across different
models.

## The challenge

Implement **MiniCalc**, a complete expression language, in a single Python file (≤1200
lines, stdlib only, exact integer math — no floats). It covers a fixed-point decimal
engine with banker's rounding, a hand-written tokenizer/parser, two execution engines
that must agree, exact error formats with positions, and a self-test mode. A deliberate
rule-vs-example contradiction tests whether the model follows the spec or anchors on the
worked example. The exact-integer core is where a degrading quant surfaces first, as
off-by-one or rounding drift.

## Usage

1. Paste the **Challenge Prompt** section of `minicalc-challenge.md` into a model in a
   fresh context.
2. Save the output as a `.py` file.
3. Grade it:

   ```bash
   python3 grade_minicalc.py solution.py [solution2.py ...]
   ```

The grader runs ~45 behavioral and static checks across 9 categories and prints a
per-category score table (max 100), plus a comparison table for multiple solutions.

## Reading the results

- Run ≥5–10 times per config and compare worst-case behavior, not single scores.
- A new failure in Categories 1–2 (fixed-point arithmetic / banker's rounding) is the
  strongest sign of genuine weight-quant degradation; it never occurred in validation.
- Category 4 (engine equivalence) is static heuristics and can be passed without the two
  engines truly agreeing — spot-check it by hand.
- The golden values and the trap answer (`2.000001`) are memorizable, which limits use as
  a general benchmark but is harmless when comparing quants of one base model.

## Files

- `minicalc-challenge.md` — challenge, verbatim prompt, and grading rubric
- `grade_minicalc.py` — automated grader (standard library only)

## Credits

Designed and built by **Anthropic Fable 5**.
