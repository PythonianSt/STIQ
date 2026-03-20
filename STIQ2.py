import streamlit as st
from openai import OpenAI
import os
import pandas as pd
from datetime import datetime
import time

# =========================
# CONFIG
# =========================
# Check if API key exists in secrets
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API key not found in secrets. Please add it to your Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

CSV_FILE = "sti_latest_record.csv"
TOTAL_STEPS = 8

# Get mode from query params, default to "student"
mode = st.query_params.get("mode", ["student"])[0] if "mode" in st.query_params else "student"

# =========================
# STUDENT MODE
# =========================
if mode == "student":

    st.title("🩺 STI Screening")

    # Initialize session state
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

        # Use a unique key for radio button
        ans = st.radio("เลือก:", options, key=f"q_{st.session_state.step}")

        if st.button("ถัดไป", key=f"next_{st.session_state.step}"):
            st.session_state.answers.append(ans)
            st.session_state.step += 1
            st.rerun()

    elif not st.session_state.show_result:
        
        # Prepare prompt with context
        prompt = f"Based on the following STI risk assessment answers: {st.session_state.answers}. Please provide a risk assessment (low, medium, or high) and recommendations in Thai language."

        try:
            with st.spinner("กำลังวิเคราะห์..."):
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=30
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

            # Create DataFrame and save to CSV
            df = pd.DataFrame([data])
            df.to_csv(CSV_FILE, index=False)

            st.success("ส่งข้อมูลแล้ว")
            st.write(text)

            # Set flag to show result
            st.session_state.show_result = True
            st.rerun()
            
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            if st.button("ลองอีกครั้ง"):
                st.session_state.show_result = False
                st.rerun()

    else:
        # Show result and option to restart
        if st.button("เริ่มใหม่"):
            st.session_state.step = 0
            st.session_state.answers = []
            st.session_state.show_result = False
            st.rerun()

# =========================
# DOCTOR MODE
# =========================
else:

    st.title("👨‍⚕️ Doctor View")
    
    # Add refresh button
    if st.button("🔄 รีเฟรช"):
        st.rerun()

    # Check if file exists
    if not os.path.exists(CSV_FILE):
        st.warning("รอข้อมูลผู้ป่วย...")
        st.info("กรุณารอสักครู่ หรือกดปุ่มรีเฟรช")
        st.stop()

    try:
        df = pd.read_csv(CSV_FILE)

        if df.empty:
            st.warning("ไม่มีข้อมูล")
            st.stop()

        # Get latest record
        latest = df.iloc[-1]

        risk = latest["risk_level"]
        comment = latest["comment"] if pd.notna(latest["comment"]) else "ไม่มีความคิดเห็น"
        timestamp = latest["timestamp"] if pd.notna(latest["timestamp"]) else "ไม่ระบุเวลา"

        # Display risk with appropriate color
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
        
        # Show all records in expander
        with st.expander("ดูประวัติทั้งหมด"):
            st.dataframe(df)
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านข้อมูล: {str(e)}")
