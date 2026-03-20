import streamlit as st
from openai import OpenAI
import os
import pandas as pd
from datetime import datetime
import time

# =========================
# CONFIG
# =========================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

CSV_FILE = "sti_latest_record.csv"
TOTAL_STEPS = 8

mode = st.query_params.get("mode", "student")

# =========================
# STUDENT MODE
# =========================
if mode == "student":

    st.title("🩺 STI Screening")

    if "step" not in st.session_state:
        st.session_state.step = 0
        st.session_state.answers = []
        st.session_state.show_result = False

    QUESTIONS = [
        "เพศของคุณ",
        "มีเพศสัมพันธ์ใน 3 เดือนหรือไม่?",
        "ใช้ถุงยางหรือไม่?",
        "มีคู่นอนหลายคนหรือไม่?",
        "มีอาการผิดปกติหรือไม่?",
        "มีแผลหรือไม่?",
        "มีผื่นหรือไม่?",
        "คู่นอนติดโรคหรือไม่?"
    ]

    options = ["ใช่", "ไม่ใช่", "ไม่แน่ใจ"]

    if st.session_state.step < TOTAL_STEPS and not st.session_state.show_result:

        st.progress(st.session_state.step / TOTAL_STEPS)
        st.subheader(QUESTIONS[st.session_state.step])

        ans = st.radio("เลือก:", options)

        if st.button("ถัดไป"):
            st.session_state.answers.append(ans)
            st.session_state.step += 1
            st.rerun()

    elif not st.session_state.show_result:

        prompt = f"ประเมิน STI risk: {st.session_state.answers}"

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        text = res.choices[0].message.content

        risk = "ต่ำ"
        if "สูง" in text:
            risk = "สูง"
        elif "ปานกลาง" in text:
            risk = "ปานกลาง"

        data = {
            "timestamp": datetime.now(),
            "risk_level": risk,
            "comment": text
        }

        pd.DataFrame([data]).to_csv(CSV_FILE, index=False)

        st.success("ส่งข้อมูลแล้ว")
        st.write(text)

        time.sleep(5)
        st.session_state.step = 0
        st.session_state.answers = []
        st.session_state.show_result = False
        st.rerun()

# =========================
# DOCTOR MODE
# =========================
else:

    st.title("👨‍⚕️ Doctor View")

    # auto refresh
    time.sleep(3)
    st.rerun()

    if not os.path.exists(CSV_FILE):
        st.warning("Waiting for patient...")
        st.stop()

    df = pd.read_csv(CSV_FILE)

    if df.empty:
        st.warning("No data")
        st.stop()

    latest = df.iloc[-1]

    risk = latest["risk_level"]

    if risk == "สูง":
        st.error("🔴 HIGH RISK")
    elif risk == "ปานกลาง":
        st.warning("🟠 MODERATE RISK")
    else:
        st.success("🟢 LOW RISK")

    st.write(latest["comment"])
    st.caption(latest["timestamp"])