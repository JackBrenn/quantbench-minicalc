# QuantBench-1200 · MiniCalc Challenge

*Built by Anthropic Fable 5.*

A hard, deterministic single-file coding task whose **worst-case score over many runs**
is a useful proxy for how much a quantization degrades a model. It's fully
auto-gradable — no human grader in the loop.

## What it actually measures

Be honest about the instrument. This is a high-variance capability stress test, not a
clean dial that reads out "quant quality." In validation, run-to-run spread (±7–9)
exceeded the gap between quant configs (~2), and FP8 KV cache was effectively free at
that model scale. So a single score — or even a mean — mostly shows noise.

Quantization damage usually shows up as **fatter tails and occasional catastrophic
runs**, not a shift in the average. The right instrument is therefore the *floor*: run
the same quant many times and look at its worst result, not its typical one. A Q4 build
often has a much lower floor than BF16 even when individual runs look similar.

It also doubles as a general capability probe across *different* models, since the task
is dense and unforgiving.

## The challenge

Models implement **MiniCalc**, a complete expression language, in a single Python file
(≤1200 lines, stdlib only, exact integer math — no floats). It covers a fixed-point
decimal engine with banker's rounding, a hand-written tokenizer/parser, two execution
engines that must agree, exact error formats with positions, and a self-test mode. One
deliberate rule-vs-example contradiction probes whether a model follows the stated spec
or anchors on a worked example.

The exact-integer arithmetic core is the point: a degrading quant tends to surface there
first as off-by-one or rounding drift — clean, unambiguous failure signals.

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

## How to read the results

- **Hunt the floor, not the mean.** Run ≥5–10 times per config and compare worst-case
  (and tail behaviour), not single scores. The headline 0–100 number invites exactly the
  single-shot comparison that the variance makes meaningless.
- **Watch the golden path.** A *new* failure in Categories 1–2 (fixed-point arithmetic /
  banker's rounding) is the strongest signal that a weight quant is genuinely degrading —
  it never occurred in validation.
- **Category 4 is heuristic.** Engine-equivalence (12 pts) is checked statically — it
  greps for the `ENGINE MISMATCH` string, an `exit(3)` path, opcode-ish names, and a
  STORE-emit pattern. A solution can score full marks there without the two engines truly
  agreeing, and a correct solution that names things differently can false-fail. Spot-check
  it by hand.
- **Goldens are memorizable.** Once the golden values and the trap answer (`2.000001`) are
  public, they can be memorized. That's mostly harmless when comparing quants of *one* base
  model (it hits all quants equally) but limits the suite's life as a general benchmark.

## Files

- `minicalc-challenge.md` — the challenge, the verbatim prompt, and the grading rubric
- `grade_minicalc.py` — automated grader (standard library only)

## Credits

Designed and built by **Anthropic Fable 5**.
