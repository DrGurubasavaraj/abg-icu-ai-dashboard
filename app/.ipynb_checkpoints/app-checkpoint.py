import pickle

# Load trained model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)
import streamlit as st
import pandas as pd

# Title
st.title("🫁 ICU ABG + Ventilator Decision Dashboard")

st.markdown("Clinical decision support tool (educational use only)")

# --- INPUT SECTION ---
st.header("Enter Patient Data")

ph = st.number_input("pH", value=7.4)
pco2 = st.number_input("PaCO2 (mmHg)", value=40.0)
hco3 = st.number_input("HCO3 (mEq/L)", value=24.0)
po2 = st.number_input("PaO2 (mmHg)", value=90.0)
st.subheader("🧪 Electrolytes (for Anion Gap)")

na = st.number_input("Na⁺ (mEq/L)", value=140.0)
cl = st.number_input("Cl⁻ (mEq/L)", value=104.0)

st.subheader("Ventilator Settings")

rr = st.number_input("Respiratory Rate (RR)", value=16)
tv = st.number_input("Tidal Volume (ml)", value=500)
fio2 = st.number_input("FiO2", value=0.4)
peep = st.number_input("PEEP", value=5.0)

def full_abg_analysis(ph, pco2, hco3):

    result = {}

    # --- STEP 1: pH ---
    if ph < 7.35:
        result["state"] = "Acidemia"
    elif ph > 7.45:
        result["state"] = "Alkalemia"
    else:
        result["state"] = "Normal / Compensated"

    # --- STEP 2: Primary disorder ---
    if ph < 7.35:
        if pco2 > 45:
            result["primary"] = "Respiratory Acidosis"
        elif hco3 < 22:
            result["primary"] = "Metabolic Acidosis"
        else:
            result["primary"] = "Mixed/Unclear"

    elif ph > 7.45:
        if pco2 < 35:
            result["primary"] = "Respiratory Alkalosis"
        elif hco3 > 26:
            result["primary"] = "Metabolic Alkalosis"
        else:
            result["primary"] = "Mixed/Unclear"
    else:
        result["primary"] = "Compensated Disorder"

    # --- STEP 3: Compensation ---
    compensation = ""

    if result["primary"] == "Metabolic Acidosis":
        expected_pco2 = 1.5 * hco3 + 8
        compensation = f"Expected PaCO2 ≈ {round(expected_pco2,1)} (Winter’s formula)"

        if abs(pco2 - expected_pco2) > 2:
            compensation += " → Mixed disorder likely"

    elif result["primary"] == "Metabolic Alkalosis":
        expected_pco2 = 0.7 * hco3 + 20
        compensation = f"Expected PaCO2 ≈ {round(expected_pco2,1)}"

    elif result["primary"] == "Respiratory Acidosis":
        delta = pco2 - 40
        acute_hco3 = 24 + (delta/10)*1
        chronic_hco3 = 24 + (delta/10)*4

        compensation = (
            f"Expected HCO3: Acute ≈ {round(acute_hco3,1)}, "
            f"Chronic ≈ {round(chronic_hco3,1)}"
        )

        # 🔥 ADD THIS PART
        if acute_hco3 <= hco3 <= chronic_hco3:
            compensation += " → Appropriate compensation (likely chronic/subacute)"

        elif hco3 < acute_hco3:
            compensation += " → Additional metabolic acidosis"

        elif hco3 > chronic_hco3:
            compensation += " → Additional metabolic alkalosis"

    elif result["primary"] == "Respiratory Alkalosis":
        delta = 40 - pco2
        acute_hco3 = 24 - (delta/10)*2
        chronic_hco3 = 24 - (delta/10)*5

        compensation = (
            f"Expected HCO3: Acute ≈ {round(acute_hco3,1)}, "
            f"Chronic ≈ {round(chronic_hco3,1)}"
        )

    result["compensation"] = compensation

    return result

def calculate_anion_gap(na, cl, hco3):

    ag = na - (cl + hco3)

    interpretation = ""

    if ag > 14:
        interpretation = "High Anion Gap → consider DKA, lactic acidosis, toxins"
    elif ag < 8:
        interpretation = "Low Anion Gap → rare (lab error, hypoalbuminemia)"
    else:
        interpretation = "Normal Anion Gap"

    return ag, interpretation

def calculate_delta_ratio(ag, hco3):

    if hco3 >= 24:
        return None, "Not applicable"

    delta = (ag - 12) / (24 - hco3)

    if delta < 1:
        interpretation = "Mixed: High AG + Normal AG metabolic acidosis"
    elif 1 <= delta <= 2:
        interpretation = "Pure high anion gap metabolic acidosis"
    else:
        interpretation = "Mixed: High AG + Metabolic alkalosis"

    return delta, interpretation

def smart_override(pco2, po2, rr, tv, fio2, peep):
    actions = []
    reasons = []

    # --- Ventilation logic (CO2) ---
    if pco2 > 45:
        if rr >= 20 and tv >= 500:
            actions.append("Ventilation already high → consider further RR/TV increase OR assess compliance/dead space")
            reasons.append("High PaCO2 despite adequate settings → possible V/Q mismatch, dead space, or poor compliance")
        else:
            actions.append("Increase ventilation (↑ RR or ↑ TV)")
            reasons.append("High PaCO2 indicates hypoventilation")

    elif pco2 < 35:
        if rr <= 12:
            actions.append("Ventilation already low → evaluate metabolic causes")
            reasons.append("Low PaCO2 with low RR → consider metabolic alkalosis or overcompensation")
        else:
            actions.append("Reduce ventilation (↓ RR or ↓ TV)")
            reasons.append("Low PaCO2 indicates hyperventilation")

    # --- Oxygenation logic (O2) ---
    if po2 < 60:
        if fio2 >= 0.6:
            actions.append("FiO2 already high → consider increasing PEEP")
            reasons.append("Refractory hypoxemia → likely alveolar collapse (need recruitment)")
        else:
            actions.append("Increase FiO2")
            reasons.append("Low PaO2 indicates hypoxemia")

    elif po2 < 80:
        actions.append("Mild hypoxemia → monitor or adjust FiO2/PEEP")
        reasons.append("Borderline oxygenation")

    return actions, reasons
    
# --- SIMPLE LOGIC (use your model later) ---
if st.button("🔍 ANALYZE PATIENT"):

    input_data = [[ph, pco2, hco3, po2, rr, tv, fio2, peep]]

    prediction = model.predict(input_data)[0]

    probs = model.predict_proba(input_data)[0]
    confidence = max(probs)
    
    st.markdown("---")
    st.subheader("🧠 RESULTS")


    # --- MODEL INPUT ---
    input_data = [[ph, pco2, hco3, po2, rr, tv, fio2, peep]]
    prediction = model.predict(input_data)[0]
    override_actions, override_reasons = smart_override(pco2, po2, rr, tv, fio2, peep)

    # --- AI PANEL ---
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("🤖 AI + CLINICAL RECOMMENDATION")

        st.write("### ML Suggestion")
        st.success(prediction)

        st.write("### Clinical Override")

        for action in override_actions:
            st.warning(action)

        st.write("### Reasoning")
        for reason in override_reasons:
            st.info(reason)

    # --- ABG PANEL ---
    with col4:
        st.subheader("🧠 ABG INTERPRETATION ENGINE")

        analysis = full_abg_analysis(ph, pco2, hco3)

        st.write(f"**State:** {analysis['state']}")
        st.write(f"**Primary Disorder:** {analysis['primary']}")

        st.info(analysis["compensation"])

        # --- Clinical reasoning ---
        st.write("### Clinical Reasoning")

        if "Metabolic Acidosis" in analysis["primary"]:
            st.write("Low HCO3 → metabolic cause → apply Winter’s formula")

        elif "Respiratory Acidosis" in analysis["primary"]:
            st.write("High PaCO2 → hypoventilation → check acute vs chronic compensation")

        elif "Respiratory Alkalosis" in analysis["primary"]:
            st.write("Low PaCO2 → hyperventilation (pain/sepsis/PE)")

        elif "Metabolic Alkalosis" in analysis["primary"]:
            st.write("High HCO3 → metabolic alkalosis (vomiting/diuretics)")
        
        st.markdown("---")
        st.subheader("🧮 ANION GAP ANALYSIS")

        ag, ag_text = calculate_anion_gap(na, cl, hco3)

        st.write(f"**Anion Gap:** {round(ag,1)}")
        st.info(ag_text)

        delta, delta_text = calculate_delta_ratio(ag, hco3)

        if delta is not None:
            st.write(f"**Delta Ratio:** {round(delta,2)}")
            st.info(delta_text)


    # --- SEVERITY METER ---
    st.subheader("🚨 Patient Severity")

    def calculate_severity(ph, pco2, po2):
        score = 0

        if ph < 7.25 or ph > 7.55:
            score += 2
        elif ph < 7.35 or ph > 7.45:
            score += 1

        if pco2 > 60 or pco2 < 25:
            score += 2
        elif pco2 > 45 or pco2 < 35:
            score += 1

        if po2 < 60:
            score += 2
        elif po2 < 80:
            score += 1

        if score >= 4:
            return "Severe", 90
        elif score >= 2:
            return "Moderate", 60
        else:
            return "Stable", 30

    severity, progress = calculate_severity(ph, pco2, po2)

    if severity == "Severe":
        st.error("🔴 Severe – Immediate attention required")
    elif severity == "Moderate":
        st.warning("🟡 Moderate – Monitor closely")
    else:
        st.success("🟢 Stable")

    st.progress(progress)

    st.warning("⚠️ Clinical decision support only")
    
def calculate_severity(ph, pco2, po2):
    
    score = 0

    # pH severity
    if ph < 7.25 or ph > 7.55:
        score += 2
    elif ph < 7.35 or ph > 7.45:
        score += 1

    # CO2 severity
    if pco2 > 60 or pco2 < 25:
        score += 2
    elif pco2 > 45 or pco2 < 35:
        score += 1

    # Oxygenation
    if po2 < 60:
        score += 2
    elif po2 < 80:
        score += 1

    # Final classification
    if score >= 4:
        return "Severe", "red"
    elif score >= 2:
        return "Moderate", "orange"
    else:
        return "Stable", "green"
        
st.markdown("---")
st.subheader("🧾 FINAL CLINICAL SUMMARY")

# --- Confidence label ---
if confidence > 0.85:
    conf_label = "High confidence"
elif confidence > 0.6:
    conf_label = "Moderate confidence"
else:
    conf_label = "Low confidence – interpret cautiously"

# --- Main summary box ---
st.success(f"""
**AI Suggestion:** {prediction}  
**Confidence:** {round(confidence*100,1)}% ({conf_label})
""")

# --- Actionable recommendations ---
st.write("### 📌 Recommended Actions")

for action in override_actions:
    st.warning(f"• {action}")

# --- Clinical reasoning ---
st.write("### 🧠 Clinical Interpretation")

for reason in override_reasons:
    st.info(f"• {reason}")

# --- Safety note ---
if confidence < 0.6:
    st.error("⚠️ Low model confidence → possible mixed or complex physiology")

st.warning("⚠️ Clinical decision support only – correlate with full clinical picture")