import streamlit as st
from openai import OpenAI
import os
import pandas as pd
from datetime import datetime

# =========================
# CONFIG
# =========================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API key not found in secrets. Please add it to your Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# NOTE: This CSV is written to the ephemeral filesystem on Streamlit Cloud.
# Data will be lost on app restart. For persistence, use a database or
# Streamlit's st.session_state shared across users (not recommended for production).
CSV_FILE = "sti_latest_record.csv"
TOTAL_STEPS = 8

# FIX 1: st.query_params returns a plain string, not a list
mode = st.query_params.get("mode", "student")

# =========================
# QUESTIONS & OPTIONS
# =========================
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

# FIX 2: Question 0 is a gender question — give it appropriate options
QUESTION_OPTIONS = [
    ["ชาย", "หญิง", "อื่นๆ"],                      # เพศ
    ["ใช่", "ไม่ใช่"],                              # มีเพศสัมพันธ์
    ["ใช่", "ไม่ใช่", "บางครั้ง"],                  # ใช้ถุงยาง
    ["ใช่", "ไม่ใช่"],                              # มีคู่นอนหลายคน
    ["ใช่", "ไม่ใช่", "ไม่แน่ใจ"],                  # มีอาการผิดปกติ
    ["ใช่", "ไม่ใช่"],                              # มีแผล
    ["ใช่", "ไม่ใช่"],                              # มีผื่น
    ["ใช่", "ไม่ใช่", "ไม่ทราบ"],                   # คู่นอนติดโรค
]

# =========================
# STUDENT MODE
# =========================
if mode == "student":

    st.title("🩺 STI Screening")

    if "step" not in st.session_state:
        st.session_state.step = 0
    if "answers" not in st.session_state:
        st.session_state.answers = []
    if "show_result" not in st.session_state:
        st.session_state.show_result = False
    if "result_text" not in st.session_state:
        st.session_state.result_text = ""

    # FIX 3: Guard against step going out of bounds
    current_step = st.session_state.step
    if current_step < TOTAL_STEPS and not st.session_state.show_result:

        st.progress(current_step / TOTAL_STEPS)
        st.subheader(QUESTIONS[current_step])

        options = QUESTION_OPTIONS[current_step]
        ans = st.radio("เลือก:", options, key=f"q_{current_step}")

        if st.button("ถัดไป", key=f"next_{current_step}"):
            st.session_state.answers.append(ans)
            st.session_state.step += 1
            st.rerun()

    elif not st.session_state.show_result:

        prompt = (
            f"Based on the following STI risk assessment answers: {st.session_state.answers}. "
            "Please provide a risk assessment (low, medium, or high) and recommendations in Thai language."
        )

        try:
            with st.spinner("กำลังวิเคราะห์..."):
                # FIX 4: Remove unsupported `timeout` kwarg from openai v1 SDK
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )

            text = res.choices[0].message.content

            # Determine risk level
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

            df = pd.DataFrame([data])
            df.to_csv(CSV_FILE, index=False)

            st.session_state.result_text = text
            st.session_state.show_result = True
            st.rerun()

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            if st.button("ลองอีกครั้ง"):
                st.session_state.show_result = False
                st.rerun()

    else:
        st.success("ส่งข้อมูลแล้ว")
        st.write(st.session_state.result_text)

        if st.button("เริ่มใหม่"):
            st.session_state.step = 0
            st.session_state.answers = []
            st.session_state.show_result = False
            st.session_state.result_text = ""
            st.rerun()

# =========================
# DOCTOR MODE
# =========================
else:

    st.title("👨‍⚕️ Doctor View")

    if st.button("🔄 รีเฟรช"):
        st.rerun()

    if not os.path.exists(CSV_FILE):
        st.warning("รอข้อมูลผู้ป่วย...")
        st.info("กรุณารอสักครู่ หรือกดปุ่มรีเฟรช")
        st.stop()

    try:
        df = pd.read_csv(CSV_FILE)

        if df.empty:
            st.warning("ไม่มีข้อมูล")
            st.stop()

        latest = df.iloc[-1]

        risk = latest["risk_level"]
        comment = latest["comment"] if pd.notna(latest["comment"]) else "ไม่มีความคิดเห็น"
        timestamp = latest["timestamp"] if pd.notna(latest["timestamp"]) else "ไม่ระบุเวลา"

        col1, col2 = st.columns([1, 3])

        with col1:
            if risk == "สูง":
                st.error("🔴")
            elif risk == "ปานกลาง":
                st.warning("🟠")
            else:
                st.success("🟢")

        with col2:
            if risk == "สูง":
                st.error("**ระดับความเสี่ยง: สูง**")
            elif risk == "ปานกลาง":
                st.warning("**ระดับความเสี่ยง: ปานกลาง**")
            else:
                st.success("**ระดับความเสี่ยง: ต่ำ**")

        st.divider()
        st.write("**ความคิดเห็น:**")
        st.write(comment)
        st.caption(f"บันทึกเมื่อ: {timestamp}")

        with st.expander("ดูประวัติทั้งหมด"):
            st.dataframe(df)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านข้อมูล: {str(e)}")
