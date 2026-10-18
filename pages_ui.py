"""pages_ui.py - the screens of the Thyroid CDSM (hospital-styled)."""

import io
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

import database as db
import model as ml
import report

# Reference ranges (edit to match the clinical source you cite)
NORMAL_RANGES = {
    "TSH": (0.4, 4.0), "T3": (1.0, 2.8), "TT4": (60, 140),
    "T4U": (0.7, 1.3), "FTI": (60, 140),
}

RISK_LEVEL = {
    "Negative":                ("LOW",       "#2e7d32"),
    "Compensated Hypothyroid": ("MEDIUM",    "#f57f17"),
    "Primary Hypothyroid":     ("HIGH",      "#c62828"),
    "Hyperthyroid":            ("HIGH",      "#c62828"),
    "Other Thyroid Condition": ("REFER NOW", "#6a1b9a"),
}

# (model feature name, friendly label) for the tickable medical history
HISTORY_FIELDS = [
    ("on_thyroxine", "On thyroxine"),
    ("query_on_thyroxine", "Query on thyroxine"),
    ("on_antithyroid_medication", "On antithyroid medication"),
    ("sick", "Currently sick"),
    ("pregnant", "Pregnant"),
    ("thyroid_surgery", "Thyroid surgery (history)"),
    ("I131_treatment", "I-131 treatment (history)"),
    ("query_hypothyroid", "Query hypothyroid"),
    ("query_hyperthyroid", "Query hyperthyroid"),
    ("lithium", "On lithium"),
    ("goitre", "Goitre"),
    ("tumor", "Tumour"),
    ("hypopituitary", "Hypopituitary"),
    ("psych", "Psychiatric symptoms"),
]

PALETTE = px.colors.qualitative.Set2


def _go(page):
    """Callback for quick-access buttons - switches the sidebar nav."""
    st.session_state.nav = page


def _card(title=""):
    """Open a styled white card container; returns the container."""
    c = st.container()
    if title:
        c.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
    return c


def _hormone_figure(values: dict):
    rows = []
    for h, (lo, hi) in NORMAL_RANGES.items():
        v = values[h]
        status = "Low" if v < lo else "High" if v > hi else "Normal"
        rows.append({"Hormone": h, "Position": (v - lo) / (hi - lo) if hi > lo else 0,
                     "Status": status, "Value": v, "Range": f"{lo}-{hi}"})
    d = pd.DataFrame(rows)
    fig = px.bar(d, x="Hormone", y="Position", color="Status",
                 color_discrete_map={"Normal": "#2e7d32", "Low": "#1565c0", "High": "#c62828"},
                 hover_data={"Value": True, "Range": True, "Position": False},
                 title="Hormone levels vs normal range")
    fig.add_hrect(y0=0, y1=1, fillcolor="#a5d6a7", opacity=0.25, line_width=0)
    fig.update_layout(yaxis_title="0 = low limit • 1 = high limit",
                      plot_bgcolor="white", height=340, margin=dict(t=50, b=10))
    return fig


# ============================ DIAGNOSE ============================
def page_diagnose(user):
    st.markdown("## 🩺 Diagnose a Patient")

    with st.form("diagnose_form"):
        _card().markdown("<div class='card-title'>Patient details</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        ic   = c1.text_input("IC number")
        name = c2.text_input("Name")
        age  = c3.number_input("Age", 0, 120, 40)
        sex  = c4.selectbox("Sex", ["F", "M"])

        st.markdown("<div class='card-title'>Hormone test results</div>", unsafe_allow_html=True)
        h1, h2, h3, h4, h5 = st.columns(5)
        tsh = h1.number_input("TSH", 0.0, value=1.5, format="%.2f")
        t3  = h2.number_input("T3",  0.0, value=2.0, format="%.2f")
        tt4 = h3.number_input("TT4", 0.0, value=110.0, format="%.1f")
        t4u = h4.number_input("T4U", 0.0, value=1.0, format="%.2f")
        fti = h5.number_input("FTI", 0.0, value=110.0, format="%.1f")

        st.markdown("<div class='card-title'>Medical history "
                    "<span style='font-weight:400;color:#6b7a8d'>(tick all that apply)</span></div>",
                    unsafe_allow_html=True)
        ticks = {}
        cols = st.columns(4)
        for i, (field, label) in enumerate(HISTORY_FIELDS):
            ticks[field] = cols[i % 4].checkbox(label, key=f"hx_{field}")

        submitted = st.form_submit_button("🔍  Diagnose & Save", type="primary",
                                          use_container_width=True)

    if submitted:
        st.session_state.pop("pending_diag", None)   # clear any stale prompt
        if not ic or not name:
            st.warning("Please enter both an IC number and a name.")
            return

        hormones = {"TSH": tsh, "T3": t3, "TT4": tt4, "T4U": t4u, "FTI": fti}
        model_inputs = {**hormones, "age": age, "sex": 1 if sex == "M" else 0,
                        **{f: int(v) for f, v in ticks.items()}}
        history_str = ", ".join(lbl for (f, lbl) in HISTORY_FIELDS if ticks[f]) or "None"

        existing = db.get_patient_by_ic(ic)
        # IC already registered to a DIFFERENT name -> pause for confirmation
        if existing and existing["name"].strip().lower() != name.strip().lower():
            st.session_state.pending_diag = {
                "ic": ic, "typed_name": name, "stored_name": existing["name"],
                "age": int(age), "sex": sex, "hormones": hormones,
                "model_inputs": model_inputs, "history": history_str}
            st.rerun()
        else:
            _render_result(user, ic, name, int(age), sex,
                           hormones, model_inputs, history_str)
        return

    # name-mismatch confirmation prompt
    pending = st.session_state.get("pending_diag")
    if pending:
        st.warning(
            f"⚠️ IC **{pending['ic']}** is already registered to "
            f"**{pending['stored_name']}**, but you entered **{pending['typed_name']}**. "
            "Please verify this is the correct patient before saving.")
        c1, c2 = st.columns(2)
        if c1.button("✅  Same patient — save anyway", type="primary",
                     use_container_width=True):
            p = st.session_state.pop("pending_diag")
            _render_result(user, p["ic"], p["stored_name"], p["age"], p["sex"],
                           p["hormones"], p["model_inputs"], p["history"])
        if c2.button("✖️  Cancel — do not save", use_container_width=True):
            st.session_state.pop("pending_diag", None)
            st.info("Cancelled. No record was saved. Check the IC number and try again.")
    return


def _render_result(user, ic, name, age, sex, hormones, model_inputs, history_str):
    """Run the prediction, save the record, and display the result block."""
    label, confidence, probs = ml.predict(model_inputs)
    risk_text, risk_color = RISK_LEVEL.get(label, ("UNKNOWN", "#555"))

    existing = db.get_patient_by_ic(ic)
    pid = db.add_or_get_patient(ic, name, int(age), sex)
    db.save_diagnosis(pid, hormones, label, confidence, user["username"], history_str)
    db.log_action(user["username"], "diagnose", f"{name} ({ic}) -> {label} {confidence}%")

    st.success("Diagnosis saved." +
               (" Linked to existing patient record." if existing else ""))

    # result cards
    r1, r2, r3 = st.columns(3)
    r1.markdown(f"<div class='result-card' style='border-left:6px solid #0E7C7B'>"
                f"<div class='rc-label'>Diagnosis</div>"
                f"<div class='rc-value'>{label}</div></div>", unsafe_allow_html=True)
    r2.markdown(f"<div class='result-card' style='border-left:6px solid #1565C0'>"
                f"<div class='rc-label'>Confidence</div>"
                f"<div class='rc-value'>{confidence}%</div></div>", unsafe_allow_html=True)
    r3.markdown(f"<div class='result-card' style='border-left:6px solid {risk_color}'>"
                f"<div class='rc-label'>Risk level</div>"
                f"<div class='rc-value' style='color:{risk_color}'>{risk_text}</div></div>",
                unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left:
        st.plotly_chart(_hormone_figure(hormones), use_container_width=True)
    with right:
        prob_df = pd.DataFrame({"Diagnosis": list(probs.keys()),
                                "Probability": list(probs.values())})
        fig = px.bar(prob_df.sort_values("Probability"), x="Probability", y="Diagnosis",
                     orientation="h", title="Class probabilities (%)",
                     color="Probability", color_continuous_scale="Teal")
        fig.update_layout(height=340, plot_bgcolor="white", margin=dict(t=50, b=10),
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    t = db.get_treatment(label)
    if t:
        st.markdown("<div class='card-title'>💊 Treatment recommendation</div>",
                    unsafe_allow_html=True)
        st.markdown(
            f"<div class='treat-card'>"
            f"<b>Medication:</b> {t['medication']}<br>"
            f"<b>Dosage:</b> {t['dosage']}<br>"
            f"<b>Lifestyle advice:</b> {t['lifestyle_advice']}<br>"
            f"<b>Follow-up:</b> in {t['followup_weeks']} weeks</div>",
            unsafe_allow_html=True)

    # printable PDF report
    pdf_bytes = report.build_report(
        patient={"name": name, "ic_number": ic, "age": int(age), "sex": sex},
        diagnosis={"result": label, "confidence": confidence, "risk": risk_text},
        treatment=t,
        hormones=hormones,
        history=history_str,
        diagnosed_by=user["username"])
    st.download_button(
        "🖨️  Print / Download PDF report", pdf_bytes,
        file_name=f"thyroid_report_{ic}_{datetime.now():%Y%m%d}.pdf",
        mime="application/pdf", type="primary")

    if existing:
        st.markdown("<div class='card-title'>📁 Previous visits</div>", unsafe_allow_html=True)
        st.dataframe(db.get_patient_history(pid), use_container_width=True)


# ========================= PATIENT RECORDS =========================
def page_records(user):
    st.markdown("## 📁 Patient Records")
    c1, c2, c3 = st.columns(3)
    f_name = c1.text_input("Search by name")
    f_ic   = c2.text_input("Search by IC")
    f_diag = c3.selectbox("Filter by diagnosis",
                          ["", "Negative", "Hyperthyroid", "Primary Hypothyroid",
                           "Compensated Hypothyroid", "Other Thyroid Condition"])
    df = db.search_records(f_name, f_ic, f_diag)
    st.caption(f"{len(df)} record(s) found")
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="records")
        st.download_button("⬇️  Export to Excel", buf.getvalue(),
                           file_name=f"thyroid_records_{datetime.now():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ============================ DASHBOARD ============================
def page_dashboard(user):
    st.markdown("## 📊 Statistics Dashboard")

    # quick-access buttons
    q1, q2, q3 = st.columns(3)
    q1.button("🩺  Run New Diagnosis", on_click=_go, args=("Diagnose",),
              use_container_width=True, type="primary")
    q2.button("📁  View Patient Records", on_click=_go, args=("Patient Records",),
              use_container_width=True)
    q3.button("👤  My Account", on_click=_go, args=("My Account",),
              use_container_width=True)

    data = db.get_dashboard_data()
    n_patients, n_diag = db.get_counts()

    if data.empty:
        st.info("No diagnoses recorded yet. Run a few diagnoses to populate the dashboard.")
        return

    data["diagnosed_at"] = pd.to_datetime(data["diagnosed_at"], errors="coerce")

    # interactive filter
    all_diag = sorted(data["diagnosis_result"].dropna().unique())
    chosen = st.multiselect("Filter by diagnosis", all_diag, default=all_diag)
    view = data[data["diagnosis_result"].isin(chosen)] if chosen else data

    # KPI cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total patients", n_patients)
    k2.metric("Total diagnoses", n_diag)
    top = view["diagnosis_result"].mode()
    k3.metric("Most common", top.iloc[0] if not top.empty else "-")
    k4.metric("Avg confidence", f"{view['confidence_score'].mean():.1f}%"
              if not view.empty else "-")

    if view.empty:
        st.warning("No data for the selected filter.")
        return

    # row 1: donut + bar
    c1, c2 = st.columns(2)
    counts = view["diagnosis_result"].value_counts().reset_index()
    counts.columns = ["Diagnosis", "Count"]
    with c1:
        fig = px.pie(counts, names="Diagnosis", values="Count", hole=0.45,
                     title="Diagnosis distribution", color_discrete_sequence=PALETTE)
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(counts, x="Diagnosis", y="Count", title="Diagnosis counts",
                     color="Diagnosis", color_discrete_sequence=PALETTE)
        fig.update_layout(height=360, plot_bgcolor="white", showlegend=False,
                          xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    # row 2: confidence box + age groups
    c3, c4 = st.columns(2)
    with c3:
        fig = px.box(view, x="diagnosis_result", y="confidence_score",
                     title="Confidence by diagnosis", color="diagnosis_result",
                     color_discrete_sequence=PALETTE)
        fig.update_layout(height=360, plot_bgcolor="white", showlegend=False,
                          xaxis_title="", yaxis_title="Confidence (%)")
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        bins = [0, 18, 35, 50, 65, 120]
        labels = ["0-18", "19-35", "36-50", "51-65", "65+"]
        view = view.copy()
        view["Age group"] = pd.cut(view["age"], bins=bins, labels=labels)
        ag = view["Age group"].value_counts().reindex(labels, fill_value=0).reset_index()
        ag.columns = ["Age group", "Count"]
        fig = px.bar(ag, x="Age group", y="Count", title="Patients by age group",
                     color_discrete_sequence=["#0E7C7B"])
        fig.update_layout(height=360, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    # row 3: trend over time + sex split
    c5, c6 = st.columns(2)
    with c5:
        trend = (view.dropna(subset=["diagnosed_at"])
                 .groupby(view["diagnosed_at"].dt.date).size().reset_index(name="Count"))
        trend.columns = ["Date", "Count"]
        fig = px.line(trend, x="Date", y="Count", markers=True,
                      title="Diagnoses over time")
        fig.update_layout(height=340, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        sx = view["sex"].value_counts().reset_index()
        sx.columns = ["Sex", "Count"]
        fig = px.pie(sx, names="Sex", values="Count", title="Sex distribution",
                     color_discrete_sequence=["#1565C0", "#0E7C7B"])
        fig.update_layout(height=340)
        st.plotly_chart(fig, use_container_width=True)


# ============================ MY ACCOUNT ============================
def page_account(user):
    st.markdown("## 👤 My Account")
    st.write(f"**Username:** {user['username']}")
    st.write(f"**Role:** {user['role']}")
    with st.form("pw"):
        new1 = st.text_input("New password", type="password")
        new2 = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Change password"):
            if not new1:
                st.warning("Password cannot be empty.")
            elif new1 != new2:
                st.error("Passwords do not match.")
            else:
                db.change_password(user["username"], new1)
                db.log_action(user["username"], "change_password", "")
                st.success("Password changed.")


# ============================== ADMIN ==============================
def page_admin(user):
    st.markdown("## ⚙️ Administration")
    st.markdown("<div class='card-title'>Users</div>", unsafe_allow_html=True)
    st.dataframe(db.get_all_users(), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Add user**")
        with st.form("add_user"):
            u  = st.text_input("Username")
            p  = st.text_input("Password", type="password")
            r  = st.selectbox("Role", ["doctor", "nurse", "admin"])
            fn = st.text_input("Full name")
            if st.form_submit_button("Add"):
                if db.add_user(u, p, r, fn):
                    db.log_action(user["username"], "add_user", u)
                    st.success(f"User '{u}' added."); st.rerun()
                else:
                    st.error("Username already exists.")
    with c2:
        st.markdown("**Delete user**")
        users = db.get_all_users()["username"].tolist()
        with st.form("del_user"):
            target = st.selectbox("Select user", users)
            if st.form_submit_button("Delete"):
                if target == user["username"]:
                    st.error("You cannot delete your own account.")
                else:
                    db.delete_user(target)
                    db.log_action(user["username"], "delete_user", target)
                    st.success(f"User '{target}' deleted."); st.rerun()

    st.markdown("<div class='card-title'>Activity log</div>", unsafe_allow_html=True)
    st.dataframe(db.get_activity_log(), use_container_width=True)

    st.markdown("<div class='card-title'>Database backup</div>", unsafe_allow_html=True)
    with open(db.DB_PATH, "rb") as f:
        st.download_button("⬇️  Download database backup", f.read(),
                           file_name="thyroid_cdsm_backup.db")