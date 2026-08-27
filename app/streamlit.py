import os

import requests
import streamlit as st

INFERENCE_URL = os.environ.get(
    "INFERENCE_URL",
    "http://<IP>:<PORT>/invocations",
)

st.set_page_config(
    page_title="Telco Churn Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600&display=swap');

      html, body, [class*="css"] { font-family: "DM Sans", sans-serif; }

      .stApp {
        background:
          radial-gradient(1200px 500px at 10% -10%, #1e3a5f 0%, transparent 50%),
          radial-gradient(900px 400px at 110% 10%, #3d1f4a 0%, transparent 45%),
          linear-gradient(180deg, #0b1220 0%, #111827 40%, #0f172a 100%);
        color: #e5e7eb;
      }

      .hero-kicker {
        letter-spacing: 0.18em;
        text-transform: uppercase;
        font-size: 0.72rem;
        color: #93c5fd;
        font-weight: 700;
        margin-bottom: 0.35rem;
      }
      .hero-title {
        font-family: Fraunces, Georgia, serif;
        font-size: 2.4rem;
        line-height: 1.15;
        color: #f8fafc;
        margin: 0 0 0.4rem 0;
      }
      .hero-sub { color: #94a3b8; font-size: 1.02rem; max-width: 42rem; }

      div[data-testid="stForm"] {
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 1.25rem 1.25rem 0.5rem 1.25rem;
        box-shadow: 0 20px 50px rgba(0,0,0,0.35);
      }

      .section-label {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #7dd3fc;
        margin: 0.4rem 0 0.8rem 0;
      }

      .result-card {
        border-radius: 20px;
        padding: 1.4rem 1.5rem;
        border: 1px solid rgba(255,255,255,0.08);
      }
      .result-stay {
        background: linear-gradient(135deg, rgba(6,95,70,0.55), rgba(15,23,42,0.9));
      }
      .result-churn {
        background: linear-gradient(135deg, rgba(127,29,29,0.6), rgba(15,23,42,0.9));
      }
      .result-kicker { font-size: 0.75rem; letter-spacing: 0.14em; text-transform: uppercase; color: #cbd5e1; }
      .result-main { font-family: Fraunces, Georgia, serif; font-size: 2rem; margin: 0.25rem 0 0.5rem 0; }
      .chip {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        background: rgba(255,255,255,0.08);
        margin-right: 0.35rem;
      }

      #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

HIGH_RISK = dict(
    gender="Female",
    senior=0,
    partner="No",
    dependents="No",
    tenure=2,
    phone="Yes",
    multiple_lines="No",
    internet="Fiber optic",
    online_sec="No",
    online_bak="No",
    device_prot="No",
    tech="No",
    stream_tv="No",
    stream_mov="No",
    contract="Month-to-month",
    paperless="Yes",
    payment="Electronic check",
    monthly=70.70,
    total=151.65,
)
LOYAL = dict(
    gender="Female",
    senior=0,
    partner="Yes",
    dependents="Yes",
    tenure=69,
    phone="Yes",
    multiple_lines="Yes",
    internet="Fiber optic",
    online_sec="Yes",
    online_bak="Yes",
    device_prot="Yes",
    tech="Yes",
    stream_tv="Yes",
    stream_mov="Yes",
    contract="Two year",
    paperless="No",
    payment="Credit card (automatic)",
    monthly=113.25,
    total=7895.15,
)

with st.sidebar:
    st.markdown("### Quick fill")
    preset = st.radio(
        "Customer profile",
        ["Current values", "High risk", "Loyal customer"],
        index=0,
        label_visibility="collapsed",
    )

defaults = HIGH_RISK if preset == "High risk" else LOYAL if preset == "Loyal customer" else {}

st.markdown('<div class="hero-kicker">Customer retention</div>', unsafe_allow_html=True)
st.markdown('<p class="hero-title">Will this customer leave?</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Enter account details to estimate churn risk.</p>',
    unsafe_allow_html=True,
)
st.write("")

left, right = st.columns([1.35, 0.9], gap="large")

with left:
    with st.form("churn_form"):
        st.markdown('<div class="section-label">Account</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        gender = c1.selectbox("Gender", ["Female", "Male"], index=["Female", "Male"].index(defaults.get("gender", "Female")))
        senior = c2.selectbox("Senior citizen", [0, 1], index=int(defaults.get("senior", 0)))
        partner = c3.selectbox("Partner", ["Yes", "No"], index=["Yes", "No"].index(defaults.get("partner", "Yes")))
        dependents = c4.selectbox("Dependents", ["Yes", "No"], index=["Yes", "No"].index(defaults.get("dependents", "No")))

        c5, c6, c7 = st.columns(3)
        tenure = c5.number_input("Tenure (months)", 0, 100, int(defaults.get("tenure", 12)))
        phone = c6.selectbox("Phone service", ["Yes", "No"], index=["Yes", "No"].index(defaults.get("phone", "Yes")))
        multiple_lines = c7.selectbox(
            "Multiple lines",
            ["No phone service", "No", "Yes"],
            index=["No phone service", "No", "Yes"].index(defaults.get("multiple_lines", "No")),
        )

        st.markdown('<div class="section-label">Internet & add-ons</div>', unsafe_allow_html=True)
        i1, i2, i3 = st.columns(3)
        internet = i1.selectbox(
            "Internet",
            ["DSL", "Fiber optic", "No"],
            index=["DSL", "Fiber optic", "No"].index(defaults.get("internet", "DSL")),
        )
        online_sec = i2.selectbox(
            "Online security",
            ["Yes", "No", "No internet service"],
            index=["Yes", "No", "No internet service"].index(defaults.get("online_sec", "No")),
        )
        online_bak = i3.selectbox(
            "Online backup",
            ["Yes", "No", "No internet service"],
            index=["Yes", "No", "No internet service"].index(defaults.get("online_bak", "No")),
        )
        i4, i5, i6 = st.columns(3)
        device_prot = i4.selectbox(
            "Device protection",
            ["Yes", "No", "No internet service"],
            index=["Yes", "No", "No internet service"].index(defaults.get("device_prot", "No")),
        )
        tech = i5.selectbox(
            "Tech support",
            ["Yes", "No", "No internet service"],
            index=["Yes", "No", "No internet service"].index(defaults.get("tech", "No")),
        )
        stream_tv = i6.selectbox(
            "Streaming TV",
            ["Yes", "No", "No internet service"],
            index=["Yes", "No", "No internet service"].index(defaults.get("stream_tv", "No")),
        )
        stream_mov = st.selectbox(
            "Streaming movies",
            ["Yes", "No", "No internet service"],
            index=["Yes", "No", "No internet service"].index(defaults.get("stream_mov", "No")),
        )

        st.markdown('<div class="section-label">Billing</div>', unsafe_allow_html=True)
        b1, b2, b3 = st.columns(3)
        contract = b1.selectbox(
            "Contract",
            ["Month-to-month", "One year", "Two year"],
            index=["Month-to-month", "One year", "Two year"].index(defaults.get("contract", "Month-to-month")),
        )
        paperless = b2.selectbox(
            "Paperless billing",
            ["Yes", "No"],
            index=["Yes", "No"].index(defaults.get("paperless", "Yes")),
        )
        payment = b3.selectbox(
            "Payment method",
            [
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ],
            index=[
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ].index(defaults.get("payment", "Electronic check")),
        )
        m1, m2 = st.columns(2)
        monthly = m1.number_input("Monthly charges ($)", 0.0, 250.0, float(defaults.get("monthly", 70.0)), step=0.05)
        total = m2.number_input("Total charges ($)", 0.0, 10000.0, float(defaults.get("total", 500.0)), step=0.05)

        submitted = st.form_submit_button("Score customer", use_container_width=True)

with right:
    st.markdown("#### Result")
    result_box = st.container()

if submitted:
    row = {
        "gender": gender,
        "SeniorCitizen": int(senior),
        "Partner": partner,
        "Dependents": dependents,
        "tenure": int(tenure),
        "PhoneService": phone,
        "MultipleLines": multiple_lines,
        "InternetService": internet,
        "OnlineSecurity": online_sec,
        "OnlineBackup": online_bak,
        "DeviceProtection": device_prot,
        "TechSupport": tech,
        "StreamingTV": stream_tv,
        "StreamingMovies": stream_mov,
        "Contract": contract,
        "PaperlessBilling": paperless,
        "PaymentMethod": payment,
        "MonthlyCharges": float(monthly),
        "TotalCharges": float(total),
    }
    try:
        response = requests.post(
            INFERENCE_URL,
            json={"dataframe_records": [row]},
            timeout=30,
        )
        response.raise_for_status()
        pred = int(response.json()["predictions"][0])
        churn = pred == 1
        klass = "result-churn" if churn else "result-stay"
        title = "Likely to churn" if churn else "Likely to stay"
        kicker = "High risk" if churn else "Lower risk"
        with result_box:
            st.markdown(
                f"""
                <div class="result-card {klass}">
                  <div class="result-kicker">{kicker}</div>
                  <div class="result-main">{title}</div>
                  <span class="chip">{contract}</span>
                  <span class="chip">{tenure} mo tenure</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    except requests.RequestException:
        with result_box:
            st.error("Scoring is unavailable right now. Try again in a moment.")
else:
    with result_box:
        st.info("Fill in the customer details and click Score customer.")
