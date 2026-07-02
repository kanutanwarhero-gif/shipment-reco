import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
from io import BytesIO

# 1. Page Config for Enterprise Dashboard
st.set_page_config(page_title="Romsons Enterprise Logistics Portal", page_icon="🚚", layout="wide")

# Custom UI Styles
st.markdown("""
    <style>
    .main-title { font-size:28px; font-weight:bold; color:#1E3A8A; margin-bottom:5px; }
    .sub-title { font-size:14px; color:#555555; margin-bottom:20px; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .metric-val { font-size: 26px; font-weight: bold; color: #1E3A8A; }
    .metric-lbl { font-size: 12px; color: #64748B; text-transform: uppercase; margin-top: 5px; font-weight: 500; }
    .banner-update { background-color: #EFF6FF; border-left: 5px solid #2563EB; padding: 10px; border-radius: 4px; color: #1E40AF; font-weight: 500; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# 2. Centralized Global Memory Simulation using @st.cache_resource
# Yeh server par ek permanent storage banata hai jahan Admin ka data aur logs safe rehte hain.
@st.cache_resource
def get_global_storage():
    return {
        "portal_status_dict": {},        # Master Courier Database
        "last_updated": "N/A",           # Timestamp Banner
        "admin_uploading": False,        # Live Lock Flag for Popup
        "active_users": {},              # Online Tracker
        "activity_logs": []              # Audit Trail
    }

global_store = get_global_storage()

# 3. User Authorization & Credentials
WAREHOUSES = {
    "RPPL - DEL": "delhi@123",
    "RPPL - BLR": "bangalore@123",
    "RPPL - KOL": "kolkata@123",
    "RPPL - PUN": "mumbai@123",
    "Admin": "admin@romsons"
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None

# --- SECURED LOGIN SCREEN ---
if not st.session_state['logged_in']:
    st.markdown("<div class='main-title'>🚚 Romsons India | Central Logistics Portal</div>", unsafe_allow_html=True)
    with st.form("login_form"):
        wh_selection = st.selectbox("Select Your Warehouse Node / Role", list(WAREHOUSES.keys()))
        password = st.text_input("Enter Node Password", type="password")
        if st.form_submit_button("Sign In"):
            if WAREHOUSES[wh_selection] == password:
                st.session_state['logged_in'] = True
                st.session_state['warehouse'] = wh_selection
                
                # Log login activity
                timestamp = datetime.datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
                global_store["activity_logs"].append(f"🟢 [{timestamp}] {wh_selection} logged in successfully.")
                st.rerun()
            else:
                st.error("❌ Invalid Node Password!")
    st.stop()

# Track Active Session (Online Status)
global_store["active_users"][st.session_state['warehouse']] = time.time()

# Clean outdated active users (idle for more than 5 mins)
current_time_epoch = time.time()
inactive_users = [u for u, t in global_store["active_users"].items() if current_time_epoch - t > 300]
for u in inactive_users:
    del global_store["active_users"][u]

# --- SIDEBAR LOGOUT OPTION ---
st.sidebar.markdown(f"**🟢 Active Node:** `{st.session_state['warehouse']}`")
if st.sidebar.button("Logout Node"):
    timestamp = datetime.datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
    global_store["activity_logs"].append(f"🔴 [{timestamp}] {st.session_state['warehouse']} logged out.")
    if st.session_state['warehouse'] in global_store["active_users"]:
        del global_store["active_users"][st.session_state['warehouse']]
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None
    st.rerun()

# 🛑 REQUIREMENT 3: Real-time Blocking Popup if Admin is uploading data
if global_store["admin_uploading"] and st.session_state['warehouse'] != "Admin":
    st.warning("⚠️ **Admin is uploading the courier master data... Please wait.**")
    st.info("🔄 Yeh page automatic refresh ho jayega jaise hi Admin ka upload complete hoga.")
    time.sleep(5)
    st.rerun()

# --- MAIN DASHBOARD INTERFACE ---
st.markdown(f"<div class='main-title'>📦 Dispatch Reconciliation Dashboard — {st.session_state['warehouse']}</div>", unsafe_allow_html=True)

# 🛑 REQUIREMENT 4: Courier Partner Last Updated Timestamp Banner (Visible to All)
st.markdown(f"<div class='banner-update'>🕒 Courier Portals Last Updated: {global_store['last_updated']}</div>", unsafe_allow_html=True)

# Helper Function for Dynamic Column Identification
def find_col_by_name(df, possible_names):
    for col in df.columns:
        if str(col).strip().lower() in [name.lower() for name in possible_names]:
            return col
    return None

# Sidebar Setup based on Roles
st.sidebar.header("📁 Data Ingestion Segment")

# Initialize File Upload Variables
vinculum_file = None
admin_portal_files = None

# 🛑 REQUIREMENT 1 & 2: Role Wise Access Division
if st.session_state['warehouse'] == "Admin":
    st.sidebar.subheader("🔒 Admin Controls Only")
    admin_portal_files = st.sidebar.file_uploader("Upload Courier Portals (Multiple Files)", type=["xlsx", "csv"], accept_multiple_files=True)
    
    if st.sidebar.button("🚀 Process & Save Master Courier Data"):
        if admin_portal_files:
            global_store["admin_uploading"] = True  # Activate Lock Popup
            
            temp_dict = {}
            for p_file in admin_portal_files:
                df_p = pd.read_csv(p_file) if p_file.name.endswith('.csv') else pd.read_excel(p_file)
                awb_col = find_col_by_name(df_p, ['trackingid', 'waybill', 'awb no', 'awb number', 'tracking number'])
                status_col = find_col_by_name(df_p, ['order status', 'current status', 'status', 'delivery status'])
                
                if awb_col and status_col:
                    for key, val in zip(df_p[awb_col].astype(str).str.strip(), df_p[status_col].astype(str).str.strip()):
                        if key != 'nan':
                            temp_dict[key] = val
            
            # Save to global memory
            global_store["portal_status_dict"] = temp_dict
            global_store["last_updated"] = datetime.datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
            global_store["admin_uploading"] = False  # Deactivate Lock Popup
            
            # Log Admin activity
            global_store["activity_logs"].append(f"⚡ [{global_store['last_updated']}] Admin uploaded fresh master courier data ({len(temp_dict)} AWBs processed).")
            st.success("✅ Master Courier Database updated successfully!")
            st.rerun()
        else:
            st.sidebar.error("Kripya pehle files select karein!")
else:
    # For normal warehouses, show Vinculum upload option
    vinculum_file = st.sidebar.file_uploader("Upload Local Vinculum Base Report", type=["xlsx", "csv"])

# --- PROCESSING LOGIC FOR WAREHOUSES (RECONCILIATION) ---
if st.session_state['warehouse'] != "Admin":
    if vinculum_file:
        # Check if Admin has uploaded data yet
        if not global_store["portal_status_dict"]:
            st.error("📥 Admin ne abhi tak master courier portal data upload nahi kiya hai. Kripya Admin ke data upload karne ka wait karein.")
            st.stop()
            
        # Fast read logic
        df_vinc = pd.read_csv(vinculum_file) if vinculum_file.name.endswith('.csv') else pd.read_excel(vinculum_file)
        
        # 🛑 REQUIREMENT: M07 Order ID Filter
        vinc_order_id_col = find_col_by_name(df_vinc, ['Order No', 'Order ID', 'External Order No'])
        if vinc_order_id_col:
            df_vinc[vinc_order_id_col] = df_vinc[vinc_order_id_col].astype(str).str.strip()
            df_vinc = df_vinc[df_vinc[vinc_order_id_col].str.startswith('M07', na=False)]
        else:
            st.error("❌ Error: Vinculum sheet mein 'Order No' ya 'Order ID' nahi mila!")
            st.stop()
            
        # Auto Filter based on login node
        vinc_wh_col = find_col_by_name(df_vinc, ['SourceWH', 'Warehouse', 'WH'])
        if vinc_wh_col:
            df_vinc = df_vinc[df_vinc[vinc_wh_col] == st.session_state['warehouse']]
            
        vinc_awb_col = find_col_by_name(df_vinc, ['Tracking No', 'AWB Number', 'AWB No'])
        vinc_ship_date = find_col_by_name(df_vinc, ['Ship Date', 'Shipped Date', 'Actual Time of Shipment'])
        vinc_del_date = find_col_by_name(df_vinc, ['Delivery Date', 'Delivered Date'])
        
        if not vinc_awb_col:
            st.error("❌ Error: AWB/Tracking Column missing!")
            st.stop()
            
        # 🟢 Match directly with Admin's Master Dictionary Cached on Server
        df_vinc['Clean_AWB'] = df_vinc[vinc_awb_col].astype(str).str.strip()
        df_vinc['Reconciled_Status'] = df_vinc['Clean_AWB'].map(global_store["portal_status_dict"]).fillna("In-Transit")
        
        # Calculations 
        if vinc_ship_date: df_vinc['Ship_Clean'] = pd.to_datetime(df_vinc[vinc_ship_date], errors='coerce')
        if vinc_del_date: df_vinc['Del_Clean'] = pd.to_datetime(df_vinc[vinc_del_date], errors='coerce')
        
        current_date = pd.to_datetime(datetime.date.today())
        is_delivered = df_vinc['Reconciled_Status'].astype(str).str.lower().str.contains('deliver')
        
        df_vinc['Days_TAT_or_Aging'] = np.where(
            is_delivered,
            (df_vinc['Del_Clean'] - df_vinc['Ship_Clean']).dt.days,
            (current_date - df_vinc['Ship_Clean']).dt.days
        )
        
        df_delivered = df_vinc[is_delivered]
        df_intransit = df_vinc[~is_delivered]
        
        # Display Metrics Cards
        st.markdown("### 📊 Consolidated Summary Status")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_vinc)}</div><div class='metric-lbl'>Total Dispatches (M07)</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#16A34A;'>{len(df_delivered)}</div><div class='metric-lbl'>Delivered Shipments</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EA580C;'>{len(df_intransit)}</div><div class='metric-lbl'>In-Transit Tracking</div></div>", unsafe_allow_html=True)
        avg_t = df_delivered['Days_TAT_or_Aging'].mean()
        c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#2563EB;'>{f'{avg_t:.1f} Days' if pd.notnull(avg_t) else 'N/A'}</div><div class='metric-lbl'>Avg Delivery TAT</div></div>", unsafe_allow_html=True)
        
        # Log warehouse activity
        if f"{st.session_state['warehouse']}_uploaded" not in st.session_state:
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
            global_store["activity_logs"].append(f"📝 [{timestamp}] {st.session_state['warehouse']} uploaded Vinculum file ({len(df_vinc)} filtered rows).")
            st.session_state[f"{st.session_state['warehouse']}_uploaded"] = True

        # Downloads Excel Sheets
        def get_excel_bytes(dataframe):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w:
                dataframe.to_excel(w, index=False)
            return buf.getvalue()
            
        st.markdown("<br>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["📋 Reconciled Database View", "✅ Delivered Performance Sheet", "⏳ Active In-Transit Tracking"])
        with t1: st.dataframe(df_vinc, use_container_width=True)
        with t2:
            st.dataframe(df_delivered, use_container_width=True)
            st.download_button("📥 Download Delivered Report (.xlsx)", data=get_excel_bytes(df_delivered), file_name="Delivered_M07_Report.xlsx")
        with t3:
            st.dataframe(df_intransit, use_container_width=True)
            st.download_button("📥 Download In-Transit Tracking Sheet (.xlsx)", data=get_excel_bytes(df_intransit), file_name="In_Transit_M07_Report.xlsx")
    else:
        st.info("💡 Dashboard Active karne ke liye kripya left sidebar se apni 'Vinculum Base Sheet' upload karne ka prabandh karein.")

# --- ADMIN PANEL EXCLUSIVE REQUISITIONS ---
else:
    st.markdown("### 🔑 Admin Operational Control Room")
    
    # 🛑 REQUIREMENT 5: Live Warehouses Online Monitor
    st.markdown(f"#### 🌐 Active Warehouses Online: `{len(global_store['active_users'])}`")
    if global_store["active_users"]:
        st.write(list(global_store["active_users"].keys()))
        
    # 🛑 REQUIREMENT 6: Warehouse Real-time Activity Audit Logs
    st.markdown("<br>#### 📋 Real-time Warehouse Activity System Logs", unsafe_allow_html=True)
    
    # Show logs in descending order (latest first)
    logs_reversed = list(reversed(global_store["activity_logs"]))
    st.text_area("Audit Trail (Live Logs):", value="\n".join(logs_reversed) if logs_reversed else "No logs captured yet.", height=300)
    
    if st.button("🗑️ Clear Logs History"):
        global_store["activity_logs"] = []
        st.rerun()

