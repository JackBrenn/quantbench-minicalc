#!/usr/bin/env python3
"""
grade_minicalc.py — automated grader for the QuantBench-1200 MiniCalc challenge.

Usage:
    python3 grade_minicalc.py solution1.py [solution2.py ...]

Runs ~45 behavioral + static checks per solution, prints a per-category score
table (max 100), and a comparison table if multiple solutions are given.
Requires only the Python standard library.
"""

import re
import subprocess
import sys

TIMEOUT = 30


# ───────────────────────── execution helper ─────────────────────────

def run(sol, args=None, stdin=None, timeout=TIMEOUT):
    """Run a solution; returns (rc, stdout, stderr). rc=-1 on timeout."""
    cmd = [sys.executable, sol] + (args or [])
    try:
        p = subprocess.run(cmd, input=stdin, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:  # noqa: BLE001
        return -2, "", f"RUNNER ERROR: {e}"


def is_clean_error(rc, out, err, code=None, line_col=None):
    """True if: exit 2, no stdout, single-line formatted error, no traceback,
    optional error code match, optional exact L:C match, never L0:C0."""
    if rc != 2 or out != "":
        return False
    if "Traceback" in err:
        return False
    e = err.strip()
    m = re.match(r"^(SyntaxError|RuntimeError)\[L(\d+):C(\d+)\](\[(E\d+)\])?: ", e)
    if not m:
        return False
    if m.group(2) == "0" or m.group(3) == "0":
        return False  # placeholder positions are a failure
    if code and m.group(5) != code:
        return False
    if line_col and (m.group(2), m.group(3)) != line_col:
        return False
    return True


# ───────────────────────── check definitions ─────────────────────────
# Each check: (id, points, description, function(sol, src) -> bool)

def make_golden(program, expected):
    def f(sol, _src):
        rc, out, err = run(sol, [program])
        return rc == 0 and out == expected
    return f


def make_error(program, code=None, line_col=None):
    def f(sol, _src):
        rc, out, err = run(sol, [program])
        return is_clean_error(rc, out, err, code, line_col)
    return f


def chk_syntax_reject(program):
    def f(sol, _src):
        rc, out, err = run(sol, [program])
        return (rc == 2 and "Traceback" not in err
                and err.strip().startswith("SyntaxError[L"))
    return f


def chk_stdin(sol, _src):
    rc, out, _ = run(sol, stdin="let a=2; a*a; a+1")
    return rc == 0 and out == "4.000000\n3.000000\n"


def chk_let_silent(sol, _src):
    rc, out, _ = run(sol, ["let q = 5"])
    return rc == 0 and out == ""


def chk_incremental(sol, _src):
    rc, out, err = run(sol, ["2; 1/0"])
    return rc == 2 and out == "2.000000\n" and "E300" in err


def chk_exit0(sol, _src):
    rc, out, _ = run(sol, ["1+1"])
    return rc == 0 and out == "2.000000\n"


def chk_determinism(sol, _src):
    r1 = run(sol, ["sqrt(7) + 1/3; let z = 2^10; z % 7"])
    r2 = run(sol, ["sqrt(7) + 1/3; let z = 2^10; z % 7"])
    return r1 == r2 and r1[0] == 0


def chk_lines(sol, src):
    return len(src.splitlines()) <= 1200


def chk_banned(sol, src):
    banned = [r"\bimport\s+decimal\b", r"\bimport\s+fractions\b",
              r"\bimport\s+numpy\b", r"\bimport\s+ctypes\b",
              r"\bfrom\s+(decimal|fractions|numpy|ctypes)\b",
              r"(?<![\w.])eval\s*\(", r"(?<![\w.])exec\s*\("]
    return not any(re.search(b, src) for b in banned)


def chk_no_regex(sol, src):
    return not re.search(r"^\s*import\s+re\b|^\s*from\s+re\s+import", src, re.M)


def chk_no_float(sol, src):
    # Heuristic: float() calls or float literals used in arithmetic context.
    if re.search(r"(?<![\w.])float\s*\(", src):
        return False
    # float literals like 0.5 outside strings/comments are hard to verify
    # statically; rely on golden values (floats produce 1.000000 for x*3).
    rc, out, _ = run(sol, ["let x = 1/3; x * 3"])
    return out == "0.999999\n"


def chk_selftest_exact(sol, _src):
    rc, out, _ = run(sol, ["--selftest"], timeout=120)
    return rc == 0 and out == "SELFTEST OK\n"


def chk_selftest_runs(sol, _src):
    rc, out, _ = run(sol, ["--selftest"], timeout=120)
    return rc == 0 and "SELFTEST OK" in out


def chk_assert_count(sol, src):
    n = len(re.findall(
        r"^\s*(assert\b|chk\w*\s*\(|check\w*\s*\(|ok\s*\+=|_expect\w*\s*\()",
        src, re.M))
    return n >= 30


def chk_mismatch_string(sol, src):
    return "ENGINE MISMATCH" in src


def chk_exit3(sol, src):
    return re.search(r"exit\s*\(\s*3\s*\)", src) is not None


def chk_opcodes(sol, src):
    """Heuristic: a bytecode layer exists. Look for opcode-ish identifiers."""
    families = [
        r"\bPUSH\w*\b|\bPU\b", r"\bLOAD\w*\b|\bLD\w*\b|\bLV\b",
        r"\bSTORE\w*\b|\bST\w*\b|\bSV\b", r"\bADD\w*\b|\bAD\b",
        r"\bMUL\w*\b|\bMU\b", r"\bDIV\w*\b|\bDI\b",
        r"\bNEG\w*\b|\bNG\b|\bNE\b", r"\bPOW\w*\b|\bPO\b|\bPW\b",
        r"\bCALL\w*\b|\bCF\b|\bCA?LL\b",
    ]
    hits = sum(1 for f in families if re.search(f, src))
    return hits >= 7


def chk_store_emitted(sol, src):
    """Heuristic: a STORE-family opcode is appended/emitted somewhere."""
    return re.search(
        r"(append|extend|_e|emit)\s*\(\s*[\[\(]?\s*(\w*ST(ORE)?\w*|SV)\b",
        src) is not None or re.search(r"\(\s*(ST\w*|SV|STORE\w*)\s*,", src) is not None


CHECKS = [
    # ── Cat 1: Fixed-point arithmetic (18) ──
    ("1", "G1  1/3", 2.0, make_golden("1/3", "0.333333\n")),
    ("1", "G2  2/3", 2.0, make_golden("2/3", "0.666667\n")),
    ("1", "G3  sqrt(2)", 3.0, make_golden("sqrt(2)", "1.414214\n")),
    ("1", "G4  let x=1/3; x*3", 3.0, make_golden("let x = 1/3; x * 3", "0.999999\n")),
    ("1", "G8  10/4", 2.0, make_golden("10 / 4", "2.500000\n")),
    ("1", "G10 min/max mix", 2.0,
     make_golden("min(3, 1+1) + max(0.5, 0.25)", "2.500000\n")),
    ("1", "pow 2^10", 2.0, make_golden("2 ^ 10", "1024.000000\n")),
    ("1", "neg pow 2^-2", 2.0, make_golden("2 ^ -2", "0.250000\n")),
    # ── Cat 2: Banker's rounding (10) ──
    ("2", "tie down 0.000001/2", 2.0, make_golden("0.000001 / 2", "0.000000\n")),
    ("2", "tie up 0.000003/2", 2.0, make_golden("0.000003 / 2", "0.000002\n")),
    ("2", "mul tie 1.5*0.000001", 2.0, make_golden("1.5 * 0.000001", "0.000002\n")),
    ("2", "neg tie -0.000003/2", 2.0, make_golden("0 - 0.000003 / 2", "-0.000002\n")),
    ("2", "sqrt boundary 0.008248", 2.0,
     make_golden("sqrt(0.008248)", "0.090819\n")),
    # ── Cat 3: Parser & precedence (12) ──
    ("3", "G6  2^3^2 right-assoc", 2.0, make_golden("2 ^ 3 ^ 2", "512.000000\n")),
    ("3", "G7  -2^2 = -4", 2.0, make_golden("-2 ^ 2", "-4.000000\n")),
    ("3", "G9  7 % -3 sign rule", 2.0, make_golden("7 % -3", "-2.000000\n")),
    ("3", "G14 7th frac digit rejected", 2.0, chk_syntax_reject("1.1234567")),
    ("3", "missing ';' rejected (1 2)", 2.0, chk_syntax_reject("1 2")),
    ("3", "'let' reserved (let let = 1)", 2.0, chk_syntax_reject("let let = 1")),
    # ── Cat 4: Engine equivalence — static heuristics (12) ──
    ("4", "ENGINE MISMATCH string present", 4.0, chk_mismatch_string),
    ("4", "exit(3) path present", 3.0, chk_exit3),
    ("4", "bytecode opcode set present", 3.0, chk_opcodes),
    ("4", "STORE opcode emitted for let", 2.0, chk_store_emitted),
    # ── Cat 5: Exact error formats (12) ──
    ("5", "G11 1/0 -> E300 @ L1:C2", 2.0, make_error("1/0", "E300", ("1", "2"))),
    ("5", "G12 2^0.5 -> E301 @ L1:C3", 2.0, make_error("2 ^ 0.5", "E301", ("1", "3"))),
    ("5", "G13 nope(1) -> E305 @ L1:C1", 2.0, make_error("nope(1)", "E305", ("1", "1"))),
    ("5", "E302 undefined var", 1.0, make_error("zz + 1", "E302")),
    ("5", "E303 sqrt negative", 1.0, make_error("sqrt(0 - 4)", "E303")),
    ("5", "E304 wrong arg count", 1.0, make_error("sqrt(1, 2)", "E304")),
    ("5", "1 % 0 clean E300 (no traceback)", 1.5, make_error("1 % 0", "E300")),
    ("5", "0 ^ -1 clean E300, real position", 1.5, make_error("0 ^ -1", "E300")),
    # ── Cat 6: Constraints (12) ──
    ("6", "line count <= 1200", 3.0, chk_lines),
    ("6", "no banned imports / eval / exec", 3.0, chk_banned),
    ("6", "no float arithmetic (behavioral)", 2.0, chk_no_float),
    ("6", "no regex import", 2.0, chk_no_regex),
    ("6", "deterministic output", 2.0, chk_determinism),
    # ── Cat 7: CLI & I/O (8) ──
    ("7", "stdin mode works", 2.0, chk_stdin),
    ("7", "let prints nothing", 2.0, chk_let_silent),
    ("7", "incremental output (2; 1/0)", 2.0, chk_incremental),
    ("7", "exit 0 on success", 2.0, chk_exit0),
    # ── Cat 8: Self-test (8) ──
    ("8", "selftest passes (contains OK)", 3.0, chk_selftest_runs),
    ("8", "stdout is exactly 'SELFTEST OK'", 3.0, chk_selftest_exact),
    ("8", ">= 30 assertions (static count)", 2.0, chk_assert_count),
    # ── Cat 9: Long-range fidelity (8) ──
    ("9", "TRAP: sqrt(2)^2 = 2.000001 (rule over example)", 4.0,
     make_golden("sqrt(2) ^ 2", "2.000001\n")),
    ("9", "E301 positioned at the ^ operator", 2.0,
     make_error("10 ^ 0.5", "E301", ("1", "4"))),
    ("9", "perf: 2^4096 under 5s", 2.0,
     lambda sol, _src: run(sol, ["2 ^ 4096"], timeout=5)[0] == 0),
]

CATEGORIES = {
    "1": ("Fixed-point arithmetic", 18),
    "2": ("Banker's rounding edges", 10),
    "3": ("Parser & precedence", 12),
    "4": ("Engine equivalence (heuristic)", 12),
    "5": ("Exact error formats", 12),
    "6": ("Constraint compliance", 12),
    "7": ("CLI & I/O contract", 8),
    "8": ("Self-test quality", 8),
    "9": ("Long-range spec fidelity", 8),
}


# ───────────────────────── grading ─────────────────────────

def grade(sol, verbose=True):
    try:
        with open(sol, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except OSError as e:
        print(f"Cannot read {sol}: {e}", file=sys.stderr)
        return None

    cat_scores = {c: 0.0 for c in CATEGORIES}
    rows = []
    for cat, name, pts, fn in CHECKS:
        try:
            passed = bool(fn(sol, src))
        except Exception:  # noqa: BLE001
            passed = False
        if passed:
            cat_scores[cat] += pts
        rows.append((cat, name, pts, passed))

    total = sum(cat_scores.values())

    if verbose:
        print(f"\n{'=' * 64}\n  {sol}\n{'=' * 64}")
        cur = None
        for cat, name, pts, passed in rows:
            if cat != cur:
                cur = cat
                cname, cmax = CATEGORIES[cat]
                print(f"\n[{cat}] {cname} "
                      f"— {cat_scores[cat]:.1f}/{cmax}")
            mark = "PASS" if passed else "FAIL"
            print(f"    {mark}  ({pts:>4.1f})  {name}")
        print(f"\n{'-' * 64}")
        for cat, (cname, cmax) in CATEGORIES.items():
            print(f"  {cname:<34} {cat_scores[cat]:>5.1f} / {cmax}")
        print(f"  {'TOTAL':<34} {total:>5.1f} / 100")
    return total, cat_scores


def main():
    sols = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not sols:
        print(__doc__)
        sys.exit(1)
    results = {}
    for sol in sols:
        r = grade(sol)
        if r:
            results[sol] = r
    if len(results) > 1:
        print(f"\n{'=' * 64}\n  COMPARISON\n{'=' * 64}")
        hdr = f"  {'Category':<34}" + "".join(
            f"{s.split('/')[-1][:12]:>14}" for s in results)
        print(hdr)
        for cat, (cname, cmax) in CATEGORIES.items():
            row = f"  {cname[:33]:<34}" + "".join(
                f"{r[1][cat]:>11.1f}/{cmax:<2}" for r in results.values())
            print(row)
        print("  " + "-" * (len(hdr) - 2))
        print(f"  {'TOTAL':<34}" + "".join(
            f"{r[0]:>10.1f}/100" for r in results.values()))


if __name__ == "__main__":
    main()