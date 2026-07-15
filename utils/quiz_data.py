import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")

SUBJECTS = {
    "mechanical": [
        {"key": "ucmp", "code": "20MEP11", "title": "Unconventional Machining Process"},
        {"key": "hmt", "code": "20ME014", "title": "Heat and Mass Transfer"},
    ],
    "cse": [
        {"key": "toc", "code": "20CS006", "title": "Theory of Computation (R2020)"},
    ],
}


def get_subjects(department):
    return SUBJECTS.get(department, [])


def load_quiz(subject_key):
    path = os.path.join(DATA_DIR, f"{subject_key}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_subject_key_by_code(subject_code):
    for subjects in SUBJECTS.values():
        for s in subjects:
            if s["code"] == subject_code:
                return s["key"]
    return None
