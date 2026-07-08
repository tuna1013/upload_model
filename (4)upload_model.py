import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

st.set_page_config(layout="wide")
st.title("📡 실시간 다변수 이상치 탐지 시스템")

# -------------------------
# 📂 파일 업로드
# -------------------------
uploaded_file = st.file_uploader("파일 업로드")

# -------------------------
# ⚙️ 설정값
# -------------------------
window_size = st.slider("Window Size", 10, 100, 30)
threshold = st.slider("Threshold", 1.0, 100.0, 2.6)
speed = st.slider("재생 속도", min_value=0.001, max_value=0.1, value=0.001, step=0.001, format="%.3f")

# -------------------------
# 📊 Z-score 함수 (루프 밖으로)
# -------------------------
def compute_score(value, window):
    median = np.median(window)
    mad = np.median(np.abs(window - median))
    mad = max(mad, 1e-2)
    return 0.6745 * (value - median) / mad

# -------------------------
# 📊 데이터 처리
# -------------------------
if uploaded_file:

    # csv / xlsx 분기
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    required_cols = [
        "Flow Bytes/s",
        "Flow Duration",
        "Packet Length Mean",
        "Flow Packets/s",
        "ACK Flag Count"
    ]

    if not all(col in df.columns for col in required_cols):
        st.error("필수 컬럼이 없습니다!")
    else:
        traffic = df["Flow Bytes/s"].values
        duration = df["Flow Duration"].values
        pkt_len = df["Packet Length Mean"].values
        pkt_rate = df["Flow Packets/s"].values
        ack = df["ACK Flag Count"].values

        scores = []
        warnings = []
        anomalies = []

        chart = st.empty()

        for i in range(len(traffic)):

            if i < window_size:
                scores.append(np.nan)
                continue

            # window
            t_win = traffic[i-window_size:i]
            d_win = duration[i-window_size:i]
            p_win = pkt_len[i-window_size:i]
            r_win = pkt_rate[i-window_size:i]
            a_win = ack[i-window_size:i]

            s1 = compute_score(traffic[i], t_win)
            s2 = compute_score(duration[i], d_win)
            s3 = compute_score(pkt_len[i], p_win)
            s4 = compute_score(pkt_rate[i], r_win)
            s5 = compute_score(ack[i], a_win)

            score = (
                0.35 * abs(s1) +
                0.2  * abs(s2) +
                0.15 * abs(s3) +
                0.25 * abs(s4) +
                0.05 * abs(s5)
            )

            scores.append(score)

            if score > threshold:
                warnings.append(i)
            if score > threshold * 1.5:  # threshold 기준으로 변경
                anomalies.append(i)

            # -------------------------
            # 📈 그래프 (200번에 1번만 업데이트)
            # -------------------------
            if i % 2000 == 0:
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(traffic[:i], label="Flow Bytes/s", color="steelblue")

                if warnings:
                    ax.scatter(warnings, traffic[warnings],
                               color="orange", label="Warning", zorder=5)
                if anomalies:
                    ax.scatter(anomalies, traffic[anomalies],
                               color="red", label="Anomaly", zorder=6)

                ax.legend()
                ax.set_title(f"실시간 탐지 (index: {i})")
                ax.set_ylim(0, 10)
                ax.set_xlabel("Index")
                ax.set_ylabel("Flow Bytes/s")

                chart.pyplot(fig)
                plt.close(fig)

            time.sleep(speed)

        # -------------------------
        # 📊 결과
        # -------------------------
        st.success("분석 완료!")
        st.write(f"⚠️ Warning: {len(warnings)}개")
        st.write(f"🚨 Anomaly: {len(anomalies)}개")