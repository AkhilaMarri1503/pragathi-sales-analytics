import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import re

st.set_page_config(page_title="Pragathi Shoes - Sales Analytics", layout="wide")

st.title("📈 Pragathi Shoes - Sales Analytics Dashboard")
st.markdown("**Track sales patterns, identify trends, and forecast demand**")

# ============================================
# BRANCH CONFIGURATION
# ============================================

BRANCHES = {
    "POPULAR SHOE COMPANY": "Popular Store",
    "PRAGATHI SHOES AMD 2": "AMD 2 Store",
    "PRAGATHI SHOES RAGOLU": "Ragolu Store",
    "PRAGATHI SHOES BALAGA": "Balaga Store",
    "PRAGATHI SHOES AKP": "AKP Store"
}

def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip()

# ============================================
# SALES DATA PROCESSING
# ============================================

def detect_sales_format(df):
    """Auto-detect the format of sales file"""
    
    columns = df.columns.str.lower()
    
    # Look for common patterns
    has_date = any(col in ['date', 'sale_date', 'transaction_date', 'day'] for col in columns)
    has_product = any(col in ['product', 'item', 'sku', 'description'] for col in columns)
    has_qty = any(col in ['quantity', 'qty', 'sold', 'sales'] for col in columns)
    has_branch = any(col in ['branch', 'store', 'location'] for col in columns)
    has_size = any(col in ['size', 'sizes'] for col in columns)
    
    return {
        "has_date": has_date,
        "has_product": has_product,
        "has_qty": has_qty,
        "has_branch": has_branch,
        "has_size": has_size
    }

def process_sales_file(uploaded_file):
    """Parse and process sales file"""
    
    # Try reading with headers first
    try:
        df = pd.read_csv(uploaded_file)
        format_info = detect_sales_format(df)
        
        # Map columns
        date_col = None
        product_col = None
        qty_col = None
        branch_col = None
        size_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if format_info["has_date"] and any(d in col_lower for d in ['date', 'day']):
                date_col = col
            if format_info["has_product"] and any(p in col_lower for p in ['product', 'item', 'sku']):
                product_col = col
            if format_info["has_qty"] and any(q in col_lower for q in ['quantity', 'qty', 'sold']):
                qty_col = col
            if format_info["has_branch"] and any(b in col_lower for b in ['branch', 'store']):
                branch_col = col
            if format_info["has_size"] and 'size' in col_lower:
                size_col = col
        
        # If no headers found, try reading without headers
        if product_col is None or qty_col is None:
            df = pd.read_csv(uploaded_file, header=None)
            # Assume first column is product, second is quantity
            product_col = 0
            qty_col = 1
            df.columns = ['Product', 'Quantity'] + [f'Col_{i}' for i in range(2, len(df.columns))]
            date_col = None
            branch_col = None
            size_col = None
    
    except Exception as e:
        return None, str(e)
    
    # Clean and prepare data
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
    
    # Remove rows with zero quantity
    df = df[df['Quantity'] > 0]
    
    # Extract size from product description if not present
    if size_col is None and 'Size' not in df.columns:
        df['Size'] = df['Product'].str.extract(r'(\d+)').fillna('N/A')
    
    # Extract product type
    df['Product_Type'] = df['Product'].apply(lambda x: 'BOYS' if 'BOYS' in x.upper() else ('GIRLS' if 'GIRLS' in x.upper() else 'OTHER'))
    
    return df, None

# ============================================
# PDF REPORT GENERATION
# ============================================

def generate_sales_report_pdf(sales_df, period_days):
    """Generate PDF sales report"""
    
    if sales_df.empty:
        return None
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "PRAGATHI SHOES - SALES REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Period: Last {period_days} days", ln=True, align='C')
    pdf.cell(200, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    # Summary
    total_sales = sales_df['Quantity'].sum()
    total_transactions = len(sales_df)
    avg_daily = total_sales / period_days if period_days > 0 else total_sales
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "SUMMARY STATISTICS", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 8, f"Total Units Sold: {int(total_sales):,}", ln=False)
    pdf.cell(100, 8, f"Total Transactions: {total_transactions:,}", ln=True)
    pdf.cell(100, 8, f"Average Daily Sales: {avg_daily:.1f} units", ln=True)
    pdf.ln(10)
    
    # Top products
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "TOP 10 SELLING PRODUCTS", ln=True)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(80, 8, "Product", 1)
    pdf.cell(30, 8, "Size", 1)
    pdf.cell(40, 8, "Total Sold", 1)
    pdf.ln()
    
    top_products = sales_df.groupby(['Product', 'Size'])['Quantity'].sum().nlargest(10).reset_index()
    pdf.set_font("Arial", size=8)
    for _, row in top_products.iterrows():
        pdf.cell(80, 7, clean_text(row['Product'])[:78], 1)
        pdf.cell(30, 7, clean_text(row['Size'])[:28], 1)
        pdf.cell(40, 7, str(int(row['Quantity'])), 1)
        pdf.ln()
    
    pdf.ln(5)
    
    # Sales by branch
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "SALES BY BRANCH", ln=True)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(80, 8, "Branch", 1)
    pdf.cell(60, 8, "Units Sold", 1)
    pdf.ln()
    
    branch_sales = sales_df.groupby('Branch')['Quantity'].sum().reset_index()
    pdf.set_font("Arial", size=8)
    for _, row in branch_sales.iterrows():
        pdf.cell(80, 7, clean_text(row['Branch'])[:78], 1)
        pdf.cell(60, 7, str(int(row['Quantity'])), 1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1', errors='ignore')

# ============================================
# MAIN APP
# ============================================

# Sidebar
with st.sidebar:
    st.header("⚙️ Analytics Configuration")
    
    st.subheader("Time Period")
    period_days = st.select_slider(
        "Select analysis period",
        options=[7, 14, 30, 60, 90, 180, 365],
        value=30
    )
    
    st.divider()
    
    st.subheader("📁 Upload Sales File")
    sales_file = st.file_uploader("Sales Data CSV", type=["csv"])
    
    st.divider()
    
    st.markdown("**Supported Formats:**")
    st.markdown("- Any CSV with sales data")
    st.markdown("- Auto-detects columns")
    st.markdown("- Works with POS exports")
    st.markdown("- Works with manual entries")

# Main content
if sales_file:
    with st.spinner("Analyzing sales data..."):
        sales_df, error = process_sales_file(sales_file)
        
        if error:
            st.error(f"Error processing file: {error}")
            st.stop()
        
        if sales_df.empty:
            st.warning("No sales data found in the file")
            st.stop()
        
        # Filter by date if available
        if 'Date' in sales_df.columns and not sales_df['Date'].isna().all():
            max_date = sales_df['Date'].max()
            min_date = max_date - timedelta(days=period_days)
            sales_df = sales_df[sales_df['Date'] >= min_date]
        
        # Create tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Dashboard", "📈 Trends", "🏪 Branch Analysis", 
            "📦 Product Analysis", "📄 Reports"
        ])
        
        # ============================================
        # TAB 1: DASHBOARD
        # ============================================
        with tab1:
            st.subheader("Sales Dashboard")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_sales = sales_df['Quantity'].sum()
            total_transactions = len(sales_df)
            avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0
            unique_products = sales_df['Product'].nunique()
            
            with col1:
                st.metric("Total Units Sold", f"{int(total_sales):,}")
            with col2:
                st.metric("Total Transactions", f"{total_transactions:,}")
            with col3:
                st.metric("Avg per Transaction", f"{avg_transaction:.1f}")
            with col4:
                st.metric("Unique Products", unique_products)
            
            st.markdown("---")
            
            # Sales trend chart
            if 'Date' in sales_df.columns and not sales_df['Date'].isna().all():
                st.subheader("Sales Trend")
                daily_sales = sales_df.groupby(sales_df['Date'].dt.date)['Quantity'].sum().reset_index()
                daily_sales.columns = ['Date', 'Units Sold']
                
                fig = px.line(daily_sales, x='Date', y='Units Sold', title="Daily Sales Trend")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Top products
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top 10 Selling Products")
                top_products = sales_df.groupby('Product')['Quantity'].sum().nlargest(10).reset_index()
                fig = px.bar(top_products, x='Product', y='Quantity', title="Top Products by Units Sold")
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Sales by Size")
                size_sales = sales_df.groupby('Size')['Quantity'].sum().nlargest(10).reset_index()
                if not size_sales.empty:
                    fig = px.pie(size_sales, values='Quantity', names='Size', title="Sales Distribution by Size")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Size data not available")
        
        # ============================================
        # TAB 2: TRENDS
        # ============================================
        with tab2:
            st.subheader("Sales Trends & Patterns")
            
            if 'Date' in sales_df.columns and not sales_df['Date'].isna().all():
                # Weekly pattern
                sales_df['DayOfWeek'] = sales_df['Date'].dt.day_name()
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                weekday_sales = sales_df.groupby('DayOfWeek')['Quantity'].sum().reindex(weekday_order).reset_index()
                weekday_sales.columns = ['Day', 'Units Sold']
                
                fig = px.bar(weekday_sales, x='Day', y='Units Sold', title="Sales by Day of Week")
                st.plotly_chart(fig, use_container_width=True)
                
                # Monthly trend
                sales_df['Month'] = sales_df['Date'].dt.strftime('%Y-%m')
                monthly_sales = sales_df.groupby('Month')['Quantity'].sum().reset_index()
                fig = px.line(monthly_sales, x='Month', y='Quantity', title="Monthly Sales Trend")
                st.plotly_chart(fig, use_container_width=True)
        
        # ============================================
        # TAB 3: BRANCH ANALYSIS
        # ============================================
        with tab3:
            st.subheader("Branch-wise Sales Analysis")
            
            branch_sales = sales_df.groupby('Branch').agg({
                'Quantity': 'sum',
                'Product': 'count'
            }).rename(columns={'Product': 'Transactions'}).reset_index()
            branch_sales['Avg per Transaction'] = branch_sales['Quantity'] / branch_sales['Transactions']
            
            st.dataframe(branch_sales, use_container_width=True)
            
            # Branch comparison chart
            fig = px.bar(branch_sales, x='Branch', y='Quantity', title="Sales by Branch")
            st.plotly_chart(fig, use_container_width=True)
            
            # Top products by branch
            st.subheader("Top Products by Branch")
            selected_branch = st.selectbox("Select Branch", branch_sales['Branch'].unique())
            branch_products = sales_df[sales_df['Branch'] == selected_branch].groupby('Product')['Quantity'].sum().nlargest(10).reset_index()
            st.dataframe(branch_products, use_container_width=True)
        
        # ============================================
        # TAB 4: PRODUCT ANALYSIS
        # ============================================
        with tab4:
            st.subheader("Product-wise Sales Analysis")
            
            # Product filter
            all_products = sales_df['Product'].unique()
            selected_product = st.selectbox("Select Product", all_products)
            
            if selected_product:
                product_data = sales_df[sales_df['Product'] == selected_product]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Sold", int(product_data['Quantity'].sum()))
                with col2:
                    st.metric("Transactions", len(product_data))
                with col3:
                    avg = product_data['Quantity'].mean()
                    st.metric("Avg per Transaction", f"{avg:.1f}")
                
                # Size distribution
                st.subheader("Size-wise Sales")
                size_dist = product_data.groupby('Size')['Quantity'].sum().reset_index()
                fig = px.bar(size_dist, x='Size', y='Quantity', title=f"Size Distribution for {selected_product}")
                st.plotly_chart(fig, use_container_width=True)
                
                # Branch distribution
                st.subheader("Branch-wise Sales")
                branch_dist = product_data.groupby('Branch')['Quantity'].sum().reset_index()
                fig = px.pie(branch_dist, values='Quantity', names='Branch', title=f"Branch Distribution for {selected_product}")
                st.plotly_chart(fig, use_container_width=True)
            
            # Product comparison
            st.subheader("Product Comparison")
            top_products_for_compare = sales_df.groupby('Product')['Quantity'].sum().nlargest(5).index.tolist()
            selected_products = st.multiselect("Compare Products", all_products, default=top_products_for_compare[:3])
            
            if selected_products:
                compare_data = sales_df[sales_df['Product'].isin(selected_products)]
                compare_summary = compare_data.groupby(['Product', 'Branch'])['Quantity'].sum().reset_index()
                pivot_data = compare_summary.pivot(index='Branch', columns='Product', values='Quantity').fillna(0)
                st.dataframe(pivot_data, use_container_width=True)
        
        # ============================================
        # TAB 5: REPORTS
        # ============================================
        with tab5:
            st.subheader("Generate Sales Reports")
            
            # Fast movers
            st.markdown("### 🚀 Fast Moving Products (High Demand)")
            fast_movers = sales_df.groupby(['Product', 'Size'])['Quantity'].sum().nlargest(20).reset_index()
            fast_movers.columns = ['Product', 'Size', 'Units Sold']
            fast_movers['Priority'] = 'HIGH'
            st.dataframe(fast_movers, use_container_width=True)
            
            # Slow movers
            st.markdown("### 🐢 Slow Moving Products (Low Demand)")
            all_products_sales = sales_df.groupby(['Product', 'Size'])['Quantity'].sum().reset_index()
            slow_movers = all_products_sales.nsmallest(20, 'Quantity')
            slow_movers.columns = ['Product', 'Size', 'Units Sold']
            slow_movers['Priority'] = 'LOW'
            st.dataframe(slow_movers, use_container_width=True)
            
            # Download report
            st.markdown("---")
            if st.button("📄 Generate PDF Report"):
                pdf_data = generate_sales_report_pdf(sales_df, period_days)
                if pdf_data:
                    st.download_button(
                        "✅ Download Sales Report (PDF)",
                        pdf_data,
                        f"sales_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                    )
            
            # Download raw data
            csv = sales_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Raw Sales Data (CSV)",
                csv,
                f"sales_data_{datetime.now().strftime('%Y%m%d')}.csv"
            )

else:
    st.info("👈 **Upload your sales CSV file to begin analysis**")
    
    st.markdown("""
    ## 📈 Sales Analytics Dashboard
    
    ### What This App Does:
    
    - **Sales Dashboard** - Key metrics and overview
    - **Trend Analysis** - Daily, weekly, monthly patterns
    - **Branch Analysis** - Compare branch performance
    - **Product Analysis** - Identify best/worst sellers
    - **Size Analysis** - See which sizes sell most
    - **Report Generation** - PDF reports for management
    
    ### How to Use:
    
    1. Upload your sales CSV file
    2. Select analysis period (7-365 days)
    3. Explore different tabs for insights
    4. Generate reports for sharing
    
    ### Sample Sales File Format:
    
