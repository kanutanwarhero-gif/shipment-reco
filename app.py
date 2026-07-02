import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
from io import BytesIO

# 1. Page Layout & Config
st.set_page_config(page_title="Romsons Enterprise Logistics Portal", page_icon="🚚", layout="wide")

# Custom Premium Styling
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

# Helper function to get exact Indian Standard Time (IST)
def get_ist_time():
    utc_now = datetime.datetime.utcnow()
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_now = utc_now + ist_offset
    return ist_now

# Server Global Storage (Shared across all users instantly)
@st.cache_resource
def get_global_storage():
    return {
        "portal_status_dict": {},        # Master Courier DB
        "last_updated": "N/A",           # Update Timestamp Banner
        "admin_uploading": False,        # Live Lock Flag for Popup
        "active_users": {},              # Online Warehouse Sessions Tracking
        "activity_logs": []              # System Audit Trail
    }

global_store = get_global_storage()

# User Credentials Logins
WAREHOUSES = {
    "RPPL - DEL": "delhi@123",
    "RPPL - BLR": "bangalore@123",
    "RPPL - KOL": "kolkata@123",
    "RPPL - MUM": "mumbai@123",
    "Admin": "admin@romsons"
}

# Local User state initialization
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
                
                # Dynamic IST activity entry
                timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
                global_store["activity_logs"].append(f"🟢 [{timestamp} IST] {wh_selection} logged in.")
                st.rerun()
            else:
                st.error("❌ Invalid Node Password!")
    st.stop()

# --- REAL-TIME LIVENESS HEARTBEAT SCRIPT ---
# Notify server that the session is active with timestamp
global_store["active_users"][st.session_state['warehouse']] = time.time()

# Drop dead/refreshed connections if no ping received in last 12 seconds
current_epoch = time.time()
dead_sessions = [u for u, last_ping in global_store["active_users"].items() if current_epoch - last_ping > 12]
for dead_user in dead_sessions:
    if dead_user in global_store["active_users"]:
        del global_store["active_users"][dead_user]

# --- SIDEBAR CONTROL LAYOUT ---
st.sidebar.markdown(f"**🟢 Active Node:** `{st.session_state['warehouse']}`")

# Attractive Interactive Sync / Refresh Data Button
if st.sidebar.button("🔄 Sync & Refresh Live Data", use_container_width=True, type="primary"):
    with st.spinner("Fetching latest updates from server..."):
        time.sleep(1)
        st.rerun()

if st.sidebar.button("Logout Node", use_container_width=True):
    timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
    global_store["activity_logs"].append(f"🔴 [{timestamp} IST] {st.session_state['warehouse']} logged out manually.")
    if st.session_state['warehouse'] in global_store["active_users"]:
        del global_store["active_users"][st.session_state['warehouse']]
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None
    st.rerun()

# 🛑 REQUIREMENT 2 & 3: Dynamic Real-time Popup Modal Interceptor for Warehouses
if global_store["admin_uploading"] and st.session_state['warehouse'] != "Admin":
    st.markdown("""
        <div style="background-color:#FEF3C7; padding:25px; border-radius:10px; border-left:8px solid #D97706; margin-top:50px;">
            <h3 style="color:#92400E; margin:0;">⚠️ Admin Uploading Master Data... Please Wait!</h3>
            <p style="color:#B45309; font-size:15px; margin-top:8px;">
                Admin is currently injecting and processing the live courier platform data sheets on the server cluster. 
                Your dashboard controls are temporarily locked to prevent reconciliation mismatches. 
                This screen will automatically release as soon as the upload finishes.
            </p>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(3)
    st.rerun()

# --- MAIN ENGINE DASHBOARD AREA ---
st.markdown(f"<div class='main-title'>📦 Dispatch Reconciliation Dashboard — {st.session_state['warehouse']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='banner-update'>🕒 Courier Portals Last Updated: {global_store['last_updated']} (IST)</div>", unsafe_allow_html=True)

def find_col_by_name(df, possible_names):
    for col in df.columns:
        if str(col).strip().lower() in [name.lower() for name in possible_names]:
            return col
    return None

st.sidebar.header("📁 Data Ingestion Segment")
vinculum_file = None

# Admin Panel Layout Controls (FIXED FOR REALTIME RELEASE)
if st.session_state['warehouse'] == "Admin":
    st.sidebar.subheader("🔒 Admin Upload Engine")
    admin_portal_files = st.sidebar.file_uploader("Upload Courier Portals (Multiple)", type=["xlsx", "csv"], accept_multiple_files=True)
    
    # Files are selected, trigger the lock across all nodes instantly
    if admin_portal_files:
        if not global_store["admin_uploading"] and "lock_triggered" not in st.session_state:
            global_store["admin_uploading"] = True
            st.session_state["lock_triggered"] = True
            st.rerun()

    if st.sidebar.button("🚀 Complete Upload & Save Master Data", use_container_width=True):
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
            
            # Save data globally
            global_store["portal_status_dict"] = temp_dict
            global_store["last_updated"] = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
            
            # STRICT FORCE RELEASE: Release locking mechanism instantly
            global_store["admin_uploading"] = False  
            
            if "lock_triggered" in st.session_state:
                del st.session_state["lock_triggered"]
                
            global_store["activity_logs"].append(f"⚡ [{global_store['last_updated']} IST] Admin successfully reconciled and saved {len(temp_dict)} master tracking numbers.")
            st.success("✅ Global Courier Database synchronized successfully!")
            st.rerun()
        else:
            st.sidebar.error("Upload fields are empty!")
else:
    vinculum_file = st.sidebar.file_uploader("Upload Local Vinculum Base Report", type=["xlsx", "csv"])

# --- WAREHOUSE DATA RECONCILIATION PROCESSOR ---
if st.session_state['warehouse'] != "Admin":
    if vinculum_file:
        if not global_store["portal_status_dict"]:
            st.error("📥 Admin master lookup dump empty. Please await synchronization from Admin.")
            st.stop()
            
        df_vinc = pd.read_csv(vinculum_file) if vinculum_file.name.endswith('.csv') else pd.read_excel(vinculum_file)
        
        # M07 Filter Rules
        vinc_order_id_col = find_col_by_name(df_vinc, ['Order No', 'Order ID', 'External Order No'])
        if vinc_order_id_col:
            df_vinc[vinc_order_id_col] = df_vinc[vinc_order_id_col].astype(str).str.strip()
            df_vinc = df_vinc[df_vinc[vinc_order_id_col].str.startswith('M07', na=False)]
        else:
            st.error("❌ Error: Order reference identifier missing in Vinculum sheet!")
            st.stop()
            
        vinc_wh_col = find_col_by_name(df_vinc, ['SourceWH', 'Warehouse', 'WH'])
        if vinc_wh_col:
            df_vinc = df_vinc[df_vinc[vinc_wh_col] == st.session_state['warehouse']]
            
        vinc_awb_col = find_col_by_name(df_vinc, ['Tracking No', 'AWB Number', 'AWB No'])
        vinc_ship_date = find_col_by_name(df_vinc, ['Ship Date', 'Shipped Date', 'Actual Time of Shipment'])
        vinc_del_date = find_col_by_name(df_vinc, ['Delivery Date', 'Delivered Date'])
        
        if not vinc_awb_col:
            st.error("❌ Target tracking records column error.")
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
        
        # Dashboard UI Cards Grid
        st.markdown("### 📊 Consolidated Summary Status")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_vinc)}</div><div class='metric-lbl'>Total Dispatches (M07)</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#16A34A;'>{len(df_delivered)}</div><div class='metric-lbl'>Delivered Shipments</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EA580C;'>{len(df_intransit)}</div><div class='metric-lbl'>In-Transit Tracking</div></div>", unsafe_allow_html=True)
        avg_t = df_delivered['Days_TAT_or_Aging'].mean()
        c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#2563EB;'>{f'{avg_t:.1f} Days' if pd.notnull(avg_t) else 'N/A'}</div><div class='metric-lbl'>Avg Delivery TAT</div></div>", unsafe_allow_html=True)
        
        # Activity Logging Hook
        if f"{st.session_state['warehouse']}_uploaded" not in st.session_state:
            timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
            global_store["activity_logs"].append(f"📝 [{timestamp} IST] {st.session_state['warehouse']} uploaded Vinculum file ({len(df_vinc)} items).")
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
        
        # Background listener to scan if admin changes status while idle
        time.sleep(3)
        st.rerun()

# --- EXCLUSIVE ADMIN VIEW ENGINE PANEL ---
else:
    st.markdown("### 🔑 Admin Operational Control Room")
    
    # Calculate unique online users inside threshold (Excluding Admin)
    online_warehouses = [u for u in global_store["active_users"].keys() if u != "Admin"]
    
    st.markdown(f"#### 🌐 Active Warehouses Online right now: `{len(online_warehouses)}`")
    if online_warehouses:
        st.write(online_warehouses)
    else:
        st.info("No active warehouse connections detected in last 12 seconds.")
        
    st.markdown("<br>#### 📋 Real-time Warehouse Activity System Logs (IST Timezone)", unsafe_allow_html=True)
    logs_reversed = list(reversed(global_store["activity_logs"]))
    st.text_area("Audit Trail Registers:", value="\n".join(logs_reversed) if logs_reversed else "Log matrix empty.", height=280)
    
    if st.button("🗑️ Clear Logs History"):
        global_store["activity_logs"] = []
        st.rerun()
        
    # Auto-refresh loop for Admin screen to monitor logs/active users in real-time
    time.sleep(4)
    st.rerun()

