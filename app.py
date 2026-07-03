import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import os
import base64
from io import BytesIO

# Page Layout & View Configuration
st.set_page_config(page_title="Romsons.In | Logistics Portal", page_icon="🚚", layout="wide")

# Safe Base64 Image Encoder Utility
def get_base64_image(image_path):
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        pass
    return ""

# Fetch Base64 data strings for both Banner and Logo
banner_base64 = get_base64_image("login_banner.jpg")
logo_base64 = get_base64_image("romsons_logo.png")

# Custom UI Styling to match eRETAIL layout perfectly and fix ALL visibility bugs
st.markdown(f"""
    <style>
    /* Full Page Settings */
    .stApp {{
        background-color: #FFFFFF !important;
    }}
    
    /* 🔴 SIDEBAR VISIBILITY FIX: Force white text on dark grey sidebar fields */
    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}
    
    /* Split Screen Grid Layout Container */
    .split-container {{
        display: flex;
        width: 100%;
        min-height: 90vh;
        margin: 0;
        padding: 0;
    }}
    
    /* Left Side Image Banner Framework */
    .left-banner-side {{
        flex: 1.2;
        background-color: #0E6F62;
        {"background-image: url('data:image/jpeg;base64," + banner_base64 + "');" if banner_base64 else ""}
        background-size: contain !important;
        background-repeat: no-repeat !important;
        background-position: center center !important;
        border-radius: 12px 0 0 12px;
        min-height: 90vh;
        width: 100%;
    }}
    
    /* Right Side Login Form Framework */
    .right-login-side {{
        flex: 0.9;
        background-color: #FFFFFF;
        padding: 40px 60px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        border-radius: 0 12px 12px 0;
        border: 1px solid #E5E7EB;
    }}
    
    /* Center Box For Internal Inputs styling */
    .login-form-wrapper {{
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
    }}
    
    /* Logo Container Framework */
    .logo-cloud-frame {{
        width: 100%;
        max-width: 250px;
        height: auto;
        max-height: 90px;
        margin: 0 auto 25px auto;
        display: block;
        object-fit: contain;
    }}
    
    /* 🔴 LOGIN CARD VISIBILITY FIX: Black text on white background login inputs */
    .right-login-side label, 
    .right-login-side p, 
    .right-login-side span {{
        color: #111111 !important;
        font-weight: bold !important;
        font-size: 14px !important;
    }}
    
    /* Text input typing alignment coloring */
    .stSelectbox div[data-baseweb="select"], .stTextInput input {{
        background-color: #F3F4F6 !important;
        color: #111111 !important;
        border: 1px solid #D1D5DB !important;
    }}
    
    /* eRETAIL Gradient Blue Login Button */
    div.stButton > button:first-child {{
        background: linear-gradient(180deg, #2A52BE 0%, #1E3A8A 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #1E3A8A !important;
        padding: 10px 30px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    div.stButton > button:first-child:hover {{
        background: linear-gradient(180deg, #1E3A8A 0%, #172554 100%) !important;
        border-color: #172554 !important;
    }}
    
    /* Core Dashboards Element Styles */
    .main-title {{ font-size:26px; font-weight:bold; color:#0E6F62; margin-bottom:5px; }}
    .sub-title {{ font-size:13px; color:#4B5563; margin-bottom:20px; }}
    .metric-card {{ background-color: #F9FAFB; border: 1px solid #E5E7EB; padding: 15px; border-radius: 8px; text-align: center; }}
    .metric-val {{ font-size: 26px; font-weight: bold; color: #0E6F62; }}
    .metric-lbl {{ font-size: 12px; color: #6B7280; text-transform: uppercase; font-weight: 600; }}
    .banner-update {{ background-color: #F0FDF4; border-left: 5px solid #0E6F62; padding: 10px; color: #0E6F62; font-weight: 500; margin-bottom: 15px; }}
    </style>
""", unsafe_allow_html=True)

# Helper function for Indian Standard Time (IST)
def get_ist_time():
    utc_now = datetime.datetime.utcnow()
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    return utc_now + ist_offset

# Shared Cloud Memory Cache
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

# System Node Access Setup
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

# --- eRETAIL EXACT MATCH SPLIT LOGIN INTERFACE ---
if not st.session_state['logged_in']:
    col_left, col_right = st.columns([1.2, 0.9])
    
    with col_left:
        if banner_base64:
            st.markdown('<div class="left-banner-side"></div>', unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="left-banner-side" style="padding:60px; display:flex; flex-direction:column; justify-content:center; color:white;">
                    <h1 style="font-size:36px; font-weight:800; line-height:1.2;">Your business doesn't<br>stop at your desk.</h1>
                    <p style="font-size:15px; opacity:0.9; margin-top:10px;">Please ensure 'login_banner.jpg' is present in your root directory.</p>
                </div>
            """, unsafe_allow_html=True)
            
    with col_right:
        st.markdown('<div class="right-login-side">', unsafe_allow_html=True)
        st.markdown('<div class="login-form-wrapper">', unsafe_allow_html=True)
        
        # Logo rendering via full base64 memory image injection
        if logo_base64:
            st.markdown(f'<img src="data:image/png;base64,{logo_base64}" class="logo-cloud-frame" alt="Romsons" />', unsafe_allow_html=True)
        else:
            st.markdown('<h2 style="text-align:center; color:#0E6F62; font-family:sans-serif; font-weight:bold; font-style:italic; margin-bottom:30px; letter-spacing:1px;">ROMSONS</h2>', unsafe_allow_html=True)
            
        # Selectbox and password inputs
        wh_selection = st.selectbox("Select Your Warehouse Node / Role", list(WAREHOUSES.keys()), key="node_sel")
        password = st.text_input("Enter Node Password", type="password", key="node_pass")
        
        st.markdown('<div style="margin-top:25px;">', unsafe_allow_html=True)
        if st.button("Login", use_container_width=True, key="submit_btn"):
            if WAREHOUSES[wh_selection] == password:
                st.session_state['logged_in'] = True
                st.session_state['warehouse'] = wh_selection
                
                global_store["active_users"][wh_selection] = time.time()
                timestamp = get_ist_time().strftime("%d-%m-%Y %I:%M:%S %p")
                global_store["activity_logs"].append(f"🟢 [{timestamp} IST] {wh_selection} logged in.")
                st.rerun()
            else:
                st.error("❌ Invalid Node Credentials!")
        st.markdown('</div></div></div></div>', unsafe_allow_html=True)
    st.stop()

# --- SERVER ACTIVE MONITOR ENGINE ---
global_store["active_users"][st.session_state['warehouse']] = time.time()
current_epoch = time.time()
dead_sessions = [u for u, last_ping in list(global_store["active_users"].items()) if current_epoch - last_ping > 15]
for dead_user in dead_sessions:
    if dead_user in global_store["active_users"]:
        del global_store["active_users"][dead_user]

# --- SIDEBAR INTERACTIVE ZONE ---
st.sidebar.markdown(f"*🏢 Node:* {st.session_state['warehouse']}")

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

# --- MASTER BANNER UPLOAD LOCK MECHANISM ---
if global_store["admin_uploading"] and st.session_state['warehouse'] != "Admin":
    st.markdown("""
        <div style="background-color:#FFFBEB; padding:25px; border-radius:10px; border-left:8px solid #FF9900; margin-top:50px;">
            <h3 style="color:#232F3E; margin:0;">⚠️ Admin Uploading Master Data... Please Wait!</h3>
            <p style="color:#4B5563; font-size:15px; margin-top:8px;">
                Admin is currently sync-parsing the core courier logs pipelines. 
                Controls will automatically restore. Use the "Sync & Refresh" button to recheck parameters.
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

# --- EXCLUSIVE ADMIN CONTROL MATRIX ---
if st.session_state['warehouse'] == "Admin":
    st.sidebar.subheader("🔒 Admin Controls Slot")
    admin_portal_files = st.sidebar.file_uploader("Upload Courier Portals (Multiple)", type=["xlsx", "csv"], accept_multiple_files=True)
    
    if st.sidebar.button("🔒 1. Lock Terminals & Start Processing", use_container_width=True):
        global_store["admin_uploading"] = True
        st.success("🔒 System node terminals locked successfully.")
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
            
            global_store["activity_logs"].append(f"⚡ [{global_store['last_updated']} IST] Admin synchronized {len(temp_dict)} rows.")
            st.success("✅ System updated and locks released!")
            st.rerun()
        else:
            st.sidebar.error("No data logs detected inside file buffer!")

    # Admin Monitoring Panel Overview
    st.markdown("### 🔑 Admin Central Control Room")
    online_nodes = [u for u in global_store["active_users"].keys() if u != "Admin"]
    st.markdown(f"#### 🌐 Active Node Connections Live: {len(online_nodes)}")
    if online_nodes:
        st.write(online_nodes)
        
    st.markdown("<br>#### 📋 Real-time Warehouse System Activity Registers (IST)", unsafe_allow_html=True)
    logs_rev = list(reversed(global_store["activity_logs"]))
    st.text_area("Audit Log Stream:", value="\n".join(logs_rev) if logs_rev else "Empty logs.", height=250)
    
    if st.button("🗑️ Clear Audit Logs"):
        global_store["activity_logs"] = []
        st.rerun()

# --- STANDARD WAREHOUSE RECONCILIATION SEGMENTS ---
else:
    vinculum_file = st.sidebar.file_uploader("Upload Local Vinculum Base Report", type=["xlsx", "csv"])
    
    if vinculum_file:
        if not global_store["portal_status_dict"]:
            st.error("📥 Reference master dictionary is blank. Await Admin syncing configuration sequence.")
            st.stop()
            
        df_vinc = pd.read_csv(vinculum_file) if vinculum_file.name.endswith('.csv') else pd.read_excel(vinculum_file)
        
        # M07 Constraint Processing Logic
        vinc_order_id_col = find_col_by_name(df_vinc, ['Order No', 'Order ID', 'External Order No'])
        if vinc_order_id_col:
            df_vinc[vinc_order_id_col] = df_vinc[vinc_order_id_col].astype(str).str.strip()
            df_vinc = df_vinc[df_vinc[vinc_order_id_col].str.startswith('M07', na=False)]
        else:
            st.error("❌ Identification Schema validation missing.")
            st.stop()
            
        vinc_wh_col = find_col_by_name(df_vinc, ['SourceWH', 'Warehouse', 'WH'])
        if vinc_wh_col:
            df_vinc = df_vinc[df_vinc[vinc_wh_col] == st.session_state['warehouse']]
            
        vinc_awb_col = find_col_by_name(df_vinc, ['Tracking No', 'AWB Number', 'AWB No'])
        vinc_ship_date = find_col_by_name(df_vinc, ['Ship Date', 'Shipped Date'])
        vinc_del_date = find_col_by_name(df_vinc, ['Delivery Date', 'Delivered Date'])
        
        if not vinc_awb_col:
            st.error("❌ Target tracking records mapping reference error.")
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
        
        # Grid Display Metrics Layout Counters
        st.markdown("### 📊 Consolidated Summary Status")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_vinc)}</div><div class='metric-lbl'>Total Dispatches (M07)</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#16A34A;'>{len(df_delivered)}</div><div class='metric-lbl'>Delivered Shipments</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EA580C;'>{len(df_intransit)}</div><div class='metric-lbl'>In-Transit Tracking</div></div>", unsafe_allow_html=True)
        avg_t = df_delivered['Days_TAT_or_Aging'].mean()
        c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#2563EB;'>{f'{avg_t:.1f} Days' if pd.notnull(avg_t) else 'N/A'}</div><div class='metric-lbl'>Avg Delivery TAT</div></div>", unsafe_allow_html=True)
        
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
