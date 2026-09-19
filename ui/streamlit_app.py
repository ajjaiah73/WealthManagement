import streamlit as st, requests
st.set_page_config(page_title="Financial Advisory Dashboard",layout="wide")
st.title("Superannuation Advisory and Regulatory Compliance Verification Dashboard")
st.caption("Customer Information.")
with st.form("client"):
    c1,c2,c3=st.columns(3)
    client_id=c1.text_input("Client Name","Ajjaiah M E")
    age=c2.number_input("Age",23,45,30)
    risk=c3.selectbox("Risk tolerance",["conservative","moderate","aggressive"],index=1)
    income=c1.number_input("Annual income",0.0,value=1800000.0)
    assets=c2.number_input("Liquid assets",0.0,value=500000.0)
    horizon=c3.number_input("Horizon (years)",1,50,10)
    max_fee=c1.number_input("Maximum product fee (%)",0.0,10.0,1.5)
    goal=st.text_input("Goal","Build a diversified long-term Supperannuation or Retirement Pension Products Summary")
    question=st.text_area("Fact-find question","What are best superannuation products along with the Regulatory Compliance should I consider?")
    go=st.form_submit_button("Generate advisory Summary")
if go:
    payload={"client":{"client_id":client_id,"age":age,"annual_income":income,"liquid_assets":assets,"risk_tolerance":risk,"investment_horizon_years":horizon,"max_fee_pct":max_fee,"restricted_products":[]},"goal":goal,"question":question}
    try:
        r=requests.post("http://localhost:8000/advice",json=payload,timeout=180); r.raise_for_status(); data=r.json()
        st.subheader("Statement of Advice"); st.write(data["statement_of_advice"])
        st.metric("Compliance", "PASS" if data["compliant"] else "REVIEW")
        st.json(data["allocation"])
        st.subheader("Recommendations"); st.dataframe(data["recommendations"],use_container_width=True)
        st.subheader("Compliance report"); st.dataframe(data["compliance_findings"],use_container_width=True)
        st.subheader("Retrieved evidence");
        for x in data["citations"]: st.markdown(f"**{x['id']}**: {x['text']}")
        st.subheader("Audit notes"); st.write(data["audit_notes"]); st.code(data["audit_id"])
    except Exception as e: st.error(str(e))
