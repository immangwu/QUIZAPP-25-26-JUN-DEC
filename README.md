# Quiz Portal (newapp)

Prepared and maintained by Mr R Immanual, AP/Mech & Ms N Sanjana, AP/CSE.

A department-themed quiz portal: students pick **Mechanical Engineering** (red theme)
or **Computer Science & Engineering** (green theme), log in with credentials generated
from the nominal rolls, pick a subject, and take a 10-minute, tab-switch-monitored MCQ quiz.

## Subjects & quizzes included

| Department | Code | Subject | Quiz 01 | Quiz 02 | Quiz 03 | Quiz 04 |
|---|---|---|---|---|---|---|
| Mechanical | 20MEP11 | Unconventional Machining Process | Introduction & Mechanical Energy Based Processes (100 Q) | Thermo-Electric Energy Based Processes (60 Q) | — | — |
| Mechanical | 20ME014 | Heat and Mass Transfer | Conduction (100 Q) | Convection Heat Transfer (60 Q) | — | — |
| Mechanical | 25ME252 | Production Processes and Fabrication | Metal Casting Processes (60 Q) | — | — | — |
| CSE | 20CS006 | Theory of Computation (R2020) | Finite Automata (120 Q) | Regular Expressions & Regular Languages (120 Q) | Context-Free Grammars & Normal Forms (120 Q) | Pushdown Automata (120 Q) |

Each subject can have multiple quizzes; students pick the subject, then which quiz
(Quiz 01, Quiz 02, ...) to attempt — attempt numbering, prior-attempt history and
faculty filtering are all scoped per quiz, not just per subject.

Question banks live in `data/<key>_q<n>.json` (one file per quiz, e.g. `ucmp_q1.json`,
`ucmp_q2.json`), parsed either from `data/raw_*.txt` via `data/parse_quiz.py` (original
subjects) or directly from source `.docx` files via `data/parse_docx_quiz.py` (newer
quizzes — edit the `SOURCES` list at the top of that script to add more; three
`.docx` layouts are supported). Correct
answers are stored but **never shown to students** — the result page only shows
right/wrong per question and marks awarded.

### Adding a new quiz or subject

1. Add an entry to `SOURCES` in `data/parse_docx_quiz.py` pointing at the source
   `.docx` (see the three supported layouts documented in that file's docstring), then
   run `python data/parse_docx_quiz.py` to produce `data/<key>_q<n>.json`.
2. Register it in `utils/quiz_data.py`'s `SUBJECTS` dict — either add a `{"quiz_no":
   N, "file": "<key>_qN"}` entry to an existing subject's `quizzes` list, or add a
   whole new subject dict (with a fresh `key`/`code`/`title`) under the right
   department.
3. No changes needed to `app.py`, `storage.py`, or the admin dashboard — the quiz
   picker, attempt tracking, and faculty filters all pick up new subjects/quizzes
   automatically from `quiz_data.py`.

## Quick start (local, no Google Sheets yet)

```bash
cd newapp
pip install -r requirements.txt
streamlit run app.py
```

Without a `.streamlit/secrets.toml`, the app automatically stores credentials/results
locally (`data/credentials.json`, `local_results/results.csv`) so you can try the full
flow immediately.

Login with any student from `credentials_output/credentials_cse.csv` or
`credentials_output/credentials_mechanical.csv` (generated below).

## Generating student credentials

Student data comes from `data/roll_cse.csv` and `data/roll_me.csv` (from the nominal
rolls). Usernames are register numbers; passwords are randomly generated.

```bash
python generate_credentials.py
```

This writes/updates `data/credentials.json` (source of truth, gitignored) and printable
handout lists in `credentials_output/*.csv` (also gitignored — distribute these to
students directly, don't commit them). Re-running the script keeps existing students'
passwords unchanged and only adds passwords for new students.

## Switching to Google Sheets storage

1. In Google Cloud Console, create a **new** service account (do not reuse the
   compromised `quiz-app-writer` key from the old app) with the Sheets and Drive APIs
   enabled, and download its JSON key.
2. Create a new Google Sheet and share it with the service account's `client_email`
   (Editor access).
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the
   service account fields and the sheet's URL.
4. Run `python seed_google_sheet.py` to create and populate the `cse_credentials`,
   `mechanical_credentials`, and `results` worksheets from `data/credentials.json`.
5. Run the app as usual — `storage.py` detects `st.secrets["gcp_service_account"]` and
   automatically switches from local files to the Sheet.

## Downloads

- **Students**: on the result page after submitting, a "Download my answer script (PDF)"
  button produces a PDF with name, register no, score/percentage, and the same
  question-wise right/wrong breakdown shown on screen (no correct answers revealed).
- **Faculty**: from the department picker, open "Faculty / Admin Login" and log in
  (default `admin` / `admin123` — override via the `[admin]` section in
  `secrets.toml`, see `secrets.toml.example`). The dashboard lets you filter by
  department/subject/quiz (Quiz 01 / Quiz 02 / ...), then:
  - Download the full filtered results as **CSV** or a formatted **PDF report**
    (name, register no, subject, score, percentage, flagged status, timestamp).
  - Pick one student's attempt from a dropdown and download **that student's exact
    answer script PDF** (same file the student downloaded — right/wrong per
    question, no correct answers revealed). This works because every attempt
    records which 20 question IDs were shown (`question_ids_json`), so it can be
    reconstructed later.
  - **Delete** an individual attempt record (tick "Confirm delete" first — this is
    permanent and removes the row from Google Sheets/local CSV).

## Question sampling

Each attempt presents **20 randomly selected questions** out of the full bank
(100 for the Mechanical subjects, 120 for TOC) — a different random set every time,
via `random.sample` in `app.py`.

## How proctoring works

- A 10-minute countdown starts the moment a student clicks "Start Quiz 1".
- A small JS snippet (via `streamlit-js-eval`) listens for `visibilitychange` on the
  browser tab and counts how many times the student switches away.
- On the **3rd** switch (more than 2), the attempt is auto-submitted, graded on
  whatever was answered so far, and stored with `flagged = true`.
- Students can always start a new attempt afterward — there's no attempt limit, but
  every attempt (including flagged ones) is recorded and visible in their attempt
  history on the subject page.

## File layout

```
newapp/
  app.py                     Streamlit app (all screens + router)
  requirements.txt
  generate_credentials.py    Generates/updates student passwords
  seed_google_sheet.py       One-time push of local credentials into a Google Sheet
  data/
    hmt.json, ucmp.json, toc.json     Question banks
    raw_*.txt, parse_quiz.py          Source text + parser (provenance)
    roll_cse.csv, roll_me.csv         Nominal rolls
    credentials.json                  Generated logins (gitignored)
  credentials_output/        Printable handout CSVs (gitignored)
  local_results/             Local fallback results storage (gitignored)
  utils/
    storage.py    Google Sheets client + local fallback
    quiz_data.py  Loads question banks per subject
    theme.py      Red/green CSS theming
    proctor.py    Tab-switch counter (JS <-> Python bridge)
  .streamlit/
    secrets.toml.example
```
