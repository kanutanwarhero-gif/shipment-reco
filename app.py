import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Romsons.In Logistics Portal", page_icon="🚚", layout="wide")

# Premium Amazon-Inspired UI Custom CSS Styling
st.markdown("""
    <style>
    /* Global Background Fix */
    .stApp {
        background-color: #EAEDED !important;
    }
    
    /* Centered Login Container */
    .login-box {
        background-color: #FFFFFF;
        padding: 35px;
        border-radius: 8px;
        border: 1px solid #D5D9D9;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        max-width: 450px;
        margin: 40px auto;
    }
    
    /* Brand Logo Text */
    .brand-logo {
        font-family: 'Amazon Ember', 'Arial', sans-serif;
        font-size: 32px;
        font-weight: 700;
        color: #232F3E;
        text-align: center;
        margin-bottom: 2px;
    }
    .brand-logo span {
        color: #FF9900;
    }
    .brand-sub {
        font-size: 13px;
        color: #565959;
        text-align: center;
        margin-bottom: 25px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Input Labels and Fields */
    label {
        font-weight: 700 !important;
        color: #111111 !important;
        font-size: 14px !important;
    }
    
    /* Main Dashboard Header Elements */
    .main-title { font-size:28px; font-weight:bold; color:#232F3E; margin-bottom:5px; }
    .sub-title { font-size:14px; color:#565959; margin-bottom:20px; }
    .metric-card { background-color: #FFFFFF; border: 1px solid #D5D9D9; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.04); }
    .metric-val { font-size: 26px; font-weight: bold; color: #232F3E; }
    .metric-lbl { font-size: 12px; color: #565959; text-transform: uppercase; margin-top: 5px; font-weight: 600; }
    .banner-update { background-color: #F0F2F2; border-left: 5px solid #232F3E; padding: 10px; border-radius: 4px; color: #232F3E; font-weight: 500; margin-bottom: 15px; }
    
    /* Custom button behavior for premium feel */
    div.stButton > button:first-child {
        background-color: #FF9900 !important;
        color: #111111 !important;
        border: 1px solid #A88734 !important;
        border-radius: 6px !important;
        box-shadow: 0 2px 5px rgba(213,217,217,.5) !important;
        font-weight: 500 !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #F5A623 !important;
        border-color: #846A29 !important;
    }
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
        "portal_status_dict": {},        
        "last_updated": "N/A",           
        "admin_uploading": False,        
        "active_users": {},              
        "activity_logs": []              
    }

global_store = get_global_storage()

# Node User Credentials Logins
WAREHOUSES = {
    "RPPL - DEL": "delhi@123",
    "RPPL - BLR": "bangalore@123",
    "RPPL - KOL": "kolkata@123",
    "RPPL - PUN": "mumbai@123",
    "Admin": "admin@romsons"
}

# Local User session stabilization logic
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None

# --- PREMIUM AMAZON CARD LOOK LOGIN SCREEN ---
if not st.session_state['logged_in']:
    # Wrapper container for centered alignment
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<div class="brand-logo">romsons<span>.in</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Central Logistics Portal</div>', unsafe_allow_html=True)
    
    # Using normal layout inside the styled CSS frame wrapper
    wh_selection = st.selectbox("Select Your Warehouse Node / Role", list(WAREHOUSES.keys()))
    password = st.text_input("Enter Node Password", type="password")
    
    st.markdown('<div style="margin-top:20px;">', unsafe_allow_html=True)
    if st.button("Sign In", use_container_width=True):
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
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop() 

# --- SERVER LIVENESS MONITOR (Sirf Logged-In Users Ke Liye) ---
global_store["active_users"][st.session_state['warehouse']] = time.time()

# Drop disconnected node sessions silently (Timeout threshold)
current_epoch = time.time()
dead_sessions = [u for u, last_ping in list(global_store["active_users"].items()) if current_epoch - last_ping > 15]
for dead_user in dead_sessions:
    if dead_user in global_store["active_users"]:
        del global_store["active_users"][dead_user]

# --- SIDEBAR CONTROL LAYOUT ---
st.sidebar.markdown(f"*🏢 Active Node:* {st.session_state['warehouse']}")

# Attractive Manual Refresh Sync Module
if st.sidebar.button("🔄 Sync & Refresh Live Data", use_container_width=True):
    st.rerun()

if st.sidebar.button("Logout Node", use_container_width=True):
    timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
    global_store["activity_logs"].append(f"🔴 [{timestamp} IST] {st.session_state['warehouse']} logged out manually.")
    if st.session_state['warehouse'] in global_store["active_users"]:
        del global_store["active_users"][st.session_state['warehouse']]
    st.session_state['logged_in'] = False
    st.session_state['warehouse'] = None
    st.rerun()

# --- POPUP INTERCEPTOR DURING ADMIN UPLOADS ---
if global_store["admin_uploading"] and st.session_state['warehouse'] != "Admin":
    st.markdown("""
        <div style="background-color:#FFF9E6; padding:25px; border-radius:10px; border-left:8px solid #FF9900; margin-top:50px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h3 style="color:#232F3E; margin:0;">⚠️ Admin Uploading Master Data... Please Wait!</h3>
            <p style="color:#565959; font-size:15px; margin-top:8px;">
                Admin is currently processing the live courier portal data sheets. 
                Your dashboard operations are temporarily frozen to ensure reconciliation integrity. 
                Please use the "Sync & Refresh Live Data" button on the sidebar to check if the lock is lifted.
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()  

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
    
    if st.sidebar.button("🔒 1. Lock Terminals & Start Processing", use_container_width=True):
        global_store["admin_uploading"] = True
        st.success("🔒 System terminals locked successfully. Proceed with file parsing.")
        st.rerun()

    if st.sidebar.button("🚀 2. Complete Upload & Save Master Data", use_container_width=True):
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
            
            global_store["portal_status_dict"] = temp_dict
            global_store["last_updated"] = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
            global_store["admin_uploading"] = False  
            
            global_store["activity_logs"].append(f"⚡ [{global_store['last_updated']} IST] Admin processed and synchronized {len(temp_dict)} master entries.")
            st.success("✅ Master Database synchronized and terminals released!")
            st.rerun()
        else:
            st.sidebar.error("Error: No files queued in slot bucket!")

    # Admin Dashboard
    st.markdown("### 🔑 Admin Operations Center")
    online_nodes = [u for u in global_store["active_users"].keys() if u != "Admin"]
    st.markdown(f"#### 🌐 Active Node Connections Live: {len(online_nodes)}")
    if online_nodes:
        st.write(online_nodes)
        
    st.markdown("<br>#### 📋 Real-time Warehouse System Registers Logs (IST)", unsafe_allow_html=True)
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
        
        st.markdown("### 📊 Consolidated Summary Status")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_vinc)}</div><div class='metric-lbl'>Total Dispatches (M07)</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#16A34A;'>{len(df_delivered)}</div><div class='metric-lbl'>Delivered Shipments</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EA580C;'>{len(df_intransit)}</div><div class='metric-lbl'>In-Transit Tracking</div></div>", unsafe_allow_html=True)
        avg_t = df_delivered['Days_TAT_or_Aging'].mean()
        c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#2563EB;'>{f'{avg_t:.1f} Days' if pd.notnull(avg_t) else 'N/A'}</div><div class='metric-lbl'>Avg Delivery TAT</div></div>", unsafe_allow_html=True)
        
        if f"{st.session_state['warehouse']}_uploaded" not in st.session_state:
            timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
            global_store["activity_logs"].append(f"📝 [{timestamp} IST] {st.session_state['warehouse']} evaluated base rows.")
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
