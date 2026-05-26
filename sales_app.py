import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Pragathi Shoes - Sales Analytics", layout="wide")

st.title("Pragathi Shoes - Sales Analytics Dashboard")
st.markdown("Track sales patterns and identify trends")

def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip()

def process_sales_file(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        
        product_col = None
        qty_col = None
        branch_col = None
        date_col = None
        size_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'product' in col_lower or 'item' in col_lower or 'sku' in col_lower:
                product_col = col
            if 'quantity' in col_lower or 'qty' in col_lower or 'sold' in col_lower:
                qty_col = col
            if 'branch' in col_lower or 'store' in col_lower:
                branch_col = col
            if 'date' in col_lower:
                date_col = col
            if 'size' in col_lower:
                size_col = col
        
        if product_col is None or qty_col is None:
            df = pd.read_csv(uploaded_file, header=None)
            product_col = 0
            qty_col = 1
            df.columns = ['Product', 'Quantity'] + [f'Col_{i}' for i in range(2, len(df.columns))]
            date_col = None
            branch_col = None
            size_col = None
    
    except Exception as e:
        return None, str(e)
    
    if product_col:
        df['Product'] = df[product_col].astype(str).apply(clean_text)
    if qty_col:
        df['Quantity'] = pd.to_numeric(df[qty_col], errors='coerce').fillna(0)
    if branch_col:
        df['Branch'] = df[branch_col].astype(str).apply(clean_text)
    else:
        df['Branch'] = 'All Branches'
    if size_col:
        df['Size'] = df[size_col].astype(str).apply(clean_text)
    else:
        df['Size'] = 'N/A'
    if date_col:
        df['Date'] = pd.to_datetime(df[date_col], errors='coerce')
    
    df = df[df['Quantity'] > 0]
    
    if size_col is None:
        size_match = df['Product'].str.extract(r'(\d+)')
        df['Size'] = size_match.fillna('N/A')[0]
    
    return df, None

with st.sidebar:
    st.header("Configuration")
    period_days = st.select_slider("Analysis Period (days)", options=[7, 14, 30, 60, 90], value=30)
    st.divider()
    sales_file = st.file_uploader("Upload Sales CSV", type=["csv"])

if sales_file:
    with st.spinner("Analyzing..."):
        sales_df, error = process_sales_file(sales_file)
        
        if error:
            st.error(f"Error: {error}")
            st.stop()
        
        if sales_df.empty:
            st.warning("No data found")
            st.stop()
        
        if 'Date' in sales_df.columns and not sales_df['Date'].isna().all():
            max_date = sales_df['Date'].max()
            min_date = max_date - timedelta(days=period_days)
            sales_df = sales_df[sales_df['Date'] >= min_date]
        
        tab1, tab2, tab3 = st.tabs(["Dashboard", "Product Analysis", "Branch Analysis"])
        
        with tab1:
            st.subheader("Key Metrics")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Units Sold", f"{int(sales_df['Quantity'].sum()):,}")
            c2.metric("Transactions", len(sales_df))
            c3.metric("Products", sales_df['Product'].nunique())
            c4.metric("Avg per Transaction", f"{sales_df['Quantity'].mean():.1f}")
            
            st.subheader("Top 10 Products")
            top_df = sales_df.groupby('Product')['Quantity'].sum().nlargest(10).reset_index()
            st.dataframe(top_df, use_container_width=True)
            
            st.subheader("Sales by Size")
            size_df = sales_df.groupby('Size')['Quantity'].sum().nlargest(10).reset_index()
            st.dataframe(size_df, use_container_width=True)
        
        with tab2:
            st.subheader("Product Search")
            all_products = sorted(sales_df['Product'].unique())
            selected = st.selectbox("Select Product", all_products)
            
            if selected:
                prod_data = sales_df[sales_df['Product'] == selected]
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Sold", int(prod_data['Quantity'].sum()))
                c2.metric("Transactions", len(prod_data))
                c3.metric("Avg per Sale", f"{prod_data['Quantity'].mean():.1f}")
                
                st.subheader("Size Breakdown")
                size_break = prod_data.groupby('Size')['Quantity'].sum().reset_index()
                st.dataframe(size_break, use_container_width=True)
                
                st.subheader("Branch Breakdown")
                branch_break = prod_data.groupby('Branch')['Quantity'].sum().reset_index()
                st.dataframe(branch_break, use_container_width=True)
        
        with tab3:
            st.subheader("Branch Performance")
            branch_df = sales_df.groupby('Branch').agg({'Quantity': 'sum', 'Product': 'count'}).reset_index()
            branch_df.columns = ['Branch', 'Units Sold', 'Transactions']
            branch_df['Avg/Transaction'] = branch_df['Units Sold'] / branch_df['Transactions']
            st.dataframe(branch_df, use_container_width=True)
            
            st.subheader("Fast Movers (High Demand)")
            fast = sales_df.groupby(['Product', 'Size'])['Quantity'].sum().nlargest(20).reset_index()
            fast.columns = ['Product', 'Size', 'Units Sold']
            st.dataframe(fast, use_container_width=True)
            
            st.subheader("Slow Movers (Low Demand)")
            all_prods = sales_df.groupby(['Product', 'Size'])['Quantity'].sum().reset_index()
            slow = all_prods.nsmallest(20, 'Quantity')
            slow.columns = ['Product', 'Size', 'Units Sold']
            st.dataframe(slow, use_container_width=True)
        
        csv = sales_df.to_csv(index=False).encode()
        st.download_button("Download Data", csv, "sales_data.csv")

else:
    st.info("Upload your sales CSV file")
    st.markdown("""
    ### Expected Format:
