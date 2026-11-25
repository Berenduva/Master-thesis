#!/usr/bin/env python3
"""
Check questions.js before running the study
===========================================

Run:   python check_questions.py

It reads questions.js (the same file the app uses) and checks that:
  1. there are 30 questions (Q01-Q30), each with every field filled in
  2. the split is right: set A = the 15 IDs below, set B = the other 15,
     and the number of correct AI answers per set is as expected (EXPECTED_CORRECT)
  3. every model (Claude, GPT, Gemini, DeepSeek, Qwen) has exactly 20 runs
  4. `agrees` matches the run: a run that starts with the shown answer is
     marked as agreeing, a run that starts with the opposite is not
  5. the confidence score (share of all valid runs that give the shown answer)
     matches the expected value per question (EXPECTED_SCORES below)
  6. `correct` matches `alt` (the ground truth) and `answer`
  7. the shown answer text `a` is exactly GPT run 1 (aSource "GPT run 1"),
     starts with the majority answer, is one or two
     sentences, and has no hedging and no markdown (** or *)

It prints every problem it finds and ends with "ALL CHECKS PASSED" or
"N PROBLEM(S) FOUND". Only the Python standard library is used.
"""

import json
import re
import sys
from pathlib import Path

QUESTIONS_JS = Path(__file__).resolve().parent / "questions.js"

MODELS = ["Claude", "GPT", "Gemini", "DeepSeek", "Qwen"]
RUNS_PER_MODEL = 20

SET_A = {"Q02", "Q04", "Q07", "Q08", "Q09", "Q13", "Q15", "Q17", "Q19", "Q20",
         "Q21", "Q22", "Q26", "Q28", "Q29"}

# Confidence score per question (rounded %), as reported in the thesis.
EXPECTED_SCORES = {
    "Q01": 96, "Q02": 85, "Q03": 80, "Q04": 98, "Q05": 100, "Q06": 98, "Q07": 100, "Q08": 91,
    "Q09": 100, "Q10": 52, "Q11": 100, "Q12": 100, "Q13": 80, "Q14": 89, "Q15": 68, "Q16": 99,
    "Q17": 100, "Q18": 100, "Q19": 100, "Q20": 100, "Q21": 80, "Q22": 53, "Q23": 51, "Q24": 55,
    "Q25": 85, "Q26": 96, "Q27": 93, "Q28": 72, "Q29": 51, "Q30": 80,
}

# Number of questions where the AI (majority) answer is correct, per set.
# 21 of 30 overall (70%): set A 10 correct + 5 incorrect, set B 11 correct + 4 incorrect.
# (Q14 was rephrased and re-run; its majority answer became correct.)
EXPECTED_CORRECT = {"A": 10, "B": 11}

PARTS = {range(1, 11): "SimpleQA", range(11, 21): "Dutch facts", range(21, 31): "Party positions"}

# Hedging phrases that must not appear in the shown answer (matched as whole words).
HEDGES = ["i'm not sure", "i am not sure", "as far as i", "i believe", "i think", "not certain",
          "i don't know", "i do not know", "possibly", "might be", "may have", "to my knowledge",
          "it's unclear", "it is unclear", "i cannot", "i can't", "as of my", "knowledge cutoff"]


def load_questions(path: Path) -> list:
    """Turn the JavaScript in questions.js into Python data (it is almost JSON)."""
    text = path.read_text(encoding="utf-8")
    start = text.index("[", text.index("const QUESTIONS"))
    end = text.rindex("]") + 1
    body = text[start:end]
    body = re.sub(r"(?m)^(\s*)([A-Za-z_]\w*):", r'\1"\2":', body)   # quote the keys
    body = re.sub(r",(\s*[\]}])", r"\1", body)                     # drop trailing commas
    return json.loads(body)


def yes_no(text: str):
    """The Yes/No a model run starts with (None if it does not start with one)."""
    m = re.match(r"\W*(yes|no)\b", text, re.IGNORECASE)
    return m.group(1).capitalize() if m else None


def main() -> int:
    problems = []
    qs = load_questions(QUESTIONS_JS)

    ids = [q["id"] for q in qs]
    if ids != [f"Q{i:02d}" for i in range(1, 31)]:
        problems.append(f"question IDs are not Q01-Q30 in order: {ids}")

    for q in qs:
        qid = q["id"]
        n = int(qid[1:])
        for field in ["id", "part", "set", "q", "answer", "a", "aSource", "correct", "alt", "models"]:
            if field not in q or q[field] in ("", None):
                problems.append(f"{qid}: field '{field}' missing or empty")

        # -- part and set
        part = next(p for r, p in PARTS.items() if n in r)
        if q["part"] != part:
            problems.append(f"{qid}: part is '{q['part']}', expected '{part}'")
        expected_set = "A" if qid in SET_A else "B"
        if q["set"] != expected_set:
            problems.append(f"{qid}: set is {q['set']}, expected {expected_set}")

        # -- answer / correct / alt
        if q["answer"] not in ("Yes", "No"):
            problems.append(f"{qid}: answer is '{q['answer']}', expected Yes or No")
        if q["correct"] != (q["answer"] == q["alt"]):
            problems.append(f"{qid}: correct={q['correct']} but answer={q['answer']} and alt={q['alt']}")

        # -- runs per model and the agrees flag
        if sorted(q["models"]) != sorted(MODELS):
            problems.append(f"{qid}: models are {list(q['models'])}, expected {MODELS}")
        agree = valid = 0
        for model, runs in q["models"].items():
            total = sum(r[0] for r in runs)
            if total != RUNS_PER_MODEL:
                problems.append(f"{qid} {model}: {total} runs, expected {RUNS_PER_MODEL}")
            for k, r in enumerate(runs, 1):
                count, text, agrees = r[0], r[1], r[2]
                invalid = len(r) > 3 and bool(r[3])
                said = yes_no(text)
                if invalid:
                    if said is not None:
                        problems.append(f"{qid} {model} run {k}: marked invalid but starts with '{said}'")
                    continue
                if said is None:
                    problems.append(f"{qid} {model} run {k}: no Yes/No at the start but not marked invalid")
                elif (said == q["answer"]) != bool(agrees):
                    problems.append(f"{qid} {model} run {k}: says '{said}', shown answer '{q['answer']}', agrees={agrees}")
                valid += count
                agree += count if agrees else 0

        # -- confidence score (same rounding as the app: Math.round)
        score = int(agree * 100 / valid + 0.5) if valid else None
        if score != EXPECTED_SCORES.get(qid):
            problems.append(f"{qid}: score {score}% ({agree}/{valid}), expected {EXPECTED_SCORES.get(qid)}%")
        if agree * 2 <= valid:
            problems.append(f"{qid}: shown answer is not the majority ({agree}/{valid})")

        # -- the shown answer text: always the first GPT run, unedited
        a = q["a"]
        if q["aSource"] != "GPT run 1":
            problems.append(f"{qid}: aSource is '{q['aSource']}', expected 'GPT run 1'")
        elif a.strip() != q["models"]["GPT"][0][1].strip():
            problems.append(f"{qid}: answer text is not exactly the text of GPT run 1")
        if yes_no(a) != q["answer"]:
            problems.append(f"{qid}: answer text does not start with '{q['answer']}': {a[:40]}...")
        sentences = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])", a.strip()) if s]
        if len(sentences) > 2:
            problems.append(f"{qid}: answer text has {len(sentences)} sentences (max 2)")
        if "*" in a or "#" in a or "`" in a:
            problems.append(f"{qid}: answer text contains markdown characters")
        for h in HEDGES:
            # whole words only, so names are never flagged (e.g. "Lord Ismay" is not "may")
            if re.search(r"" + re.escape(h) + r"", a.lower()):
                problems.append(f"{qid}: answer text contains hedging ('{h}')")

    # -- set balance
    for s in ("A", "B"):
        in_set = [q for q in qs if q["set"] == s]
        right = sum(q["correct"] for q in in_set)
        if len(in_set) != 15 or right != EXPECTED_CORRECT[s]:
            problems.append(f"set {s}: {len(in_set)} questions, {right} correct (expected 15 and {EXPECTED_CORRECT[s]})")

    n_correct = sum(q["correct"] for q in qs)
    print(f"{len(qs)} questions, {n_correct} correct AI answers ({int(n_correct * 100 / len(qs) + 0.5)}%)")
    print("ID   set  part             answer  correct  score")
    for q in qs:
        lists = q["models"].values()
        agree = sum(r[0] for l in lists for r in l if r[2] and not (len(r) > 3 and r[3]))
        valid = sum(r[0] for l in lists for r in l if not (len(r) > 3 and r[3]))
        print(f"{q['id']}  {q['set']}    {q['part']:<16} {q['answer']:<7} {str(q['correct']):<8} {int(agree * 100 / valid + 0.5)}%  ({agree}/{valid})")
    print()
    if problems:
        print("\n".join("PROBLEM: " + p for p in problems))
        print(f"\n{len(problems)} PROBLEM(S) FOUND")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
