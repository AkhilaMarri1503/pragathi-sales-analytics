import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from fpdf import FPDF
import re

st.set_page_config(page_title="Pragathi Shoes - Sales Analytics", layout="wide")

st.title("Pragathi Shoes - Sales Analytics Dashboard")
st.markdown("Track sales patterns, identify trends, and forecast demand")

# Branch configuration
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

def process_sales_file(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        
        # Try to find the right columns
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
        
        # If no headers found, try reading without headers
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
    
    # Extract size from product description if needed
    if size_col is None:
        size_match = df['Product'].str.extract(r'(\d+)')
        df['Size'] = size_match.fillna('N/A')[0]
    
    return df, None

def generate_sales_report_pdf(sales_df, period_days):
    if sales_df.empty:
        return None
    
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "PRAGATHI SHOES - SALES REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Period: Last {period_days} days", ln=True, align='C')
    pdf.cell(200, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
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
# SIDEBAR
# ============================================

with st.sidebar:
    st.header("Analytics Configuration")
    
    st.subheader("Time Period")
    period_days = st.select_slider(
        "Select analysis period",
        options=[7, 14, 30, 60, 90, 180, 365],
        value=30
    )
    
    st.divider()
    
    st.subheader("Upload Sales File")
    sales_file = st.file_uploader("Sales Data CSV", type=["csv"])
    
    st.divider()
    
    st.write("Supported Formats:")
    st.write("- Any CSV with sales data")
    st.write("- Auto-detects columns")

# ============================================
# MAIN CONTENT
# ============================================

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
            "Dashboard", "Trends", "Branch Analysis", 
            "Product Analysis", "Reports"
        ])
        
        # TAB 1: DASHBOARD
        with tab1:
            st.subheader("Sales Dashboard")
            
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
            
            # Top products bar chart using matplotlib
            st.subheader("Top 10 Selling Products")
            top_products = sales_df.groupby('Product')['Quantity'].sum().nlargest(10).reset_index()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(top_products['Product'], top_products['Quantity'])
            ax.set_xlabel('Units Sold')
            ax.set_title('Top 10 Products')
            ax.invert_yaxis()
            st.pyplot(fig)
            plt.close()
            
            # Sales by size pie chart
            st.subheader("Sales by Size")
            size_sales = sales_df.groupby('Size')['Quantity'].sum().nlargest(10).reset_index()
            if not size_sales.empty:
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.pie(size_sales['Quantity'], labels=size_sales['Size'], autopct='%1.1f%%')
                ax.set_title('Sales Distribution by Size')
                st.pyplot(fig)
                plt.close()
            else:
                st.info("Size data not available")
        
        # TAB 2: TRENDS
        with tab2:
            st.subheader("Sales Trends and Patterns")
            
            if 'Date' in sales_df.columns and not sales_df['Date'].isna().all():
                # Daily trend line chart
                daily_sales = sales_df.groupby(sales_df['Date'].dt.date)['Quantity'].sum().reset_index()
                daily_sales.columns = ['Date', 'Units Sold']
                
                fig, ax = plt.subplots(figsize=(12, 5))
                ax.plot(daily_sales['Date'], daily_sales['Units Sold'], marker='o', linewidth=2)
                ax.set_xlabel('Date')
                ax.set_ylabel('Units Sold')
                ax.set_title('Daily Sales Trend')
                ax.tick_params(axis='x', rotation=45)
                st.pyplot(fig)
                plt.close()
                
                # Weekly pattern
                sales_df['DayOfWeek'] = sales_df['Date'].dt.day_name()
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                weekday_sales = sales_df.groupby('DayOfWeek')['Quantity'].sum().reindex(weekday_order).reset_index()
                weekday_sales.columns = ['Day', 'Units Sold']
                
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.bar(weekday_sales['Day'], weekday_sales['Units Sold'])
                ax.set_xlabel('Day')
                ax.set_ylabel('Units Sold')
                ax.set_title('Sales by Day of Week')
                ax.tick_params(axis='x', rotation=45)
                st.pyplot(fig)
                plt.close()
                
                # Monthly trend
                sales_df['Month'] = sales_df['Date'].dt.strftime('%Y-%m')
                monthly_sales = sales_df.groupby('Month')['Quantity'].sum().reset_index()
                
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.bar(monthly_sales['Month'], monthly_sales['Quantity'])
                ax.set_xlabel('Month')
                ax.set_ylabel('Units Sold')
                ax.set_title('Monthly Sales Trend')
                ax.tick_params(axis='x', rotation=45)
                st.pyplot(fig)
                plt.close()
        
        # TAB 3: BRANCH ANALYSIS
        with tab3:
            st.subheader("Branch-wise Sales Analysis")
            
            branch_sales = sales_df.groupby('Branch').agg({
                'Quantity': 'sum',
                'Product': 'count'
            }).rename(columns={'Product': 'Transactions'}).reset_index()
            
            if not branch_sales.empty and 'Quantity' in branch_sales.columns:
                branch_sales['Avg per Transaction'] = branch_sales['Quantity'] / branch_sales['Transactions']
            
            st.dataframe(branch_sales, use_container_width=True)
            
            if not branch_sales.empty:
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.bar(branch_sales['Branch'], branch_sales['Quantity'])
                ax.set_xlabel('Branch')
                ax.set_ylabel('Units Sold')
                ax.set_title('Sales by Branch')
                ax.tick_params(axis='x', rotation=45)
                st.pyplot(fig)
                plt.close()
            
            st.subheader("Top Products by Branch")
            if not branch_sales.empty:
                selected_branch = st.selectbox("Select Branch", branch_sales['Branch'].unique())
                branch_products = sales_df[sales_df['Branch'] == selected_branch].groupby('Product')['Quantity'].sum().nlargest(10).reset_index()
                st.dataframe(branch_products, use_container_width=True)
        
        # TAB 4: PRODUCT ANALYSIS
        with tab4:
            st.subheader("Product-wise Sales Analysis")
            
            all_products = sales_df['Product'].unique()
            if len(all_products) > 0:
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
                    if not size_dist.empty:
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.bar(size_dist['Size'], size_dist['Quantity'])
                        ax.set_xlabel('Size')
                        ax.set_ylabel('Units Sold')
                        ax.set_title(f"Size Distribution for {selected_product}")
                        st.pyplot(fig)
                        plt.close()
                    
                    # Branch distribution
                    st.subheader("Branch-wise Sales")
                    branch_dist = product_data.groupby('Branch')['Quantity'].sum().reset_index()
                    if not branch_dist.empty:
                        fig, ax = plt.subplots(figsize=(8, 8))
                        ax.pie(branch_dist['Quantity'], labels=branch_dist['Branch'], autopct='%1.1f%%')
                        ax.set_title("Branch Distribution")
                        st.pyplot(fig)
                        plt.close()
                
                st.subheader("Product Comparison")
                top_products_list = sales_df.groupby('Product')['Quantity'].sum().nlargest(5).index.tolist()
                selected_products = st.multiselect("Compare Products", all_products, default=top_products_list[:3] if len(top_products_list) > 0 else [])
                
                if selected_products:
                    compare_data = sales_df[sales_df['Product'].isin(selected_products)]
                    compare_summary = compare_data.groupby(['Product', 'Branch'])['Quantity'].sum().reset_index()
                    pivot_data = compare_summary.pivot(index='Branch', columns='Product', values='Quantity').fillna(0)
                    st.dataframe(pivot_data, use_container_width=True)
        
        # TAB 5: REPORTS
        with tab5:
            st.subheader("Generate Sales Reports")
            
            st.markdown("**Fast Moving Products (High Demand)**")
            fast_movers = sales_df.groupby(['Product', 'Size'])['Quantity'].sum().nlargest(20).reset_index()
            fast_movers.columns = ['Product', 'Size', 'Units Sold']
            fast_movers['Priority'] = 'HIGH'
            st.dataframe(fast_movers, use_container_width=True)
            
            st.markdown("**Slow Moving Products (Low Demand)**")
            all_products_sales = sales_df.groupby(['Product', 'Size'])['Quantity'].sum().reset_index()
            slow_movers = all_products_sales.nsmallest(20, 'Quantity')
            slow_movers.columns = ['Product', 'Size', 'Units Sold']
            slow_movers['Priority'] = 'LOW'
            st.dataframe(slow_movers, use_container_width=True)
            
            st.markdown("---")
            if st.button("Generate PDF Report"):
                pdf_data = generate_sales_report_pdf(sales_df, period_days)
                if pdf_data:
                    st.download_button(
                        "Download Sales Report (PDF)",
                        pdf_data,
                        f"sales_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                    )
            
            csv = sales_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Raw Sales Data (CSV)",
                csv,
                f"sales_data_{datetime.now().strftime('%Y%m%d')}.csv"
            )

else:
    st.info("Upload your sales CSV file using the sidebar to begin")
    
    st.markdown("### Sales Analytics Dashboard")
    st.write("")
    st.write("**What This App Does:**")
    st.write("- Sales Dashboard with key metrics")
    st.write("- Trend analysis (daily, weekly, monthly)")
    st.write("- Branch performance comparison")
    st.write("- Product and size analysis")
    st.write("- PDF report generation")
    st.write("")
    st.write("**How to Use:**")
    st.write("1. Upload your sales CSV file")
    st.write("2. Select analysis period")
    st.write("3. Explore different tabs for insights")
    st.write("")
    st.write("**Sample Sales File Format:**")
    st.write("Date,Product,Size,Branch,Quantity")
    st.write("2024-01-15,BOYS SCHOOL SHOES,8,POPULAR SHOE COMPANY,5")

st.sidebar.markdown("---")
st.sidebar.caption("v1.0 | Sales Analytics Dashboard")
