"""
Usage: 

python generate_pdf_label.py 192.168.1.100

# Using registration code directly
python generate_pdf_label.py R57NX98AAFC62AF2A

# Custom dimensions
python generate_pdf_label.py R57NX98AAFC62AF2A --width 3.0 --height 1.5

# Custom output filename
python generate_pdf_label.py 192.168.1.100 -o my_label.pdf

"""


import requests
from requests.auth import HTTPBasicAuth
import argparse
import sys
import json
import re
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors

# Optional imports for better QR code handling
try:
    from PIL import Image
    PIL_SUPPORT = True
except ImportError:
    PIL_SUPPORT = False

def is_ip_address(input_str):
    """Check if the input string is a valid IP address."""
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return re.match(ip_pattern, input_str) is not None

def is_registration_code(input_str):
    """Check if the input string looks like a registration code."""
    # Registration codes are typically alphanumeric, longer than IP addresses
    # and contain both letters and numbers
    if len(input_str) < 10:  # Too short to be a reg code
        return False
    if '.' in input_str:  # Contains dots, likely an IP
        return False
    # Check if it contains both letters and numbers
    has_letter = any(c.isalpha() for c in input_str)
    has_digit = any(c.isdigit() for c in input_str)
    return has_letter and has_digit

def fetch_device_data(ip, username, password):
    """Fetch QR code data and registration code from the device via API."""
    qr_url = f"http://{ip}/api/system/qr"
    reg_url = f"http://{ip}/api/system/registerCode"
    
    auth = HTTPBasicAuth(username, password)
    
    try:
        # Fetch QR code SVG
        print(f"Fetching QR code from {qr_url}...")
        qr_response = requests.get(qr_url, auth=auth)
        if qr_response.status_code != 200:
            print(f"Error fetching QR code: HTTP {qr_response.status_code}")
            return None, None
        
        # Fetch registration code
        print(f"Fetching registration code from {reg_url}...")
        reg_response = requests.get(reg_url, auth=auth)
        if reg_response.status_code != 200:
            print(f"Error fetching registration code: HTTP {reg_response.status_code}")
            return None, None
        
        # Parse registration code (matching the working get_qr.py format)
        try:
            reg_data = reg_response.json()
            reg_code = reg_data.get('registerCode', reg_response.text.strip())
        except json.JSONDecodeError:
            reg_code = reg_response.text.strip()
        
        return qr_response.text, reg_code
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None, None

def generate_qr_code(data, size_inches=0.8):
    """Generate QR code image from data."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes for reportlab
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer

def create_pdf_label(reg_code, qr_data_or_buffer, output_path, width_inches=2.625, height_inches=1.0):
    """Create a PDF label with QR code and registration code."""
    
    # Create PDF canvas
    c = canvas.Canvas(output_path, pagesize=(width_inches * inch, height_inches * inch))
    
    # Set up dimensions
    width_pts = width_inches * inch
    height_pts = height_inches * inch
    margin = 0.1 * inch
    
    # Draw border (optional, can be removed)
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.5)
    c.rect(2, 2, width_pts - 4, height_pts - 4)
    
    # QR code dimensions and position (left side)
    qr_size = min(height_pts - 2*margin, 0.75 * inch)
    qr_x = margin
    qr_y = (height_pts - qr_size) / 2
    
    # Generate QR code from registration code
    qr_buffer = generate_qr_code(reg_code)
    
    # Draw QR code
    from reportlab.lib.utils import ImageReader
    qr_image = ImageReader(qr_buffer)
    c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)
    
    # Logo positioning - RIGHT CORNER
    logo_path = "logo.jpg"
    logo_height = 0.25 * inch  # Slightly smaller height
    logo_width = 0.6 * inch    # Slightly smaller width
    
    # Position at absolute right corner
    logo_x = width_pts - margin - logo_width   # Right edge minus margin minus logo width
    logo_y = height_pts - margin - logo_height # Top edge minus margin minus logo height
    
    try:
        import os
        if os.path.exists(logo_path):
            logo_image = ImageReader(logo_path)
            c.drawImage(logo_image, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
        else:
            print(f"Warning: Logo file '{logo_path}' not found. Skipping logo.")
    except Exception as e:
        print(f"Warning: Could not load logo: {e}")
    
    # Text positioning - starts after QR code
    text_start_x = qr_x + qr_size + 0.1 * inch
    
    # Position "Registration Code" label 
    label_y = height_pts * 0.4
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)
    c.drawString(text_start_x, label_y, "Registration Code")
    
    # Position actual registration code beneath the label
    code_y = height_pts * 0.25
    
    # Available width for text (from text start to right margin, leaving small buffer)
    available_text_width = width_pts - text_start_x - margin - 0.05 * inch
    
    # Start with smaller font to fit more text
    font_size = 7
    c.setFont("Helvetica-Bold", font_size)
    text_width = c.stringWidth(reg_code, "Helvetica-Bold", font_size)
    
    if text_width <= available_text_width:
        # Code fits with size 7 font
        c.drawString(text_start_x, code_y, reg_code)
    else:
        # Try even smaller font
        font_size = 6
        c.setFont("Helvetica-Bold", font_size)
        text_width = c.stringWidth(reg_code, "Helvetica-Bold", font_size)
        
        if text_width <= available_text_width:
            c.drawString(text_start_x, code_y, reg_code)
        else:
            # If still doesn't fit, split into two lines
            mid_point = len(reg_code) // 2
            # Try to break at a logical point
            for i in range(mid_point - 2, mid_point + 3):
                if i > 0 and i < len(reg_code):
                    if not reg_code[i-1].isalnum() or not reg_code[i].isalnum():
                        mid_point = i
                        break
            
            line1 = reg_code[:mid_point]
            line2 = reg_code[mid_point:]
            
            # Check if both lines fit
            line1_width = c.stringWidth(line1, "Helvetica-Bold", font_size)
            line2_width = c.stringWidth(line2, "Helvetica-Bold", font_size)
            
            if line1_width <= available_text_width and line2_width <= available_text_width:
                c.drawString(text_start_x, code_y + 0.05 * inch, line1)
                c.drawString(text_start_x, code_y - 0.05 * inch, line2)
            else:
                # Last resort: truncate
                max_chars = int(len(reg_code) * available_text_width / text_width) - 3
                truncated_code = reg_code[:max_chars] + "..."
                c.drawString(text_start_x, code_y, truncated_code)
    
    # Save PDF
    c.save()

def generate_label(device_input, output_path, width_inches=2.625, height_inches=1.0, username='admin', password='123456'):
    """
    Generate a PDF label with QR code and registration code.
    
    Args:
        device_input: Either an IP address or registration code
        output_path: Path where the PDF should be saved
        width_inches: Label width in inches (default: 2.625)
        height_inches: Label height in inches (default: 1.0)
        username: Username for API calls (default: 'admin')
        password: Password for API calls (default: '123456')
    
    Returns:
        str: The output_path if successful, None if failed
    """
    
    # Determine if input is IP address or registration code
    if is_ip_address(device_input):
        print("Detected IP address - fetching data from device...")
        qr_svg, reg_code = fetch_device_data(device_input, username, password)
        
        if not qr_svg or not reg_code:
            print("Failed to fetch device data.")
            return None
        
        print(f"Registration code: {reg_code}")
        
    elif is_registration_code(device_input):
        print("Detected registration code - generating QR code...")
        reg_code = device_input
        print(f"Using registration code: {reg_code}")
        
    else:
        print("Error: Input must be either a valid IP address or registration code")
        return None
    
    # Generate PDF label
    try:
        create_pdf_label(reg_code, None, output_path, width_inches, height_inches)
        print(f"PDF label saved as: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate device registration label PDF with QR code')
    parser.add_argument('input', help='Device IP address or registration code')
    parser.add_argument('--username', '-u', default='admin', help='Username for API (default: admin)')
    parser.add_argument('--password', '-p', default='123456', help='Password for API (default: 123456)')
    parser.add_argument('--output', '-o', default='device_label.pdf', help='Output filename (default: device_label.pdf)')
    parser.add_argument('--width', '-w', type=float, default=2.625, help='Label width in inches (default: 2.625)')
    parser.add_argument('--height', '-ht', type=float, default=1.0, help='Label height in inches (default: 1.0)')
    
    args = parser.parse_args()
    
    print(f"Input: {args.input}")
    print(f"Label dimensions: {args.width}\" x {args.height}\"")
    
    # Generate PDF label using the new function
    print("Generating PDF label...")
    result = generate_label(
        args.input, 
        args.output, 
        args.width, 
        args.height, 
        args.username, 
        args.password
    )
    
    if result:
        print(f"Label size: {args.width}\" x {args.height}\"")
    else:
        print("Failed to generate label.")
        sys.exit(1)

if __name__ == "__main__":
    main()
