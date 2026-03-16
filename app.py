import streamlit as st
import google.generativeai as genai
import json
import plotly.graph_objects as go

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


# ====================== PROMPT (same powerful one) ======================
SYSTEM_PROMPT = """
You are an expert insurance claims triage agent for mid-market insurers and financial services firms (like a 51D client).

First detect the language of the claim.
Translate it internally to English for analysis if needed.
Then classify into exactly one of:
- APPROVE
- FLAG_FOR_REVIEW
- DENY

Return ONLY a valid JSON object (no extra text, no markdown, no explanations):
{
  "detected_language": "French",
  "category": "FLAG_FOR_REVIEW",
  "reason": "Short 1-2 sentence explanation in the ORIGINAL language of the claim",
  "risk_score": 7,          # 1-10
  "next_steps": "Short actionable next step in ORIGINAL language"
} 

Be conservative — most real claims should be FLAG_FOR_REVIEW.
Output ONLY the JSON object.
"""
# Despite adding "Output ONLY the JSON object" to the prompt, Gemini sometimes adds ```json markdown formatting around the output, so we handle that in the model specification, and in the code below, too.

# ====================== MAIN APP ======================
st.title("🔍 51D Demo: Multilingual Insurance Claims Triage Agent")
st.markdown("**Built in <7 days** | Shows X% efficiency gain for FS/Insurance clients")

claim_text = st.text_area("Paste any claim description (English, French, Spanish, Italian, etc.)", height=150)

if st.button("🚀 Triage Claim", type="primary"):
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