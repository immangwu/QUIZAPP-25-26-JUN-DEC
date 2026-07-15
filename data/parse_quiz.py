"""One-off converter: raw_*.txt (Q/A/B/C/D/Answer blocks) -> clean JSON question banks."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

SUBJECTS = {
    "hmt": {
        "code": "20ME014",
        "title": "Heat and Mass Transfer",
        "quiz_title": "Quiz 1: Conduction",
        "department": "mechanical",
    },
    "ucmp": {
        "code": "20MEP11",
        "title": "Unconventional Machining Process",
        "quiz_title": "Quiz 1: Introduction & Mechanical Energy Based Processes",
        "department": "mechanical",
    },
    "toc": {
        "code": "20CS006",
        "title": "Theory of Computation",
        "quiz_title": "Quiz 1: Finite Automata",
        "department": "cse",
    },
}

BLOCK_RE = re.compile(
    r"Q(\d+)\.\s*(.+?)\nA\)\s*(.+?)\nB\)\s*(.+?)\nC\)\s*(.+?)\nD\)\s*(.+?)\nAnswer:\s*([ABCD])",
    re.DOTALL,
)
BLOCK_RE_AB_ONLY = re.compile(
    r"Q(\d+)\.\s*(.+?)\nA\)\s*(.+?)\nB\)\s*(.+?)\nAnswer:\s*([AB])",
    re.DOTALL,
)


def parse_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    questions = {}
    for m in BLOCK_RE.finditer(text):
        qid, qtext, a, b, c, d, ans = m.groups()
        questions[int(qid)] = {
            "id": int(qid),
            "question": qtext.strip(),
            "options": {
                "A": a.strip(),
                "B": b.strip(),
                "C": c.strip(),
                "D": d.strip(),
            },
            "answer": ans.strip(),
            "marks": 1,
        }
    for m in BLOCK_RE_AB_ONLY.finditer(text):
        qid, qtext, a, b, ans = m.groups()
        qid = int(qid)
        if qid in questions:
            continue
        questions[qid] = {
            "id": qid,
            "question": qtext.strip(),
            "options": {
                "A": a.strip(),
                "B": b.strip(),
            },
            "answer": ans.strip(),
            "marks": 1,
        }
    return [questions[k] for k in sorted(questions)]


def main():
    for key, meta in SUBJECTS.items():
        raw_path = os.path.join(HERE, f"raw_{key}.txt")
        questions = parse_file(raw_path)
        out = dict(meta)
        out["questions"] = questions
        out_path = os.path.join(HERE, f"{key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"{key}: parsed {len(questions)} questions -> {out_path}")


if __name__ == "__main__":
    main()
