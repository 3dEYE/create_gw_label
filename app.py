import streamlit as st
from generate_pdf_label import generate_label, is_ip_address, is_registration_code
import tempfile
import os

st.set_page_config(
    page_title="3dEYE Label Generator", 
    page_icon="🏷️",
    layout="centered"
)

st.title("🏷️ 3dEYE Gateway Label Generator")

st.markdown("---")

# Input method selection
input_method = st.radio(
    "Choose input method:",
    ["Device IP Address", "Registration Code"]
)

with st.form("label_form"):
    if input_method == "Device IP Address":
        st.subheader("📡 Device Connection")
        device_input = st.text_input(
            "Device IP Address", 
            placeholder="192.168.1.100",
            help="Enter the IP address of the device to fetch registration code automatically"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username", value="admin")
        with col2:
            password = st.text_input("Password", value="123456", type="password")
    
    else:
        st.subheader("🔑 Registration Code")
        device_input = st.text_input(
            "Registration Code", 
            placeholder="R57NX98AAFC62AF2A",
            help="Enter the registration code directly to generate QR code"
        )
        username = "admin"  # Default values when not using IP
        password = "123456"
    
    st.subheader("📏 Label Dimensions")
    col3, col4 = st.columns(2)
    with col3:
        width = st.number_input("Width (inches)", value=2.625, min_value=1.0, max_value=10.0, step=0.125)
    with col4:
        height = st.number_input("Height (inches)", value=1.0, min_value=0.5, max_value=5.0, step=0.125)
    
    st.subheader("📁 Output")
    filename = st.text_input("Filename (without extension)", value="device_label")
    
    submitted = st.form_submit_button("🔧 Generate Label", use_container_width=True)

if submitted:
    if not device_input:
        st.error("Please provide either a device IP address or registration code.")
    else:
        # Validate input format
        if input_method == "Device IP Address" and not is_ip_address(device_input):
            st.error("Please enter a valid IP address (e.g., 192.168.1.100)")
        elif input_method == "Registration Code" and not is_registration_code(device_input):
            st.error("Please enter a valid registration code (e.g., R57NX98AAFC62AF2A)")
        else:
            with st.spinner("Generating label..."):
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        pdf_filename = f"{filename}.pdf"
                        pdf_path = os.path.join(tmpdir, pdf_filename)
                        
                        # Generate the label
                        result = generate_label(
                            device_input, 
                            pdf_path, 
                            width, 
                            height, 
                            username, 
                            password
                        )
                        
                        if result:
                            st.success("✅ Label generated successfully!")
                            
                            # Read the PDF file
                            with open(pdf_path, "rb") as f:
                                pdf_data = f.read()
                            
                            # Provide download button
                            st.download_button(
                                label="📄 Download Label PDF",
                                data=pdf_data,
                                file_name=pdf_filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                            st.info(f"📐 Label dimensions: {width}\" x {height}\"")
                            
                        else:
                            st.error("❌ Failed to generate label. Please check your input and try again.")
                            
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ Information")
    st.markdown("""
    ### How to use:
    
    **Method 1: Device IP**
    - Enter the device's IP address
    - Provide username/password
    - The app will fetch the registration code automatically
    
    **Method 2: Registration Code**
    - Enter the registration code directly
    - No network connection needed
    
    ### Label Format:
    - QR code on the left
    - Company logo on top right
    - "Registration Code" label and code on bottom right
    
    ### Requirements:
    - Logo file: `logo.jpg` in the same directory
    - Default dimensions: 2.625" x 1.0"
    """)
    
    st.markdown("---")
    st.markdown("**🔧 3dEYE Gateway Label Generator**")



