"""
Converts a source .docx quiz (as produced by the question-generation workflow) into
the clean JSON question-bank format used by quiz_data.py / app.py.

Two source layouts are supported, auto-detected per file:

1. "Qn." layout (used by the Mechanical GATE-style docs):
   Qn. <question text>
   (a) <option>
   (b) <option>
   (c) <option>
   (d) <option>
   ... repeated for all N questions, followed by a single Word table (10 rows x
   12 cols) of Qn/answer-letter pairs, e.g. ["Q1","B","Q2","C",...].

2. "n." layout (used by the TOC docs):
   n. <question text>
   (A) <option>
   (B) <option>
   (C) <option>
   (D) <option>
   Answer: (X) <text>
   ... answer is inline, right after the four options, no table.

3. "Qn." + "A)" layout (used by the TOC Quiz 3/4 answer-key docs):
   Qn. <question text>
   A) <option>
   B) <option>
   C) <option>
   D) <option>
   Answer: X) <text>  [— optional explanation]
   ... answer is inline; header/"SET n" lines between questions are ignored.

Usage: edit SOURCES below, then `python parse_docx_quiz.py` (optionally followed by
one or more output filenames, e.g. `toc_q3.json`, to re-parse only those).
"""
import json
import os
import re
import docx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")  # "Quiz app for all" folder, where source .docx live

# Each entry: source docx (relative to ROOT), output json filename (relative to HERE),
# and the metadata to stamp onto the question bank.
SOURCES = [
    {
        "docx": "Quiz02_Unconventional_Machining_Process.docx",
        "out": "ucmp_q2.json",
        "code": "20MEP11",
        "title": "Unconventional Machining Process",
        "quiz_title": "Quiz 2: Thermo-Electric Energy Based Processes",
        "department": "mechanical",
    },
    {
        "docx": "Quiz02_Heat_and_Mass_Transfer_Conduction.docx",
        "out": "hmt_q2.json",
        "code": "20ME014",
        "title": "Heat and Mass Transfer",
        "quiz_title": "Quiz 2: Convection Heat Transfer",
        "department": "mechanical",
    },
    {
        "docx": "QUIZ 01 PRODUCTION PROCESS AND FABRICATION _ Quiz.docx",
        "out": "ppf_q1.json",
        "code": "25ME252",
        "title": "Production Processes and Fabrication",
        "quiz_title": "Quiz 1: Metal Casting Processes",
        "department": "mechanical",
    },
    {
        "docx": "toc quiz 2.docx",
        "out": "toc_q2.json",
        "code": "20CS006",
        "title": "Theory of Computation (R2020)",
        "quiz_title": "Quiz 2: Regular Expressions & Regular Languages",
        "department": "cse",
    },
    {
        "docx": "quiz 3 anserkey.docx",
        "out": "toc_q3.json",
        "code": "20CS006",
        "title": "Theory of Computation (R2020)",
        "quiz_title": "Quiz 3: Context-Free Grammars & Normal Forms",
        "department": "cse",
    },
    {
        "docx": "quiz 4 anserkey.docx",
        "out": "toc_q4.json",
        "code": "20CS006",
        "title": "Theory of Computation (R2020)",
        "quiz_title": "Quiz 4: Pushdown Automata",
        "department": "cse",
    },
]

Q_TAGGED_RE = re.compile(r"^Q(\d+)\.\s*(.+)$")
OPT_TAGGED_RE = re.compile(r"^\(([a-d])\)\s*(.*)$")

Q_PLAIN_RE = re.compile(r"^(\d+)\.\s*(.+)$")
OPT_PLAIN_RE = re.compile(r"^\(([A-D])\)\s*(.*)$")
ANSWER_INLINE_RE = re.compile(r"^Answer:\s*\(([A-D])\)")

OPT_PAREN_RE = re.compile(r"^([A-D])\)\s*(.*)$")
ANSWER_PAREN_RE = re.compile(r"^Answer:\s*([A-D])\)")


def _paras(path):
    d = docx.Document(path)
    return [p.text.strip() for p in d.paragraphs if p.text.strip()], d.tables


def parse_qtagged_with_table(path):
    """Layout 1: 'Qn.' + lowercase (a)-(d) options + trailing answer-key table."""
    paras, tables = _paras(path)
    questions = {}
    i = 0
    while i < len(paras):
        m = Q_TAGGED_RE.match(paras[i])
        if m:
            qid, qtext = int(m.group(1)), m.group(2)
            opts = {}
            for j, letter in enumerate(["A", "B", "C", "D"]):
                om = OPT_TAGGED_RE.match(paras[i + 1 + j])
                if not om:
                    raise ValueError(f"{path}: expected option {letter} after Q{qid}, got {paras[i + 1 + j]!r}")
                opts[letter] = om.group(2).strip()
            questions[qid] = {"id": qid, "question": qtext.strip(), "options": opts}
            i += 5
        else:
            i += 1

    answer_map = {}
    for t in tables:
        for row in t.rows:
            cells = [c.text.strip() for c in row.cells]
            for k in range(0, len(cells), 2):
                qm = re.match(r"^Q(\d+)$", cells[k])
                if qm and k + 1 < len(cells):
                    answer_map[int(qm.group(1))] = cells[k + 1].strip().upper()

    missing = [qid for qid in questions if qid not in answer_map]
    if missing:
        raise ValueError(f"{path}: no answer found for question ids {missing}")

    out = []
    for qid in sorted(questions):
        q = questions[qid]
        q["answer"] = answer_map[qid]
        q["marks"] = 1
        out.append(q)
    return out


def parse_plain_with_inline_answer(path):
    """Layout 2: 'n.' + uppercase (A)-(D) options + inline 'Answer: (X)' line."""
    paras, _tables = _paras(path)
    questions = {}
    i = 0
    while i < len(paras):
        m = Q_PLAIN_RE.match(paras[i])
        if m:
            qid, qtext = int(m.group(1)), m.group(2)
            opts = {}
            for j, letter in enumerate(["A", "B", "C", "D"]):
                om = OPT_PLAIN_RE.match(paras[i + 1 + j])
                if not om:
                    raise ValueError(f"{path}: expected option {letter} after {qid}., got {paras[i + 1 + j]!r}")
                opts[letter] = om.group(2).strip()
            am = ANSWER_INLINE_RE.match(paras[i + 5])
            if not am:
                raise ValueError(f"{path}: expected inline answer after {qid}., got {paras[i + 5]!r}")
            questions[qid] = {
                "id": qid,
                "question": qtext.strip(),
                "options": opts,
                "answer": am.group(1),
                "marks": 1,
            }
            i += 6
        else:
            i += 1
    return [questions[k] for k in sorted(questions)]


def parse_qtagged_with_inline_answer(path):
    """Layout 3: 'Qn.' + uppercase A)-D) options + inline 'Answer: X)' line."""
    paras, _tables = _paras(path)
    questions = {}
    i = 0
    while i < len(paras):
        m = Q_TAGGED_RE.match(paras[i])
        if m:
            qid, qtext = int(m.group(1)), m.group(2)
            if qid in questions:
                raise ValueError(f"{path}: duplicate question id Q{qid}")
            opts = {}
            for j, letter in enumerate(["A", "B", "C", "D"]):
                om = OPT_PAREN_RE.match(paras[i + 1 + j])
                if not om or om.group(1) != letter:
                    raise ValueError(f"{path}: expected option {letter} after Q{qid}, got {paras[i + 1 + j]!r}")
                opts[letter] = om.group(2).strip()
            am = ANSWER_PAREN_RE.match(paras[i + 5])
            if not am:
                raise ValueError(f"{path}: expected inline answer after Q{qid}, got {paras[i + 5]!r}")
            questions[qid] = {
                "id": qid,
                "question": qtext.strip(),
                "options": opts,
                "answer": am.group(1),
                "marks": 1,
            }
            i += 6
        else:
            i += 1
    return [questions[k] for k in sorted(questions)]


def main(only=None):
    for src in SOURCES:
        if only and src["out"] not in only:
            continue
        docx_path = os.path.join(ROOT, src["docx"])
        paras, tables = _paras(docx_path)
        if tables:
            questions = parse_qtagged_with_table(docx_path)
        elif any(OPT_PAREN_RE.match(p) for p in paras):
            questions = parse_qtagged_with_inline_answer(docx_path)
        else:
            questions = parse_plain_with_inline_answer(docx_path)

        out = {
            "code": src["code"],
            "title": src["title"],
            "quiz_title": src["quiz_title"],
            "department": src["department"],
            "questions": questions,
        }
        out_path = os.path.join(HERE, src["out"])
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"{src['docx']}: parsed {len(questions)} questions -> {out_path}")


if __name__ == "__main__":
    import sys
    main(set(sys.argv[1:]) or None)
