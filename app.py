import streamlit as st
import pandas as pd
from io import BytesIO

# --- CONFIGURATION ---
DATABASE_FILE = "sku_database.csv"
# Official logo from your website
LOGO_URL = "https://cdn.shopify.com/s/files/1/0776/1490/7671/files/MBR_LOGO_BLACK_200x.png"

def load_data():
    try:
        return pd.read_csv(DATABASE_FILE)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=['Item', 'SKU', 'L_mm', 'W_mm', 'H_mm', 'Weight_kg'])

def save_data(df):
    df.to_csv(DATABASE_FILE, index=False)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Purchase_Order')
    return output.getvalue()

# --- PAGE SETUP ---
st.set_page_config(page_title="Mirrors By Reflect | Management Portal", layout="wide", page_icon="🪞")

# --- HEADER & LOGO ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(LOGO_URL, width=200)
with col_title:
    st.title("Mirrors By Reflect Management Portal")
    st.caption("Supply Chain & Inventory Management System")

# Initialize session state for the database
if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- TAB NAVIGATION (Reordered: Calculator First) ---
tabs = st.tabs(["🚢 Shipping Calculator", "📦 SKU Database", "📤 Bulk Management"])

# --- TAB 1: CONTAINER CALCULATOR & PO EXTRACTION ---
with tabs[0]:
    st.header("Container Occupancy Calculator")
    containers = {'20ft': 28.0, '40ft': 58.0, '40ft HC': 65.0}
    
    if st.session_state.db.empty:
        st.warning("Your database is empty. Please add SKUs in the Database tab or use Bulk Management first.")
    else:
        selected_skus = st.multiselect("Select SKUs for Shipment", options=st.session_state.db['SKU'].unique())
        
        shipment_items = []
        total_cbm = 0.0
        
        if selected_skus:
            for sku in selected_skus:
                row = st.session_state.db[st.session_state.db['SKU'] == sku].iloc[0]
                c1, c2 = st.columns([1, 4])
                with c1:
                    qty = st.number_input(f"Qty: {sku}", min_value=1, value=1, key=f"q_{sku}")
                
                # CBM Calculation: (L * W * H) / 1,000,000,000 for mm to m3
                unit_cbm = (row['L_mm'] * row['W_mm'] * row['H_mm']) / 1_000_000_000
                item_total_cbm = unit_cbm * qty
                total_cbm += item_total_cbm
                
                shipment_items.append({
                    'SKU': sku, 
                    'Item': row['Item'], 
                    'Quantity': qty, 
                    'Unit CBM': round(unit_cbm, 4),
                    'Total CBM': round(item_total_cbm, 4),
                    'Total Weight (kg)': round(row['Weight_kg'] * qty, 2)
                })

            st.divider()
            st.subheader(f"📊 Total Load: {total_cbm:.3f} CBM")
            
            # Metrics for utilization
            m_cols = st.columns(3)
            for i, (name, cap) in enumerate(containers.items()):
                util = (total_cbm / cap) * 100
                color = "normal" if util <= 100 else "inverse"
                m_cols[i].metric(label=f"{name} Util.", value=f"{util:.1f}%", delta=f"{cap - total_cbm:.2f} CBM left", delta_color=color)

            # PO EXTRACTION
            st.subheader("📄 Generate Purchase Order")
            po_df = pd.DataFrame(shipment_items)
            st.dataframe(po_df, use_container_width=True)
            
            st.download_button(
                label="📥 Download Purchase Order (Excel)",
                data=to_excel(po_df),
                file_name=f"MirrorsByReflect_PO.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- TAB 2: ADD / UPDATE / DELETE INDIVIDUAL SKUs ---
with tabs[1]:
    st.header("Product Database")
    st.dataframe(st.session_state.db, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add / Update SKU")
        with st.form("sku_form", clear_on_submit=True):
            f_sku = st.text_input("SKU Code (e.g. MBR-ARCH-LED)")
            f_item = st.text_input("Item Name (e.g. Arlo Arch LED Mirror)")
            f_l = st.number_input("Length (mm)", min_value=0)
            f_w = st.number_input("Width (mm)", min_value=0)
            f_h = st.number_input("Height (mm)", min_value=0)
            f_wt = st.number_input("Gross Weight (kg)", min_value=0.0)
            
            if st.form_submit_button("Save SKU"):
                if f_sku:
                    new_row = {'Item': f_item, 'SKU': f_sku, 'L_mm': f_l, 'W_mm': f_w, 'H_mm': f_h, 'Weight_kg': f_wt}
                    st.session_state.db = st.session_state.db[st.session_state.db['SKU'] != f_sku]
                    st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.db)
                    st.success(f"SKU {f_sku} saved to Mirrors By Reflect database!")
                    st.rerun()
                else:
                    st.error("SKU Code is required.")

    with col2:
        st.subheader("Delete SKU")
        if not st.session_state.db.empty:
            del_sku = st.selectbox("Select SKU to remove", options=st.session_state.db['SKU'].unique())
            if st.button("Confirm Delete", type="primary"):
                st.session_state.db = st.session_state.db[st.session_state.db['SKU'] != del_sku]
                save_data(st.session_state.db)
                st.warning(f"SKU {del_sku} removed.")
                st.rerun()

# --- TAB 3: BULK UPLOAD & TEMPLATE ---
with tabs[2]:
    st.header("Bulk SKU Management")
    
    st.subheader("1. Download Template")
    template_df = pd.DataFrame(columns=['Item', 'SKU', 'L_mm', 'W_mm', 'H_mm', 'Weight_kg'])
    csv_template = template_df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📄 Download CSV Template",
        data=csv_template,
        file_name="MBR_SKU_Template.csv",
        mime="text/csv"
    )
    
    st.divider()
    
    st.subheader("2. Upload Completed List")
    uploaded_file = st.file_uploader("Upload your filled MBR CSV file", type="csv")
    
    if uploaded_file:
        try:
            bulk_df = pd.read_csv(uploaded_file)
            st.write("Preview of Upload:")
            st.dataframe(bulk_df.head())
            
            if st.button("Confirm Bulk Import"):
                combined_db = pd.concat([st.session_state.db, bulk_df]).drop_duplicates(subset=['SKU'], keep='last')
                st.session_state.db = combined_db
                save_data(combined_db)
                st.success("Mirrors By Reflect database updated!")
                st.rerun()
        except Exception as e:
            st.error(f"Error processing file: {e}")