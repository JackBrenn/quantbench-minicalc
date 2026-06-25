# QuantBench-1200 · MiniCalc Challenge

*Built by Anthropic Fable 5.*

A quantization-discriminating coding benchmark. The task is hard enough that a
degraded (e.g. low-bit quantized) model fails it in measurable, auto-gradable ways
— with no human grader in the loop.

## The challenge

Models are asked to implement **MiniCalc**, a complete expression language, in a
single Python file (≤1200 lines, stdlib only, exact integer math — no floats). It
covers a fixed-point decimal engine with banker's rounding, a hand-written
tokenizer/parser, two execution engines that must agree, exact error formats, and a
self-test mode. One deliberate rule-vs-example contradiction probes whether a model
follows the stated spec or anchors on a worked example.

## Usage

1. Paste the **Challenge Prompt** section of `minicalc-challenge.md` into a model in a
   fresh context.
2. Save the model's output as a `.py` file.
3. Grade it:

   ```bash
   python3 grade_minicalc.py solution.py [solution2.py ...]
   ```

The grader runs ~45 behavioral and static checks across 9 categories and prints a
per-category score table (max 100), plus a comparison table for multiple solutions.

## Files

- `minicalc-challenge.md` — the challenge, the verbatim prompt, and the grading rubric
- `grade_minicalc.py` — automated grader (standard library only)

## Notes

Compare distributions, not single scores: use ≥3 runs per config, since within-config
spread can exceed between-config gaps. A new failure on the golden-path categories
(fixed-point arithmetic / banker's rounding) is the signal that a weight quant is
genuinely degrading.

## Credits

Designed and built by **Anthropic Fable 5**.
