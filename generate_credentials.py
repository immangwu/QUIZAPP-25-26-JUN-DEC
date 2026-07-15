"""
Generates a random login password for every student in the nominal rolls.

Run once:  python generate_credentials.py

Produces:
  - data/credentials.json         (used by the app as the source of truth /
                                    local fallback when Google Sheets isn't configured)
  - credentials_output/credentials_cse.csv   (printable handout list)
  - credentials_output/credentials_me.csv    (printable handout list)

Username for every student is their register number. Re-running this script
will NOT overwrite existing passwords for students already present in
data/credentials.json, so it's safe to re-run after adding new students.
"""
import csv
import json
import os
import secrets
import string

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT_DIR = os.path.join(HERE, "credentials_output")

# Avoid visually ambiguous characters (0/O, 1/l/I) for handwritten handouts.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def gen_password(length=8):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def load_roll(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cred_path = os.path.join(DATA_DIR, "credentials.json")
    existing = {}
    if os.path.exists(cred_path):
        with open(cred_path, encoding="utf-8") as f:
            existing = json.load(f)

    departments = {
        "cse": os.path.join(DATA_DIR, "roll_cse.csv"),
        "mechanical": os.path.join(DATA_DIR, "roll_me.csv"),
    }

    result = {"cse": {}, "mechanical": {}}
    for dept, path in departments.items():
        prev = existing.get(dept, {})
        rows = load_roll(path)
        for row in rows:
            reg_no = row["reg_no"].strip()
            name = row["name"].strip()
            if reg_no in prev:
                password = prev[reg_no]["password"]
            else:
                password = gen_password()
            result[dept][reg_no] = {"name": name, "password": password}

        out_csv = os.path.join(OUT_DIR, f"credentials_{dept}.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Register No / Username", "Name", "Password"])
            for reg_no, info in sorted(result[dept].items()):
                writer.writerow([reg_no, info["name"], info["password"]])
        print(f"{dept}: {len(result[dept])} students -> {out_csv}")

    with open(cred_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Credentials store written -> {cred_path}")


if __name__ == "__main__":
    main()
