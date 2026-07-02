import streamlit as st
import pandas as pd
import numpy as np
import datetime
from io import BytesIO

# 1. Page Config for Modern & Premium Look
st.set_page_config(page_title="Romsons Logistics Dashboard", page_icon="🚚", layout="wide")

# Custom CSS matching the clean enterprise requirements
st.markdown("""
    <style>
    .main-title { font-size:28px; font-weight:bold; color:#1E3A8A; margin-bottom:5px; }
    .sub-title { font-size:14px; color:#555555; margin-bottom:20px; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .metric-val { font-size: 26px; font-weight: bold; color: #1E3A8A; }
    .metric-lbl { font-size: 12px; color: #64748B; text-transform: uppercase; margin-top: 5px; font-weight: 500; }
    div[data-testid="stExpander"] { border: 1px solid #E2E8F0; border-radius: 8px; background-color: white; }
    </style>
""", unsafe_allow_html=True)

# 2. Warehouse All India Node Credentials Setup
WAREHOUSES = {
    "RPPL - DEL": "delhi@123",
    "RPPL - BLR": "bangalore@123",
    "RPPL - KOL": "kolkata@123",
    "RPPL - MUM": "mumbai@123",
    "Admin": "admin@romsons"
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None

# --- SECURED LOGIN INTERFACE ---
if not st.session_state['logged_in']:
    st.markdown("<div class='main-title'>🚚 Romsons India | Logistics Portal</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Please choose your node location to proceed.</div>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        wh_selection = st.selectbox("Select Your Warehouse Node / Role", list(WAREHOUSES.keys()))
        password = st.text_input("Enter Node Password", type="password")
        submit_button = st.form_submit_button("Sign In")
        
        if submit_button:
            if WAREHOUSES[wh_selection] == password:
                st.session_state['logged_in'] = True
                st.session_state['warehouse'] = wh_selection
                st.rerun()
            else:
                st.error("❌ Invalid Node Password! Please enter valid credentials.")
    st.stop()

# --- SIDEBAR LOGOUT OPTION ---
st.sidebar.markdown(f"**🟢 Active Node:** `{st.session_state['warehouse']}`")
if st.sidebar.button("Logout Node"):
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None
    st.rerun()

# --- DASHBOARD MAIN AREA ---
st.markdown(f"<div class='main-title'>📦 Dispatch Reconciliation Dashboard — {st.session_state['warehouse']}</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Vinculum Base Track & Cross-Portal Status Reconciler</div>", unsafe_allow_html=True)

# Intelligent dynamic column finding helper function
def find_col_by_name(df, possible_names):
    for col in df.columns:
        if str(col).strip().lower() in [name.lower() for name in possible_names]:
            return col
    return None

# Sidebar File Dropers
st.sidebar.header("📁 Data Ingestion Segment")
vinculum_file = st.sidebar.file_uploader("1. Upload Vinculum Base Report (xlsx/csv)", type=["xlsx", "csv"])
portal_files = st.sidebar.file_uploader("2. Upload Courier Portals (Amazon, DTDC, Delhivery, XB)", type=["xlsx", "csv"], accept_multiple_files=True)

if vinculum_file:
    # Load Vinculum Base Data File
    if vinculum_file.name.endswith('.csv'):
        df_vinc = pd.read_csv(vinculum_file)
    else:
        # Handles spreadsheet logs
        df_vinc = pd.read_excel(vinculum_file)
        
    # Auto Filter data rows based on Node location login
    vinc_wh_col = find_col_by_name(df_vinc, ['SourceWH', 'Warehouse', 'WH', 'Warehouse Name'])
    if vinc_wh_col and st.session_state['warehouse'] != "Admin":
        df_vinc = df_vinc[df_vinc[vinc_wh_col] == st.session_state['warehouse']]
    
    # Pre-map critical tracking columns from target base sheet
    vinc_awb_col = find_col_by_name(df_vinc, ['Tracking No', 'AWB Number', 'AWB No', 'TrackingNo'])
    vinc_ship_date = find_col_by_name(df_vinc, ['Ship Date', 'Shipped Date', 'Actual Time of Shipment'])
    vinc_del_date = find_col_by_name(df_vinc, ['Delivery Date', 'Delivered Date'])
    vinc_status_col = find_col_by_name(df_vinc, ['Order Status', 'Delivery Status', 'Status'])
    vinc_courier_col = find_col_by_name(df_vinc, ['Transporter', 'Courier', 'Courier Partner'])

    if not vinc_awb_col:
        st.error("❌ Error: 'Tracking No' or 'AWB Number' columns not detected in Vinculum Base Sheet!")
        st.stop()

    # Dynamic Cross-Reconciliation Framework
    portal_status_dict = {}
    if portal_files:
        for p_file in portal_files:
            df_p = pd.read_csv(p_file) if p_file.name.endswith('.csv') else pd.read_excel(p_file)
            
            # Smart look-up logic irrespective of column sequence shifting
            awb_col = find_col_by_name(df_p, ['TrackingId', 'Waybill', 'AWB No', 'AWB Number', 'Tracking Number'])
            status_col = find_col_by_name(df_p, ['Order status', 'Current Status', 'Status', 'Delivery Status'])
            
            if awb_col and status_col:
                for _, row in df_p.dropna(subset=[awb_col]).iterrows():
                    portal_status_dict[str(row[awb_col]).strip()] = str(row[status_col]).strip()

    # Apply Cleaned Mapping
    df_vinc['Clean_AWB'] = df_vinc[vinc_awb_col].astype(str).str.strip()
    if portal_status_dict:
        df_vinc['Reconciled_Status'] = df_vinc['Clean_AWB'].map(portal_status_dict).fillna(df_vinc[vinc_status_col] if vinc_status_col else "In-Transit")
    else:
        df_vinc['Reconciled_Status'] = df_vinc[vinc_status_col] if vinc_status_col else "In-Transit"

    # Datetime parse cleaning & calculations 
    if vinc_ship_date: df_vinc['Ship_Clean'] = pd.to_datetime(df_vinc[vinc_ship_date], errors='coerce')
    if vinc_del_date: df_vinc['Del_Clean'] = pd.to_datetime(df_vinc[vinc_del_date], errors='coerce')
    
    current_date = pd.to_datetime(datetime.date.today())
    
    def calculate_tat_aging(row):
        status = str(row['Reconciled_Status']).lower()
        if 'deliver' in status:
            if pd.notnull(row.get('Ship_Clean')) and pd.notnull(row.get('Del_Clean')):
                return int((row['Del_Clean'] - row['Ship_Clean']).days)
        else:
            if pd.notnull(row.get('Ship_Clean')):
                return int((current_date - row['Ship_Clean']).days)
        return np.nan

    df_vinc['Days_TAT_or_Aging'] = df_vinc.apply(calculate_tat_aging, axis=1)

    # Segregating dataframes for distinct downloads and views
    df_delivered = df_vinc[df_vinc['Reconciled_Status'].astype(str).str.lower().str.contains('deliver')]
    df_intransit = df_vinc[~df_vinc['Reconciled_Status'].astype(str).str.lower().str.contains('deliver')]

    # --- MODERN EXECUTIVE SUMMARY VIEW METRICS BAR ---
    st.markdown("### 📊 Consolidated Summary Status")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_vinc)}</div><div class='metric-lbl'>Total Dispatches</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#16A34A;'>{len(df_delivered)}</div><div class='metric-lbl'>Delivered Shipments</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EA580C;'>{len(df_intransit)}</div><div class='metric-lbl'>In-Transit Tracking</div></div>", unsafe_allow_html=True)
    
    avg_t = df_delivered['Days_TAT_or_Aging'].mean()
    avg_t_str = f"{avg_t:.1f} Days" if pd.notnull(avg_t) else "N/A"
    c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#2563EB;'>{avg_t_str}</div><div class='metric-lbl'>Avg Delivery TAT</div></div>", unsafe_allow_html=True)

    # --- WHATSAPP SUMMARY GENERATION LOGIC ---
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📲 Generate & Copy WhatsApp Daily Report Summary"):
        courier_lbl = vinc_courier_col if vinc_courier_col else 'Transporter'
        
        # Aggregate logic
        del_grp = df_delivered.groupby(courier_lbl).size() if courier_lbl in df_delivered.columns else {}
        int_grp = df_intransit.groupby(courier_lbl).size() if courier_lbl in df_intransit.columns else {}
        
        whatsapp_msg = f"📦 *ROMSONS LOGISTICS DAILY REPORT* 📦\n"
        whatsapp_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        whatsapp_msg += f"🏢 *Warehouse:* {st.session_state['warehouse']}\n"
        whatsapp_msg += f"📅 *Date:* {datetime.date.today().strftime('%d-%m-%Y')}\n"
        whatsapp_msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        whatsapp_msg += f"✅ *DELIVERED REPORT (Last 30 Days)*\n"
        for cr, count in del_grp.items():
            whatsapp_msg += f"• {cr}: *{count} Orders*\n"
        whatsapp_msg += f"🔹 *Total Delivered:* **{len(df_delivered)} Orders** (Avg TAT: {avg_t_str})\n\n"
        
        whatsapp_msg += f"⏳ *PENDING DELIVERIES (In-Transit)*\n"
        for cr, count in int_grp.items():
            whatsapp_msg += f"• {cr}: *{count} Orders*\n"
        
        avg_age = df_intransit['Days_TAT_or_Aging'].mean()
        avg_age_str = f"{avg_age:.1f} Days" if pd.notnull(avg_age) else "N/A"
        whatsapp_msg += f"🔸 *Total Pending:* **{len(df_intransit)} Orders** (Avg Aging: {avg_age_str})\n"
        whatsapp_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        whatsapp_msg += f"🚀 *Generated via Romsons Automation Engine*"

        st.text_area("WhatsApp Text Preview:", value=whatsapp_msg, height=220)
        st.copy_to_clipboard(whatsapp_msg, before_text="📋 Copy To Clipboard", after_text="✅ Text Copied! Now Paste in WhatsApp")

    # Excel Download Helper Function
    def get_excel_bytes(dataframe):
        output_buffer = BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False)
        return output_buffer.getvalue()

    # --- RECONCILED TABS VIEW AND DOWNLOAD SECTION ---
    st.markdown("<br>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["📋 Master Consolidated View", "✅ Delivered Performance Sheet", "⏳ Active In-Transit Tracking"])
    
    with t1:
        st.dataframe(df_vinc, use_container_width=True)
    with t2:
        st.dataframe(df_delivered, use_container_width=True)
        st.download_button("📥 Download Delivered Report (.xlsx)", data=get_excel_bytes(df_delivered), file_name=f"Delivered_Report_{st.session_state['warehouse']}.xlsx")
    with t3:
        st.dataframe(df_intransit, use_container_width=True)
        st.download_button("📥 Download In-Transit Tracking Sheet (.xlsx)", data=get_excel_bytes(df_intransit), file_name=f"In_Transit_Report_{st.session_state['warehouse']}.xlsx")
else:
    st.info("💡 Dashboard Active karne ke liye kripya left sidebar se 'Vinculum Base Sheet' upload karein.")

