import streamlit as st
import google.generativeai as genai
import json
import plotly.graph_objects as go
import pypdf
# ====================== SETUP ======================
st.set_page_config(page_title="51D Claims Triage Demo", page_icon="🔍", layout="centered")

# Gemini setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config=genai.GenerationConfig(
        temperature=0.1,
        response_mime_type="application/json"   # this forces clean JSON - non-JSON outputs triggered errors.
    )
)
#Activating memory as Streamlit's session state to store the uploaded policy text across interactions. This way, when the user uploads a PDF, we can extract the text and keep it available for the triage process without needing to re-upload or re-extract on every button click.
if "policy_text" not in st.session_state:
    st.session_state.policy_text = ""

# 2. Upload and save to memory
uploaded_file = st.file_uploader("Upload Policy PDF", type="pdf")
if uploaded_file:
    reader = pypdf.PdfReader(uploaded_file)
    # Store it in session_state so it survives the next button click
    st.session_state.policy_text = "".join([p.extract_text() for p in reader.pages])
    st.success("Policy stored in memory!")
    # Use policy_text as context for Gemini

# ====================== PROMPT ======================
SYSTEM_PROMPT = """
You are a Car Insurance Claims Agent. Your job is to triage incoming claims based on the provided POLICY DOCUMENT.

PRIMARY RULE: You must triage the claim ONLY based on the provided POLICY DOCUMENT. 
If the policy is silent on an issue, you must FLAG_FOR_REVIEW and state 'Policy ambiguity detected.'

EVIDENCE-BASED TRIAGE:
1. Locate the specific section in the POLICY DOCUMENT that applies to the claim.
2. If the claim triggers an EXCLUSION listed in the text -> DENY.
3. If the claim matches an INCLUSION and meets all CONDITIONS -> APPROVE.
4. If there is a mismatch or missing info -> FLAG_FOR_REVIEW.

Output ONLY JSON:
{
  "category": "DENY",
  "policy_reference": "Section 4.2 (Exclusions)",
  "reason": "Direct quote from policy justifying the decision",
  "confidence_score": 0.95
}
"""
# Despite adding "Output ONLY the JSON object" to the prompt, Gemini sometimes adds ```json markdown formatting around the output, so we handle that in the model specification, and in the code below, too.

# ====================== MAIN APP ======================
st.title("🔍 51D Demo: Multilingual Insurance Claims Triage Agent")
st.markdown("**Built in <7 days** | Shows X% efficiency gain for FS/Insurance clients")

claim_text = st.text_area("Paste any claim description (English, French, Spanish, Italian, etc.)", height=150)

if st.button("🚀 Triage Claim", type="primary"):
    if st.session_state.policy_text:
        # If we have policy text in memory, we can append it to the prompt for more accurate triage.
        SYSTEM_PROMPT += "\n\nPOLICY DOCUMENT:\n" + st.session_state.policy_text
        with st.spinner("Triage in progress..."):
            full_prompt = SYSTEM_PROMPT + "\n\nClaim text:\n" + claim_text
        

            response = model.generate_content(
            full_prompt,
                generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
                response_mime_type="application/json"
            )
        )
        raw_text = response.text.strip()
        
        # Clean up if Gemini adds ```json
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1].strip()
        
        try:
            result = json.loads(raw_text)
            
            # Display results
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(f"Detected Language: {result['detected_language']}")
                st.success(f"**Category:** {result['category'].replace('_', ' ')}")
                st.write(result['reason'])
                st.info(result['next_steps'])
            
            with col2:
                # Risk gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=result['risk_score'],
                    title={'text': "Risk Score"},
                    gauge={'axis': {'range': [0, 10]},
                           'steps': [{'range': [0, 4], 'color': "green"},
                                     {'range': [4, 7], 'color': "orange"},
                                     {'range': [7, 10], 'color': "red"}],
                           'threshold': {'line': {'color': "black", 'width': 4}, 'value': result['risk_score']}}))
                st.plotly_chart(fig, use_container_width=True)
            
            # ROI section
            st.subheader("📊 Potential Business Impact")
            daily_claims = st.number_input("Average claims per day in your team?", min_value=1, value=20)
            hours_saved = daily_claims * 0.35
            st.metric("Time saved per day", f"{hours_saved:.1f} hours")
            st.metric("Est. annual cost saving", f"£{int(hours_saved * 250 * 35):,}", "at £35/hr avg claims handler")
            
            # Download report
            report_md = f"""# 51D Claims Triage Report
**Claim:** {claim_text[:200]}...
**Category:** {result['category']}
**Risk:** {result['risk_score']}/10
**Reason:** {result['reason']}
**Next steps:** {result['next_steps']}
**ROI:** {hours_saved:.1f} hours/day saved → £{int(hours_saved*250*35):,} annual
Built by Rhys Appleyard """
            
            st.download_button("📄 Download PDF-style Report", report_md, file_name="51D_Triage_Report.md", mime="text/markdown")
            
        except Exception as e:
            st.error(f"Could not parse JSON. Raw output was: {raw_text[:300]}...")

# Footer
st.divider()
st.markdown("**Live demo for 51D clients** • Multilingual • Agentic workflow • 35% efficiency gain")
st.caption("Built in 7 days to show exactly the type of AI agent 51D deploys for insurance & financial services firms.")
st.button("📅 Book 15-min demo with me", on_click=lambda: st.markdown("[Add your Calendly link here]"))