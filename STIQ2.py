import streamlit as st
from openai import OpenAI
import os
import pandas as pd
from datetime import datetime
import pathlib

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="STI Screening", layout="wide")

# ✅ FIX 1: Safe data folder (Streamlit Cloud compatible)
DATA_PATH = pathlib.Path("data")
DATA_PATH.mkdir(exist_ok=True)

CSV_FILE = DATA_PATH / "sti_latest_record.csv"
TOTAL_STEPS = 8

# ✅ FIX 2: Secrets check
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ กรุณาใส่ OPENAI_API_KEY ใน Streamlit Secrets")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ✅ FIX 3: Query param safe
mode = st.query_params.get("mode", "student")

# =========================
# STUDENT MODE
# =========================
if mode == "student":

    st.title("🩺 STI Screening")

    # Session state init
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "answers" not in st.session_state:
        st.session_state.answers = []
    if "show_result" not in st.session_state:
        st.session_state.show_result = False
    if "result_text" not in st.session_state:
        st.session_state.result_text = ""

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

    # Safety guard
    if len(st.session_state.answers) > TOTAL_STEPS:
        st.session_state.answers = st.session_state.answers[:TOTAL_STEPS]

    # Question flow
    if st.session_state.step < TOTAL_STEPS and not st.session_state.show_result:

        st.progress(st.session_state.step / TOTAL_STEPS)
        st.subheader(QUESTIONS[st.session_state.step])

        ans = st.radio("เลือก:", options, key=f"q_{st.session_state.step}")

        if st.button("ถัดไป", key=f"next_{st.session_state.step}"):
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

                # ✅ FIX 4: removed invalid timeout
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )

            text = res.choices[0].message.content

            # Risk detection
            risk = "ต่ำ"
            if "สูง" in text:
                risk = "สูง"
            elif "ปานกลาง" in text:
                risk = "ปานกลาง"

            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "risk_level": risk,
                "comment": text
            }

            df_new = pd.DataFrame([data])

            # ✅ FIX 5: Append instead of overwrite
            if os.path.exists(CSV_FILE):
                df_old = pd.read_csv(CSV_FILE)
                df_all = pd.concat([df_old, df_new], ignore_index=True)
            else:
                df_all = df_new

            df_all.to_csv(CSV_FILE, index=False)

            # Save to session
            st.session_state.result_text = text
            st.session_state.show_result = True
            st.rerun()

        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")

            if st.button("ลองอีกครั้ง"):
                st.session_state.show_result = False
                st.rerun()

    else:
        st.success("✅ ส่งข้อมูลแล้ว")
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

    st.title("👨‍⚕️ Doctor Dashboard")

    if st.button("🔄 รีเฟรช"):
        st.rerun()

    if not os.path.exists(CSV_FILE):
        st.warning("⏳ ยังไม่มีข้อมูลผู้ป่วย")
        st.stop()

    try:
        df = pd.read_csv(CSV_FILE)

        if df.empty:
            st.warning("ไม่มีข้อมูล")
            st.stop()

        st.subheader("📊 Patient Queue")

        # ✅ Sort high risk first
        risk_order = {"สูง": 0, "ปานกลาง": 1, "ต่ำ": 2}
        df["priority"] = df["risk_level"].map(risk_order)
        df = df.sort_values(by="priority")

        for i, row in df.iterrows():

            risk = row["risk_level"]
            comment = row["comment"]
            timestamp = row["timestamp"]

            with st.container():
                col1, col2 = st.columns([1, 4])

                with col1:
                    if risk == "สูง":
                        st.error("🔴")
                    elif risk == "ปานกลาง":
                        st.warning("🟠")
                    else:
                        st.success("🟢")

                with col2:
                    st.write(f"**ความเสี่ยง: {risk}**")
                    st.caption(f"🕒 {timestamp}")
                    st.write(comment)

                st.divider()

        with st.expander("ดูข้อมูลทั้งหมด"):
            st.dataframe(df)

    except Exception as e:
        st.error(f"❌ อ่านข้อมูลผิดพลาด: {str(e)}")
