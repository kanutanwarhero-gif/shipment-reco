import streamlit as st
import pandas as pd
import numpy as np
import datetime
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Romsons Logistics Dashboard", page_icon="🚚", layout="wide")

# Custom CSS for Modern Executive Look
st.markdown("""
    <style>
    .main-title { font-size:28px; font-weight:bold; color:#1E3A8A; margin-bottom:5px; }
    .sub-title { font-size:14px; color:#555555; margin-bottom:20px; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .metric-val { font-size: 24px; font-weight: bold; color: #1E3A8A; }
    .metric-lbl { font-size: 12px; color: #64748B; text-transform: uppercase; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# Warehouse Access Setup
WAREHOUSES = {
    "RPPL - DEL": "delhi@123",
    "RPPL - BLR": "bangalore@123",
    "RPPL - KOL": "kolkata@123",
    "Admin": "admin@romsons"
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None

# --- LOGIN SCREEN ---
if not st.session_state['logged_in']:
    st.markdown("<div class='main-title'>🚚 Logistics & Dispatch Portal</div>", unsafe_allow_html=True)
    with st.form("login_form"):
        wh_selection = st.selectbox("Select Your Warehouse / Role", list(WAREHOUSES.keys()))
        
        # 🟢 FIX: Changed st.password_input to st.text_input with type="password"
        password = st.text_input("Enter Password", type="password")
        
        # 🟢 FIX: Submit button properly positioned inside the form context
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if WAREHOUSES[wh_selection] == password:
                st.session_state['logged_in'] = True
                st.session_state['warehouse'] = wh_selection
                st.rerun()
            else:
                st.error("❌ Invalid Password!")
    st.stop()

# Sidebar Logout
st.sidebar.markdown(f"**Current Node:** `{st.session_state['warehouse']}`")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None
    st.rerun()

st.markdown(f"<div class='main-title'>📦 Logistics Automation — {st.session_state['warehouse']}</div>", unsafe_allow_html=True)

# Helper function to dynamically find columns (Dynamic Matching Requirement)
def find_col_by_name(df, possible_names):
    for col in df.columns:
        if str(col).strip().lower() in [name.lower() for name in possible_names]:
            return col
    return None

# Sidebar File Uploaders
st.sidebar.header("📁 Upload Section")
vinculum_file = st.sidebar.file_uploader("1. Vinculum Base Sheet", type=["xlsx", "csv"])
portal_files = st.sidebar.file_uploader("2. Courier Portal Sheets (Multiple)", type=["xlsx", "csv"], accept_multiple_files=True)

if vinculum_file:
    df_vinc = pd.read_csv(vinculum_file) if vinculum_file.name.endswith('.csv') else pd.read_excel(vinculum_file)
        
    # Warehouse wise data filtering
    vinc_wh_col = find_col_by_name(df_vinc, ['SourceWH', 'Warehouse', 'WH'])
    if vinc_wh_col and st.session_state['warehouse'] != "Admin":
        df_vinc = df_vinc[df_vinc[vinc_wh_col] == st.session_state['warehouse']]
    
    vinc_awb_col = find_col_by_name(df_vinc, ['Tracking No', 'AWB Number', 'AWB No'])
    vinc_ship_date = find_col_by_name(df_vinc, ['Ship Date', 'Shipped Date'])
    vinc_del_date = find_col_by_name(df_vinc, ['Delivery Date', 'Delivered Date'])
    vinc_status_col = find_col_by_name(df_vinc, ['Delivery Status', 'Status'])

    if not vinc_awb_col:
        st.error("Vinculum sheet mein 'Tracking No' ya 'AWB Number' nahi mila!")
        st.stop()

    # Reconciling Portal Sheets
    portal_status_dict = {}
    if portal_files:
        for p_file in portal_files:
            df_p = pd.read_csv(p_file) if p_file.name.endswith('.csv') else pd.read_excel(p_file)
            awb_col = find_col_by_name(df_p, ['TrackingId', 'Waybill', 'AWB No', 'AWB Number'])
            status_col = find_col_by_name(df_p, ['Order status', 'Current Status', 'Status'])
            if awb_col and status_col:
                for _, row in df_p.dropna(subset=[awb_col]).iterrows():
                    portal_status_dict[str(row[awb_col]).strip()] = str(row[status_col]).strip()

    df_vinc['Clean_AWB'] = df_vinc[vinc_awb_col].astype(str).str.strip()
    if portal_status_dict:
        df_vinc['Reconciled_Status'] = df_vinc['Clean_AWB'].map(portal_status_dict).fillna(df_vinc[vinc_status_col] if vinc_status_col else "Unknown")
    else:
        df_vinc['Reconciled_Status'] = df_vinc[vinc_status_col] if vinc_status_col else "Unknown"

    # Date TAT and Aging Calculations
    if vinc_ship_date: df_vinc['Ship_Clean'] = pd.to_datetime(df_vinc[vinc_ship_date], errors='coerce')
    if vinc_del_date: df_vinc['Del_Clean'] = pd.to_datetime(df_vinc[vinc_del_date], errors='coerce')
    
    today = pd.to_datetime(datetime.date.today())
    
    def calc_tat(row):
        status = str(row['Reconciled_Status']).lower()
        if 'deliver' in status:
            if pd.notnull(row.get('Ship_Clean')) and pd.notnull(row.get('Del_Clean')):
                return (row['Del_Clean'] - row['Ship_Clean']).days
        else:
            if pd.notnull(row.get('Ship_Clean')):
                return (today - row['Ship_Clean']).days
        return np.nan

    df_vinc['TAT_Days'] = df_vinc.apply(calc_tat, axis=1)
    df_delivered = df_vinc[df_vinc['Reconciled_Status'].astype(str).str.lower().str.contains('deliver')]
    df_intransit = df_vinc[~df_vinc['Reconciled_Status'].astype(str).str.lower().str.contains('deliver')]

    # Executive Modern Summary Cards
    st.markdown("### 📊 Live Executive Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_vinc)}</div><div class='metric-lbl'>Total Dispatches</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#16A34A;'>{len(df_delivered)}</div><div class='metric-lbl'>Delivered Count</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EA580C;'>{len(df_intransit)}</div><div class='metric-lbl'>In-Transit Pending</div></div>", unsafe_allow_html=True)
    avg_t = df_delivered['TAT_Days'].mean()
    c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#2563EB;'>{f'{avg_t:.1f} Days' if pd.notnull(avg_t) else 'N/A'}</div><div class='metric-lbl'>Avg Delivery TAT</div></div>", unsafe_allow_html=True)

    # Excel Download Helper
    def convert_df(df):
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            df.to_excel(w, index=False)
        return out.getvalue()

    # Views and Download Tabs
    st.markdown("<br>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["📋 Reconciled Database", "✅ Delivered Shipments", "⏳ Active In-Transit"])
    
    with t1:
        st.dataframe(df_vinc, use_container_width=True)
    with t2:
        st.dataframe(df_delivered, use_container_width=True)
        st.download_button("📥 Download Delivered Report (.xlsx)", data=convert_df(df_delivered), file_name="Delivered_Report.xlsx")
    with t3:
        st.dataframe(df_intransit, use_container_width=True)
        st.download_button("📥 Download In-Transit Report (.xlsx)", data=convert_df(df_intransit), file_name="In_Transit_Report.xlsx")
else:
    st.info("💡 Please upload the Vinculum base sheet from the sidebar to activate the system dashboards.")

