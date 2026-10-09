import time
import json
import random
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_js_eval import streamlit_js_eval

from utils import storage, quiz_data
from utils.theme import inject_theme, THEMES
from utils.proctor import read_tab_switch_count, MAX_ALLOWED_SWITCHES
from utils.pdf_report import generate_student_answer_script, generate_faculty_report

QUIZ_DURATION_SECONDS = 10 * 60
QUESTIONS_PER_ATTEMPT = 20


def _admin_credentials():
    try:
        return st.secrets["admin"]["username"], st.secrets["admin"]["password"]
    except Exception:
        return "admin", "admin123"

st.set_page_config(page_title="Quiz Portal", page_icon="\U0001f4dd", layout="centered")

FOOTER_HTML = """
<hr style="margin-top:2em;margin-bottom:0.6em;opacity:0.3;">
<div style="text-align:center;font-size:0.8em;color:#6b7280;padding-bottom:1em;">
Prepared and Maintained by Mr R Immanual, AP/Mech &amp; Ms N Sanjana, AP/CSE
</div>
"""


def render_footer(st):
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)

DEFAULTS = {
    "stage": "department",
    "department": None,
    "reg_no": None,
    "name": None,
    "subject_key": None,
    "quiz_no": None,
    "quiz": None,
    "answers": {},
    "quiz_deadline": None,
    "flagged": False,
    "tab_switch_count": 0,
    "proctor_key": None,
    "submitted_result": None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def goto(stage):
    print(f"[goto] {st.session_state.get('reg_no')}: {st.session_state.get('stage')} -> {stage}", flush=True)
    st.session_state.stage = stage


def logout_to_department():
    print(f"[logout_to_department] {st.session_state.get('reg_no')}: was on stage={st.session_state.get('stage')}", flush=True)
    for k in DEFAULTS:
        st.session_state[k] = DEFAULTS[k]


# ---------------------------------------------------------------- screens

def screen_department():
    st.title("\U0001f4dd Quiz Portal")
    st.write("Select your department to continue.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⚙️ Mechanical Engineering")
        if st.button("Continue as Mechanical", use_container_width=True, key="pick_mech"):
            st.session_state.department = "mechanical"
            goto("login")
            st.rerun()
    with col2:
        st.markdown("### \U0001f4bb Computer Science & Engineering")
        if st.button("Continue as CSE", use_container_width=True, key="pick_cse"):
            st.session_state.department = "cse"
            goto("login")
            st.rerun()

    st.divider()
    with st.expander("\U0001f9d1‍\U0001f3eb Faculty / Admin Login"):
        if st.button("Go to Faculty Login"):
            goto("admin_login")
            st.rerun()


def screen_login():
    dept = st.session_state.department
    theme = inject_theme(st, dept)
    st.title(f"{theme['emoji']} {theme['label']}")
    st.subheader("Student Login")

    creds = storage.get_credentials(dept)

    with st.form("login_form"):
        username = st.text_input("Username (Register Number)")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")

    if submitted:
        username = username.strip()
        record = creds.get(username)
        if record and password == record["password"]:
            st.session_state.reg_no = username
            st.session_state.name = record["name"]
            goto("subject")
            st.rerun()
        else:
            st.error("Invalid username or password. Please check your credentials handout.")

    if st.button("← Back"):
        logout_to_department()
        st.rerun()


def screen_subject():
    dept = st.session_state.department
    theme = inject_theme(st, dept)
    st.title(f"{theme['emoji']} Welcome, {st.session_state.name}")
    st.caption(f"Register No: {st.session_state.reg_no}")

    subjects = quiz_data.get_subjects(dept)
    labels = [f"{s['code']} – {s['title']}" for s in subjects]
    choice = st.radio("Choose your subject:", labels, key="subject_choice")
    chosen = subjects[labels.index(choice)]

    quizzes = quiz_data.get_quizzes(dept, chosen["key"])
    quiz_labels = [f"Quiz {q['quiz_no']:02d}" for q in quizzes]
    quiz_choice = st.radio("Choose the quiz:", quiz_labels, key="quiz_choice", horizontal=True)
    chosen_quiz = quizzes[quiz_labels.index(quiz_choice)]
    quiz_no = chosen_quiz["quiz_no"]

    prior = storage.get_attempts(st.session_state.reg_no, chosen["code"], quiz_no)
    if prior:
        st.info(f"You have {len(prior)} previous attempt(s) for this quiz. You may attempt again.")
        with st.expander("View previous attempts"):
            for i, p in enumerate(prior, 1):
                flag_note = " — ⚠️ flagged (tab-switch)" if str(p.get("flagged")).lower() == "true" else ""
                st.write(f"Attempt {p.get('attempt_no', i)}: {p.get('score')}/{p.get('total')} "
                         f"({p.get('percentage')}%){flag_note} — {p.get('timestamp')}")

    total_available = len(quiz_data.load_quiz(dept, chosen["key"], quiz_no)["questions"])
    n_questions = min(QUESTIONS_PER_ATTEMPT, total_available)
    st.caption(f"This attempt will present {n_questions} randomly selected questions out of {total_available}.")

    if st.button(f"Start Quiz {quiz_no:02d}", type="primary"):
        quiz = quiz_data.load_quiz(dept, chosen["key"], quiz_no)
        pool = quiz["questions"]
        quiz = dict(quiz)
        quiz["questions"] = random.sample(pool, min(QUESTIONS_PER_ATTEMPT, len(pool)))
        st.session_state.subject_key = chosen["key"]
        st.session_state.quiz_no = quiz_no
        st.session_state.quiz = quiz
        st.session_state.answers = {}
        st.session_state.flagged = False
        st.session_state.tab_switch_count = 0
        # Fresh tab-switch counter per attempt: the counter lives in the browser's
        # sessionStorage, so keying it only by subject made a new attempt inherit the
        # previous attempt's count and get auto-flagged instantly.
        st.session_state.proctor_key = f"{chosen['key']}_q{quiz_no}_{int(time.time() * 1000)}"
        st.session_state.quiz_deadline = time.time() + QUIZ_DURATION_SECONDS
        goto("quiz")
        st.rerun()

    if st.button("← Log out"):
        logout_to_department()
        st.rerun()


def _grade_and_store(auto_flagged, tab_switch_count):
    quiz = st.session_state.quiz
    answers = st.session_state.answers
    per_question = []
    score = 0
    total = 0
    for q in quiz["questions"]:
        marks = q.get("marks", 1)
        total += marks
        selected = answers.get(str(q["id"]))
        correct = selected == q["answer"]
        if correct:
            score += marks
        per_question.append({
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "selected": selected,
            "marks": marks,
            "awarded": marks if correct else 0,
            "correct": correct,
        })

    percentage = round((score / total) * 100, 2) if total > 0 else 0.0
    quiz_no = quiz.get("quiz_no", 1)

    prior = storage.get_attempts(st.session_state.reg_no, quiz["code"], quiz_no)
    attempt_no = len(prior) + 1

    record = {
        "department": st.session_state.department,
        "subject_code": quiz["code"],
        "quiz_no": quiz_no,
        "reg_no": st.session_state.reg_no,
        "name": st.session_state.name,
        "attempt_no": attempt_no,
        "score": score,
        "total": total,
        "percentage": percentage,
        "flagged": auto_flagged,
        "tab_switch_count": tab_switch_count,
        "answers_json": json.dumps({k: v for k, v in answers.items()}),
        "question_ids_json": json.dumps([q["id"] for q in quiz["questions"]]),
    }
    storage.save_result(record)

    st.session_state.submitted_result = {
        "score": score,
        "total": total,
        "percentage": percentage,
        "flagged": auto_flagged,
        "tab_switch_count": tab_switch_count,
        "attempt_no": attempt_no,
        "per_question": per_question,
        "quiz_no": quiz_no,
        "quiz_title": quiz.get("quiz_title", "Quiz 1"),
        "subject_title": quiz.get("title"),
        "subject_code": quiz.get("code"),
    }


def _reconstruct_result_from_record(record):
    """Rebuilds the same 'submitted_result' shape used for the student PDF, from a
    stored results row, so faculty can (re)download a specific student's answer
    script. Requires question_ids_json to have been recorded (i.e. saved by this
    version of the app or later)."""
    subject_code = record.get("subject_code")
    subject_key = quiz_data.get_subject_key_by_code(subject_code)
    department = record.get("department") or quiz_data.get_department_by_code(subject_code)
    quiz_no = int(record.get("quiz_no") or 1)
    if not subject_key or not department:
        return None
    quiz = quiz_data.load_quiz(department, subject_key, quiz_no)
    if not quiz:
        return None
    by_id = {q["id"]: q for q in quiz["questions"]}

    try:
        question_ids = json.loads(record.get("question_ids_json") or "[]")
        answers = json.loads(record.get("answers_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    if not question_ids:
        return None

    per_question = []
    for qid in question_ids:
        q = by_id.get(qid)
        if not q:
            continue
        marks = q.get("marks", 1)
        selected = answers.get(str(qid))
        correct = selected == q["answer"]
        per_question.append({
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "selected": selected,
            "marks": marks,
            "awarded": marks if correct else 0,
            "correct": correct,
        })

    return {
        "score": record.get("score"),
        "total": record.get("total"),
        "percentage": record.get("percentage"),
        "flagged": str(record.get("flagged")).lower() == "true",
        "tab_switch_count": record.get("tab_switch_count"),
        "attempt_no": record.get("attempt_no"),
        "per_question": per_question,
        "quiz_no": quiz_no,
        "quiz_title": quiz.get("quiz_title", "Quiz 1"),
        "subject_title": quiz.get("title"),
        "subject_code": quiz.get("code"),
    }


def screen_quiz():
    dept = st.session_state.department
    theme = inject_theme(st, dept)
    quiz = st.session_state.quiz

    st_autorefresh(interval=10000, limit=None, key="quiz_ticker")

    remaining = st.session_state.quiz_deadline - time.time()
    switch_count = read_tab_switch_count(streamlit_js_eval, st.session_state.proctor_key)
    st.session_state.tab_switch_count = switch_count

    if switch_count > MAX_ALLOWED_SWITCHES:
        _grade_and_store(auto_flagged=True, tab_switch_count=switch_count)
        goto("result")
        st.rerun()
        return

    if remaining <= 0:
        _grade_and_store(auto_flagged=False, tab_switch_count=switch_count)
        goto("result")
        st.rerun()
        return

    mins, secs = divmod(max(0, int(remaining)), 60)
    timer_color = "\U0001f7e2" if remaining > 120 else "\U0001f7e1" if remaining > 60 else "\U0001f534"

    top1, top2, top3 = st.columns([2, 1, 1])
    with top1:
        st.markdown(f"<div class='quiz-banner'>{quiz['code']} – {quiz.get('quiz_title','Quiz 1')}</div>", unsafe_allow_html=True)
    with top2:
        st.metric(f"{timer_color} Time Left", f"{mins:02d}:{secs:02d}")
    with top3:
        st.metric("Tab switches", f"{switch_count}/{MAX_ALLOWED_SWITCHES}")

    st.warning(
        f"Switching tabs/windows more than {MAX_ALLOWED_SWITCHES} times will stop and flag this attempt. "
        "Stay on this tab until you submit. (A flagged attempt doesn't block you — you can "
        "always start a fresh attempt afterwards.)"
    )

    st.caption(
        "Answer as many questions as you can, then press Submit Quiz at the bottom. "
        "Selecting an answer won't reload the page — only Submit does."
    )

    with st.form("quiz_form", clear_on_submit=False):
        selections = {}
        for q in quiz["questions"]:
            qid = str(q["id"])
            st.markdown("<div class='question-card'>", unsafe_allow_html=True)
            st.markdown(f"**Q{q['id']}. ({q.get('marks',1)} mark) {q['question']}**")
            opt_keys = list(q["options"].keys())
            opt_labels = [f"{k}) {v}" for k, v in q["options"].items()]
            current = st.session_state.answers.get(qid)
            idx = opt_keys.index(current) if current in opt_keys else None
            choice = st.radio(
                "Select one:", opt_labels, index=idx, key=f"q_{qid}", label_visibility="collapsed",
            )
            if choice is not None:
                selections[qid] = opt_keys[opt_labels.index(choice)]
            st.markdown("</div>", unsafe_allow_html=True)

        submit_clicked = st.form_submit_button(
            "Submit Quiz", type="primary", use_container_width=True,
        )

    if submit_clicked:
        print(f"[submit] reg_no={st.session_state.reg_no} subject={quiz.get('code')} "
              f"answers_selected={len(selections)}/{len(quiz['questions'])}", flush=True)
        st.session_state.answers.update(selections)
        _grade_and_store(auto_flagged=False, tab_switch_count=switch_count)
        goto("result")
        st.rerun()

    if st.button("Cancel & log out", use_container_width=True):
        logout_to_department()
        st.rerun()


def screen_result():
    dept = st.session_state.department
    theme = inject_theme(st, dept)
    res = st.session_state.submitted_result

    st.title("\U0001f4c4 Answer Script")
    st.caption(f"{res['subject_code']} – {res['subject_title']} · {res['quiz_title']} · Attempt {res['attempt_no']}")

    if res["flagged"]:
        st.markdown(
            "<div class='flag-banner'>⚠️ This attempt was auto-stopped and flagged for switching "
            f"tabs {res['tab_switch_count']} times.</div>",
            unsafe_allow_html=True,
        )
        st.write("")

    m1, m2, m3 = st.columns(3)
    m1.metric("Score", f"{res['score']} / {res['total']}")
    m2.metric("Percentage", f"{res['percentage']}%")
    m3.metric("Tab switches", res["tab_switch_count"])

    pdf_bytes = generate_student_answer_script(res, st.session_state.name, st.session_state.reg_no, dept)
    st.download_button(
        "\U0001f4e5 Download my answer script (PDF)",
        data=pdf_bytes,
        file_name=f"{st.session_state.reg_no}_{res['subject_code']}_q{res['quiz_no']}_attempt{res['attempt_no']}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Question-wise Result")
    st.caption("Correct answers are not shown — only whether your response was right or wrong.")

    for pq in res["per_question"]:
        st.markdown("<div class='question-card'>", unsafe_allow_html=True)
        pill = "<span class='correct-pill'>✓ Correct</span>" if pq["correct"] else "<span class='wrong-pill'>✗ Incorrect</span>"
        st.markdown(f"**Q{pq['id']}. ({pq['marks']} mark) {pq['question']}**  {pill}", unsafe_allow_html=True)
        selected = pq["selected"]
        if selected:
            st.write(f"Your answer: {selected}) {pq['options'].get(selected, '')}")
        else:
            st.write("Your answer: _Not answered_")
        st.write(f"Marks awarded: {pq['awarded']} / {pq['marks']}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Take another subject / attempt", use_container_width=True):
            st.session_state.subject_key = None
            st.session_state.quiz = None
            st.session_state.submitted_result = None
            goto("subject")
            st.rerun()
    with c2:
        if st.button("Log out", use_container_width=True):
            logout_to_department()
            st.rerun()


def screen_admin_login():
    st.title("\U0001f9d1‍\U0001f3eb Faculty / Admin Login")
    admin_user, admin_pass = _admin_credentials()

    with st.form("admin_login_form"):
        username = st.text_input("Admin Username")
        password = st.text_input("Admin Password", type="password")
        submitted = st.form_submit_button("Log In")

    if submitted:
        if username == admin_user and password == admin_pass:
            st.session_state.admin_authed = True
            goto("admin_dashboard")
            st.rerun()
        else:
            st.error("Invalid admin credentials.")

    if st.button("← Back"):
        goto("department")
        st.rerun()


def screen_admin_dashboard():
    st.title("\U0001f4ca Faculty Dashboard")

    if storage.is_sheets_configured():
        st.success("✅ Connected to Google Sheets — logins and results are being read/written there.")
    else:
        err = storage.get_last_sheets_error()
        st.error(
            "⚠️ Not connected to Google Sheets — running on local fallback storage instead "
            "(logins/results won't be shared across devices or survive a redeploy)."
        )
        if err:
            st.code(err)

    dept_filter = st.selectbox("Department", ["All", "mechanical", "cse"])
    dept_arg = None if dept_filter == "All" else dept_filter

    subj_options = ["All"]
    for d in (["mechanical", "cse"] if dept_arg is None else [dept_arg]):
        subj_options += [s["code"] for s in quiz_data.get_subjects(d)]
    subject_filter = st.selectbox("Subject", subj_options)
    subject_arg = None if subject_filter == "All" else subject_filter

    quiz_options = ["All"] + [f"Quiz {n:02d}" for n in range(1, quiz_data.max_quiz_no() + 1)]
    quiz_filter = st.selectbox("Quiz", quiz_options)
    quiz_arg = None if quiz_filter == "All" else int(quiz_filter.split()[1])

    records = storage.get_all_results(department=dept_arg, subject_code=subject_arg, quiz_no=quiz_arg)
    st.write(f"**{len(records)}** result record(s) found.")

    if records:
        st.dataframe(records, use_container_width=True, hide_index=True)

        csv_lines = [",".join(storage.RESULT_FIELDS)]
        for r in records:
            csv_lines.append(",".join(f'"{str(r.get(f, "")).replace(chr(34), chr(39))}"' for f in storage.RESULT_FIELDS))
        csv_bytes = "\n".join(csv_lines).encode("utf-8")

        pdf_bytes = generate_faculty_report(records, title=f"Quiz Results — {dept_filter} / {subject_filter} / {quiz_filter}")

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "\U0001f4e5 Download full database (CSV)",
                data=csv_bytes, file_name="quiz_results.csv", mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "\U0001f4e5 Download report (PDF)",
                data=pdf_bytes, file_name="quiz_results_report.pdf", mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.info("No results recorded yet for this filter.")

    if records:
        st.divider()
        st.subheader("Individual student")

        def _row_label(r):
            flag = " ⚠️" if str(r.get("flagged")).lower() == "true" else ""
            quiz_tag = f"Q{r.get('quiz_no') or 1}"
            return (f"{r.get('reg_no')} — {r.get('name')} — {r.get('subject_code')} ({quiz_tag}) "
                    f"— Attempt {r.get('attempt_no')} — {r.get('score')}/{r.get('total')}{flag} "
                    f"— {r.get('timestamp')}")

        labels = [_row_label(r) for r in records]
        chosen_idx = st.selectbox("Select a student's attempt:", range(len(records)), format_func=lambda i: labels[i])
        chosen_record = records[chosen_idx]

        c1, c2 = st.columns(2)
        with c1:
            reconstructed = _reconstruct_result_from_record(chosen_record)
            if reconstructed:
                pdf_bytes = generate_student_answer_script(
                    reconstructed, chosen_record.get("name"), chosen_record.get("reg_no"),
                    chosen_record.get("department"),
                )
                st.download_button(
                    "\U0001f4e5 Download this student's answer script (PDF)",
                    data=pdf_bytes,
                    file_name=f"{chosen_record.get('reg_no')}_{chosen_record.get('subject_code')}_q{chosen_record.get('quiz_no') or 1}_attempt{chosen_record.get('attempt_no')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_{chosen_idx}",
                )
            else:
                st.warning("This record predates per-question tracking and can't be regenerated as a PDF.")

        with c2:
            confirm = st.checkbox("Confirm delete — this cannot be undone", key=f"confirm_del_{chosen_idx}")
            if st.button("\U0001f5d1️ Delete this record", use_container_width=True, disabled=not confirm):
                deleted = storage.delete_result(
                    chosen_record.get("timestamp"), chosen_record.get("reg_no"),
                    chosen_record.get("subject_code"), chosen_record.get("quiz_no"),
                    chosen_record.get("attempt_no"),
                )
                if deleted:
                    st.success("Record deleted.")
                else:
                    st.error("Could not find that record to delete (it may have already been removed).")
                st.rerun()

    st.divider()
    if st.button("Log out of admin panel"):
        st.session_state.admin_authed = False
        goto("department")
        st.rerun()


# ---------------------------------------------------------------- router

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

STAGE_HANDLERS = {
    "department": screen_department,
    "login": screen_login,
    "subject": screen_subject,
    "quiz": screen_quiz,
    "result": screen_result,
    "admin_login": screen_admin_login,
    "admin_dashboard": screen_admin_dashboard if st.session_state.admin_authed else screen_admin_login,
}

print(f"[render] reg_no={st.session_state.get('reg_no')} stage={st.session_state.stage}", flush=True)
STAGE_HANDLERS.get(st.session_state.stage, screen_department)()
render_footer(st)
