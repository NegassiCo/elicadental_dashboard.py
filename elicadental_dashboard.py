# elicadental_dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image

st.set_page_config(page_title="Elica Dental Revenue Cycle Dashboard",
                   layout="wide", initial_sidebar_state="collapsed")

# ---------- Helper UI styles ----------
st.markdown(
    """
    <style>
      .stApp { background-color: #0b1220; color: #f8fafc; }
      .kpi { background: #0f1724; border: 1px solid #1f2937; padding: 12px; border-radius: 10px; }
      .small { color: #9ca3af; font-size:12px }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Sample realistic data generation ----------
def make_sample_data(seed=42):
    np.random.seed(seed)
    payers = ['Delta Dental', 'Medi-Cal', 'Anthem Blue Cross', 'Aetna', 'MetLife', 'Cigna']
    denial_types = ['Coding Error', 'Eligibility', 'Missing Documentation', 'Timely Filing', 'Bundling/Policy']
    start_date = datetime.today().replace(day=1) - pd.DateOffset(months=11)
    rows = []
    for m in range(12):
        month_dt = (start_date + pd.DateOffset(months=m)).replace(day=1)
        month_label = month_dt.strftime("%Y-%m")
        for payer in payers:
            for d_type in denial_types:
                # create realistic variation
                count = int(np.random.poisson(lam=12) + np.random.randint(0, 10))
                amount = int(count * (np.random.uniform(50, 200)))  # $ per denial
                overturned = int(count * np.random.uniform(0.4, 0.8))
                days_to_pay = int(np.random.normal(loc=30, scale=8))
                rows.append({
                    "Date": month_dt.date(),
                    "Month": month_label,
                    "Payer": payer,
                    "Denial Type": d_type,
                    "Denial Count": count,
                    "Amount": amount,
                    "Overturned Count": overturned,
                    "Avg Days To Pay": max(1, days_to_pay)
                })
    df = pd.DataFrame(rows)
    return df

df = make_sample_data()

# ---------- Sidebar filters ----------
st.sidebar.markdown("### Filters")
unique_payers = ['All'] + sorted(df['Payer'].unique().tolist())
payer_sel = st.sidebar.selectbox("Payer", unique_payers, index=0)
date_options = ["Last 3 Months", "Last 6 Months", "Last 12 Months"]
date_sel = st.sidebar.selectbox("Date Range", date_options, index=1)
denial_types = ['All'] + sorted(df['Denial Type'].unique().tolist())
denial_sel = st.sidebar.multiselect("Denial Types (multi)", denial_types, default=['All'])

# compute date cutoff
today = datetime.today()
if date_sel == "Last 3 Months":
    cutoff = (today - pd.DateOffset(months=3)).replace(day=1)
elif date_sel == "Last 6 Months":
    cutoff = (today - pd.DateOffset(months=6)).replace(day=1)
else:
    cutoff = (today - pd.DateOffset(months=12)).replace(day=1)

# apply filters
filtered = df[df['Date'] >= cutoff.date()]
if payer_sel != 'All':
    filtered = filtered[filtered['Payer'] == payer_sel]
if denial_sel and 'All' not in denial_sel:
    filtered = filtered[filtered['Denial Type'].isin(denial_sel)]

# ---------- KPI computations ----------
total_denial_amount = filtered['Amount'].sum()
last_month = (today - pd.DateOffset(months=1)).strftime("%Y-%m")
last_month_amount = filtered[filtered['Month'] == last_month]['Amount'].sum()
# vs prior
prior_month = (today - pd.DateOffset(months=2)).strftime("%Y-%m")
prior_month_amount = filtered[filtered['Month'] == prior_month]['Amount'].sum()
vs_prior_pct = ((last_month_amount - prior_month_amount) / prior_month_amount * 100) if prior_month_amount else 0
rolling_avg = filtered.groupby('Month')['Amount'].sum().tail(6).mean()
clean_claim_rate = 1 - (filtered['Denial Count'].sum() / (filtered['Denial Count'].sum() + 5000))  # example metric
avg_days_to_pay = int(filtered['Avg Days To Pay'].mean())

# Top 3 denial causes
top_causes = filtered.groupby('Denial Type')['Amount'].sum().sort_values(ascending=False).head(3)

# ---------- Layout - Top KPIs ----------
header_col1, header_col2, header_col3, header_col4 = st.columns([2,1,1,1])
with header_col1:
    # optional logo placeholder (replace 'elica_logo.png' in the same folder to display)
    try:
        logo = Image.open("elica_logo.png")
        st.image(logo, width=180)
    except Exception:
        st.markdown("<h2 style='color:#fff;margin:0;padding:0'>Dental Revenue Cycle Dashboard</h2>", unsafe_allow_html=True)

with header_col2:
    st.markdown('<div class="kpi"><div class="small">Total Denial Amount</div><div style="font-size:20px;font-weight:700">${:,.0f}</div></div>'.format(total_denial_amount), unsafe_allow_html=True)
with header_col3:
    st.markdown('<div class="kpi"><div class="small">Last Month End Denials</div><div style="font-size:20px;font-weight:700">${:,.0f}</div></div>'.format(last_month_amount), unsafe_allow_html=True)
with header_col4:
    st.markdown('<div class="kpi"><div class="small">Vs Prior Month</div><div style="font-size:20px;font-weight:700">{:+.1f}%</div></div>'.format(vs_prior_pct), unsafe_allow_html=True)

st.markdown("---")

# ---------- Charts & Tables in compact grid ----------
col1, col2 = st.columns([1.3,1])

with col1:
    st.markdown("### Denial Amount by Type (bar)")
    agg_by_type = filtered.groupby('Denial Type')['Amount'].sum().reset_index().sort_values('Amount', ascending=False)
    fig_type = px.bar(agg_by_type, x='Denial Type', y='Amount', title='', template='plotly_dark', text='Amount')
    fig_type.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=330)
    st.plotly_chart(fig_type, use_container_width=True)
    st.markdown("#### Table: Denial Type Detail")
    st.dataframe(filtered[['Date','Month','Payer','Denial Type','Denial Count','Amount']].sort_values(['Month','Amount'], ascending=[False,False]).reset_index(drop=True), height=220)

with col2:
    st.markdown("### Denial Trend (last months) (line)")
    trend = filtered.groupby('Month')['Amount'].sum().reset_index()
    trend['Month_dt'] = pd.to_datetime(trend['Month'] + "-01")
    trend = trend.sort_values('Month_dt')
    fig_trend = px.line(trend, x='Month', y='Amount', markers=True, template='plotly_dark')
    fig_trend.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=330)
    st.plotly_chart(fig_trend, use_container_width=True)
    st.markdown("#### Table: Trend Detail")
    st.dataframe(trend[['Month','Amount']].reset_index(drop=True), height=220)

st.markdown("---")

col3, col4, col5 = st.columns([1,1,1])

with col3:
    st.markdown("### Payer Mix (pie)")
    payer_agg = filtered.groupby('Payer')['Amount'].sum().reset_index().sort_values('Amount', ascending=False)
    fig_pie = px.pie(payer_agg, names='Payer', values='Amount', template='plotly_dark')
    fig_pie.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=260)
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("#### Table: Payer Detail")
    st.dataframe(payer_agg, height=160)

with col4:
    st.markdown("### Overturns by Type (bar)")
    over_agg = filtered.groupby('Denial Type')['Overturned Count'].sum().reset_index().sort_values('Overturned Count', ascending=False)
    fig_over = px.bar(over_agg, x='Denial Type', y='Overturned Count', template='plotly_dark')
    fig_over.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=260)
    st.plotly_chart(fig_over, use_container_width=True)
    st.markdown("#### Table: Overturn Detail")
    st.dataframe(over_agg, height=160)

with col5:
    st.markdown("### Avg Days to Pay")
    payer_days = filtered.groupby('Payer')['Avg Days To Pay'].mean().round().reset_index().sort_values('Avg Days To Pay')
    fig_days = px.bar(payer_days, x='Payer', y='Avg Days To Pay', template='plotly_dark')
    fig_days.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=260)
    st.plotly_chart(fig_days, use_container_width=True)
    st.markdown("#### Table: Days-To-Pay Detail")
    st.dataframe(payer_days, height=160)

st.markdown("---")

# ---------- Export functions ----------
def to_csv(df_in):
    return df_in.to_csv(index=False).encode('utf-8')

def to_excel(df_in):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_in.to_excel(writer, index=False, sheet_name='Denials')
        writer.save()
    processed_data = output.getvalue()
    return processed_data

def create_pdf_snapshot(title, df_snapshot, charts=[]):
    """
    Build a simple PDF with reportlab. Charts should be filepaths to PNGs.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, 750, title)
    c.setFont("Helvetica", 10)
    c.drawString(30, 735, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    # small table print (first N rows)
    y = 710
    cols = ['Date','Month','Payer','Denial Type','Denial Count','Amount']
    c.setFont("Helvetica-Bold", 9)
    x_positions = [30, 90, 150, 270, 390, 460]
    for i, col in enumerate(cols):
        c.drawString(x_positions[i], y, col)
    c.setFont("Helvetica", 9)
    y -= 14
    for _, row in df_snapshot.head(18).iterrows():
        if y < 60:
            c.showPage()
            y = 750
        for i, col in enumerate(cols):
            c.drawString(x_positions[i], y, str(row[col]))
        y -= 12
    # embed chart images if provided
    y -= 10
    for chart_path in charts:
        try:
            c.showPage()
            c.drawImage(chart_path, 30, 150, width=540, height=360)
        except Exception:
            pass
    c.save()
    buffer.seek(0)
    return buffer

# Export UI
st.markdown("### Export / Share")
export_col1, export_col2, export_col3 = st.columns(3)

with export_col1:
    csv_bytes = to_csv(filtered)
    st.download_button("⬇️ Download CSV", csv_bytes, file_name="elica_denials.csv", mime="text/csv")

with export_col2:
    excel_bytes = to_excel(filtered)
    st.download_button("⬇️ Download Excel", excel_bytes, file_name="elica_denials.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with export_col3:
    # Create a small pdf snapshot using the filtered table and no charts (charts require saving images to disk)
    pdf_buffer = create_pdf_snapshot("Elica Dental Denial Snapshot", filtered[['Date','Month','Payer','Denial Type','Denial Count','Amount']])
    st.download_button("⬇️ Download PDF (snapshot)", pdf_buffer, file_name="elica_denial_snapshot.pdf", mime="application/pdf")

# ---------- Summary insights ----------
st.markdown("### Summary Insights")
insight_1 = f"Top denial causes (by amount): {', '.join(top_causes.index.tolist())}"
insight_2 = f"Average days to pay: {avg_days_to_pay} days"
insight_3 = "Automation opportunities: auto-validate eligibility prior to submission, automated document attach for common missing documentation, and coding validation checks in the EHR-to-837 pipeline."
st.write("- " + insight_1)
st.write("- " + insight_2)
st.write("- " + insight_3)

st.markdown("### Raw Data (preview)")
st.dataframe(filtered.sort_values(['Month','Amount'], ascending=[False,False]).reset_index(drop=True).head(200), height=250)
