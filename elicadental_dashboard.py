import streamlit as st
from PIL import Image
import os

st.set_page_config(page_title="Elica Dental Dashboard", layout="wide")

# Load logo (expects elica_logo.png at the repository root)
logo_path = os.path.join(os.path.dirname(__file__), "elica_logo.png")

if os.path.exists(logo_path):
    try:
        logo = Image.open(logo_path)
        st.image(logo, use_column_width=True)
    except Exception as e:
        st.header("Elica Dental Dashboard")
        st.error(f"Failed to open elica_logo.png: {e}")
else:
    st.header("Elica Dental Dashboard")
    st.warning("elica_logo.png not found in repository root. Upload the image to display the logo.")

st.markdown("## Overview")
st.write("This is a starter dashboard. Replace this with your application code and visualizations.")

# Example placeholder content
st.subheader("Sample data")
st.write("Add charts, data loading, and interactivity here.")
