import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")

# Each subject can now have multiple quizzes (Quiz 01, Quiz 02, ...). Every quiz is
# its own JSON file under data/ (e.g. "ucmp_q1", "ucmp_q2"), holding a full question
# bank + its own quiz_title. `quiz_no` is the number shown to students/faculty and
# used to scope attempt numbering + admin filtering.
SUBJECTS = {
    "mechanical": [
        {
            "key": "ucmp", "code": "20MEP11", "title": "Unconventional Machining Process",
            "quizzes": [
                {"quiz_no": 1, "file": "ucmp_q1"},
                {"quiz_no": 2, "file": "ucmp_q2"},
                {"quiz_no": 3, "file": "ucmp_q3"},
                {"quiz_no": 4, "file": "ucmp_q4"},
            ],
        },
        {
            "key": "hmt", "code": "20ME014", "title": "Heat and Mass Transfer",
            "quizzes": [
                {"quiz_no": 1, "file": "hmt_q1"},
                {"quiz_no": 2, "file": "hmt_q2"},
                {"quiz_no": 3, "file": "hmt_q3"},
                {"quiz_no": 4, "file": "hmt_q4"},
            ],
        },
        {
            "key": "ppf", "code": "25ME252", "title": "Production Processes and Fabrication",
            "quizzes": [
                {"quiz_no": 1, "file": "ppf_q1"},
                {"quiz_no": 2, "file": "ppf_q2"},
            ],
        },
    ],
    "cse": [
        {
            "key": "toc", "code": "20CS006", "title": "Theory of Computation (R2020)",
            "quizzes": [
                {"quiz_no": 1, "file": "toc_q1"},
                {"quiz_no": 2, "file": "toc_q2"},
                {"quiz_no": 3, "file": "toc_q3"},
                {"quiz_no": 4, "file": "toc_q4"},
            ],
        },
    ],
}


def get_subjects(department):
    return SUBJECTS.get(department, [])


def get_subject(department, subject_key):
    for s in SUBJECTS.get(department, []):
        if s["key"] == subject_key:
            return s
    return None


def get_quizzes(department, subject_key):
    """Returns the list of {quiz_no, file} dicts available for a subject, sorted by quiz_no."""
    subject = get_subject(department, subject_key)
    if not subject:
        return []
    return sorted(subject["quizzes"], key=lambda q: q["quiz_no"])


def load_quiz_file(file_key):
    path = os.path.join(DATA_DIR, f"{file_key}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_quiz(department, subject_key, quiz_no):
    """Loads a specific quiz's question bank, tagging it with its quiz_no."""
    for q in get_quizzes(department, subject_key):
        if q["quiz_no"] == quiz_no:
            data = load_quiz_file(q["file"])
            data["quiz_no"] = quiz_no
            return data
    return None


def get_subject_key_by_code(subject_code):
    for subjects in SUBJECTS.values():
        for s in subjects:
            if s["code"] == subject_code:
                return s["key"]
    return None


def get_department_by_code(subject_code):
    for dept, subjects in SUBJECTS.items():
        for s in subjects:
            if s["code"] == subject_code:
                return dept
    return None


def max_quiz_no():
    """Highest quiz_no configured across every subject — used to size the admin filter."""
    best = 1
    for subjects in SUBJECTS.values():
        for s in subjects:
            for q in s["quizzes"]:
                best = max(best, q["quiz_no"])
    return best
