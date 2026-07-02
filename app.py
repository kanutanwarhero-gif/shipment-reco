import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Romsons Enterprise Logistics Portal", page_icon="🚚", layout="wide")

# Custom UI Styling
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

# Helper function for Exact Indian Standard Time (IST)
def get_ist_time():
    utc_now = datetime.datetime.utcnow()
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    return utc_now + ist_offset

# Server Global Storage (Shared across nodes)
@st.cache_resource
def get_global_storage():
    return {
        "portal_status_dict": {},        # Master Courier DB
        "last_updated": "N/A",           # Update Timestamp Banner
        "admin_uploading": False,        # Strict Core Flag for Popup Lock
        "active_users": {},              # Online Tracker
        "activity_logs": []              # System Audit Trail
    }

global_store = get_global_storage()

# Node User Credentials Logins
WAREHOUSES = {
    "RPPL - DEL": "delhi@123",
    "RPPL - BLR": "bangalore@123",
    "RPPL - KOL": "kolkata@123",
    "RPPL - MUM": "mumbai@123",
    "Admin": "admin@romsons"
}

# Local User session stabilization logic
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
                
                # Active Ping Register
                global_store["active_users"][wh_selection] = time.time()
                timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
                global_store["activity_logs"].append(f"🟢 [{timestamp} IST] {wh_selection} logged in.")
                st.rerun()
            else:
                st.error("❌ Invalid Node Password!")
    st.stop()

# --- SERVER LIVENESS MONITOR & PERSISTENT CHECK ---
if st.session_state['logged_in']:
    global_store["active_users"][st.session_state['warehouse']] = time.time()

# Drop disconnected node sessions silently (Timeout threshold)
current_epoch = time.time()
dead_sessions = [u for u, last_ping in list(global_store["active_users"].items()) if current_epoch - last_ping > 15]
for dead_user in dead_sessions:
    if dead_user in global_store["active_users"]:
        del global_store["active_users"][dead_user]

# --- SIDEBAR CONTROL LAYOUT ---
st.sidebar.markdown(f"**🟢 Active Node:** `{st.session_state['warehouse']}`")

# Attractive Manual Refresh Sync Module
if st.sidebar.button("🔄 Sync & Refresh Live Data", use_container_width=True, type="primary"):
    st.rerun()

if st.sidebar.button("Logout Node", use_container_width=True):
    timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
    global_store["activity_logs"].append(f"🔴 [{timestamp} IST] {st.session_state['warehouse']} logged out manually.")
    if st.session_state['warehouse'] in global_store["active_users"]:
        del global_store["active_users"][st.session_state['warehouse']]
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None
    st.rerun()

# 🛑 REQUIREMENT 2 & 3: Dynamic Popup Interceptor (Isolated from local state crash)
if global_store["admin_uploading"] and st.session_state['warehouse'] != "Admin":
    st.markdown("""
        <div style="background-color:#FEF3C7; padding:25px; border-radius:10px; border-left:8px solid #D97706; margin-top:50px;">
            <h3 style="color:#92400E; margin:0;">⚠️ Admin Uploading Master Data... Please Wait!</h3>
            <p style="color:#B45309; font-size:15px; margin-top:8px;">
                Admin is currently processing the live courier portal data sheets. 
                Your dashboard operations are temporarily frozen to ensure reconciliation integrity. 
                Please use the "Sync & Refresh Live Data" button on the sidebar to check if the lock is lifted.
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()  # Prevents rendering and scripts execution until released

# --- MAIN DASHBOARD INTERFACE AREA ---
st.markdown(f"<div class='main-title'>📦 Dispatch Reconciliation Dashboard — {st.session_state['warehouse']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='banner-update'>🕒 Courier Portals Last Updated: {global_store['last_updated']} (IST)</div>", unsafe_allow_html=True)

def find_col_by_name(df, possible_names):
    for col in df.columns:
        if str(col).strip().lower() in [name.lower() for name in possible_names]:
            return col
    return None

st.sidebar.header("📁 Data Ingestion Segment")
vinculum_file = None

# --- EXCLUSIVE ADMIN WORKBENCH PANEL ---
if st.session_state['warehouse'] == "Admin":
    st.sidebar.subheader("🔒 Admin Control Matrix")
    admin_portal_files = st.sidebar.file_uploader("Upload Courier Portals (Multiple)", type=["xlsx", "csv"], accept_multiple_files=True)
    
    # 🟢 Button 1: Start Process locks the system explicitly
    if st.sidebar.button("🔒 1. Lock Terminals & Start Processing", use_container_width=True):
        global_store["admin_uploading"] = True
        st.success("🔒 System terminals locked successfully. Proceed with file parsing.")
        st.rerun()

    # 🟢 Button 2: Process, Save and Release Terminals strictly
    if st.sidebar.button("🚀 2. Complete Upload & Save Master Data", use_container_width=True, type="primary"):
        if admin_portal_files:
            temp_dict = {}
            for p_file in admin_portal_files:
                df_p = pd.read_csv(p_file) if p_file.name.endswith('.csv') else pd.read_excel(p_file)
                awb_col = find_col_by_name(df_p, ['trackingid', 'waybill', 'awb no', 'awb number', 'tracking number'])
                status_col = find_col_by_name(df_p, ['order status', 'current status', 'status', 'delivery status'])
                
                if awb_col and status_col:
                    for key, val in zip(df_p[awb_col].astype(str).str.strip(), df_p[status_col].astype(str).str.strip()):
                        if key != 'nan':
                            temp_dict[key] = val
            
            # Flush data to cloud cache database registers
            global_store["portal_status_dict"] = temp_dict
            global_store["last_updated"] = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
            
            # STRICT AND ABSOLUTE UNLOCK OVERRIDE
            global_store["admin_uploading"] = False  
            
            global_store["activity_logs"].append(f"⚡ [{global_store['last_updated']} IST] Admin processed and synchronized {len(temp_dict)} master entries.")
            st.success("✅ Master Database synchronized and terminals released!")
            st.rerun()
        else:
            st.sidebar.error("Error: No files queued in slot bucket!")

    # Admin Control Analytics Panel Metrics
    st.markdown("### 🔑 Admin Operations Center")
    online_nodes = [u for u in global_store["active_users"].keys() if u != "Admin"]
    st.markdown(f"#### 🌐 Active Node Connections Live: `{len(online_nodes)}`")
    if online_nodes:
        st.write(online_nodes)
        
    st.markdown("<br>#### 📋 Real-time Warehouse System Registers Logs", unsafe_allow_html=True)
    logs_rev = list(reversed(global_store["activity_logs"]))
    st.text_area("Audit Registers Display:", value="\n".join(logs_rev) if logs_rev else "Logs empty.", height=250)
    
    if st.button("🗑️ Clear Audit History Registers"):
        global_store["activity_logs"] = []
        st.rerun()

# --- STANDARD WAREHOUSE RECONCILIATION PANELS ---
else:
    vinculum_file = st.sidebar.file_uploader("Upload Local Vinculum Base Report", type=["xlsx", "csv"])
    
    if vinculum_file:
        if not global_store["portal_status_dict"]:
            st.error("📥 Master lookup database reference is blank. Await Admin cloud configuration synchronization.")
            st.stop()
            
        df_vinc = pd.read_csv(vinculum_file) if vinculum_file.name.endswith('.csv') else pd.read_excel(vinculum_file)
        
        # M07 Strict Validation Filtering
        vinc_order_id_col = find_col_by_name(df_vinc, ['Order No', 'Order ID', 'External Order No'])
        if vinc_order_id_col:
            df_vinc[vinc_order_id_col] = df_vinc[vinc_order_id_col].astype(str).str.strip()
            df_vinc = df_vinc[df_vinc[vinc_order_id_col].str.startswith('M07', na=False)]
        else:
            st.error("❌ Schema Validation Error: Order identifier mismatch.")
            st.stop()
            
        vinc_wh_col = find_col_by_name(df_vinc, ['SourceWH', 'Warehouse', 'WH'])
        if vinc_wh_col:
            df_vinc = df_vinc[df_vinc[vinc_wh_col] == st.session_state['warehouse']]
            
        vinc_awb_col = find_col_by_name(df_vinc, ['Tracking No', 'AWB Number', 'AWB No'])
        vinc_ship_date = find_col_by_name(df_vinc, ['Ship Date', 'Shipped Date'])
        vinc_del_date = find_col_by_name(df_vinc, ['Delivery Date', 'Delivered Date'])
        
        if not vinc_awb_col:
            st.error("❌ Base Record Mapping Error: Tracking number index mismatch.")
            st.stop()
            
        df_vinc['Clean_AWB'] = df_vinc[vinc_awb_col].astype(str).str.strip()
        df_vinc['Reconciled_Status'] = df_vinc['Clean_AWB'].map(global_store["portal_status_dict"]).fillna("In-Transit")
        
        if vinc_ship_date: df_vinc['Ship_Clean'] = pd.to_datetime(df_vinc[vinc_ship_date], errors='coerce')
        if vinc_del_date: df_vinc['Del_Clean'] = pd.to_datetime(df_vinc[vinc_del_date], errors='coerce')
        
        current_date = pd.to_datetime(get_ist_time().date())
        is_delivered = df_vinc['Reconciled_Status'].astype(str).str.lower().str.contains('deliver')
        
        df_vinc['Days_TAT_or_Aging'] = np.where(
            is_delivered,
            (df_vinc['Del_Clean'] - df_vinc['Ship_Clean']).dt.days,
            (current_date - df_vinc['Ship_Clean']).dt.days
        )
        
        df_delivered = df_vinc[is_delivered]
        df_intransit = df_vinc[~is_delivered]
        
        # UI Metrics Analytics Display Grid
        st.markdown("### 📊 Consolidated Summary Status")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_vinc)}</div><div class='metric-lbl'>Total Dispatches (M07)</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#16A34A;'>{len(df_delivered)}</div><div class='metric-lbl'>Delivered Shipments</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EA580C;'>{len(df_intransit)}</div><div class='metric-lbl'>In-Transit Tracking</div></div>", unsafe_allow_html=True)
        avg_t = df_delivered['Days_TAT_or_Aging'].mean()
        c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#2563EB;'>{f'{avg_t:.1f} Days' if pd.notnull(avg_t) else 'N/A'}</div><div class='metric-lbl'>Avg Delivery TAT</div></div>", unsafe_allow_html=True)
        
        if f"{st.session_state['warehouse']}_uploaded" not in st.session_state:
            timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
            global_store["activity_logs"].append(f"📝 [{timestamp} IST] {st.session_state['warehouse']} evaluated and reconciled base rows.")
            st.session_state[f"{st.session_state['warehouse']}_uploaded"] = True

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

