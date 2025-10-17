from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import uuid
import os
import re 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email Configuration
EMAIL_HOST = "smtp.gmail.com"  # o kung ano ang SMTP mo
EMAIL_PORT = 587
EMAIL_USER = "brgybaritan1@gmail.com"  
EMAIL_PASSWORD = "dszmuxiixxlhmhns" 

# Base URL for emails (fallback to local). When running behind a domain, request.host_url will be used automatically.
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000/")

def build_external_url(path: str) -> str:
    """Return an absolute URL for emails. Prefers Flask request.host_url when available.
    path: e.g. 'signin' or '/signin'
    """
    try:
        from flask import request
        host = getattr(request, 'host_url', None)
        if host:
            base = host
        else:
            base = BASE_URL
    except Exception:
        base = BASE_URL
    # normalize slashes
    if not base.endswith('/'):
        base += '/'
    if path.startswith('/'):
        path = path[1:]
    return base + path

app = Flask(__name__)
app.secret_key = os.urandom(24) 

# Constants
SUPABASE_URL = "https://vehpeqlxmucsgasedcuh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZlaHBlcWx4bXVjc2dhc2VkY3VoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjYxNjIyMiwiZXhwIjoyMDcyMTkyMjIyfQ.Xp5JiKtJVPMfZR1ethvOwguVBwjbIYKapi-1STLLfd8"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Helper functions: defective stored in inventory.description ---
def _to_int(val, default=0):
    try:
        if val is None:
            return default
        if isinstance(val, str):
            s = val.strip()
            if s == "":
                return default
            return int(s)
        return int(val)
    except Exception:
        return default
def parse_defective_from_description(desc: str) -> int:
    try:
        if not desc:
            return 0
        # Look for patterns like 'defective:10' or '[DEFECTIVE=10]'
        m = re.search(r"(?:defective\s*[:=]\s*)(\d+)", desc, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))
        return 0
    except Exception:
        return 0

def set_defective_in_description(desc: str, value: int) -> str:
    try:
        value = max(int(value), 0)
        if not desc:
            return f"defective:{value}"
        if re.search(r"defective\s*[:=]\s*\d+", desc, flags=re.IGNORECASE):
            return re.sub(r"defective\s*[:=]\s*\d+", f"defective:{value}", desc, flags=re.IGNORECASE)
        # If description exists but has no defective tag, append neatly
        joiner = "\n" if not desc.endswith("\n") else ""
        return f"{desc}{joiner}defective:{value}"
    except Exception:
        return desc or f"defective:{value}"



# Helper functions
def validate_email_format(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_password_strength(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long!"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least 1 uppercase letter!"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least 1 lowercase letter!"
    if not re.search(r"\d", password):
        return "Password must contain at least 1 number!"
    return None

def get_user_by_email(email):
    return supabase.table("users").select("*").eq("email", email).execute()

def get_user_by_barangay_id(bid):
    return supabase.table("users").select("*").eq("barangay_id", bid).execute()
def get_user_by_id(user_id):
    return supabase.table("users").select("*").eq("id", user_id).limit(1).execute()

# Ticket numbering reset start (fixed)
RESET_FROM_ISO = "2025-10-12T00:00:00"

# Lightweight API: check if email exists (for realtime validation)
@app.get('/api/check_email')
def api_check_email():
    email = request.args.get('email', '').strip().lower()
    if not email or not validate_email_format(email):
        return jsonify({"ok": False, "exists": False, "error": "Invalid email format."}), 400
    try:
        res = get_user_by_email(email)
        exists = bool(res.data)
        return jsonify({"ok": True, "exists": exists})
    except Exception as e:
        print(f"/api/check_email error: {e}")
        return jsonify({"ok": False, "exists": False, "error": "Server error."}), 500

# --- NEW: Notification Helper Function ---
def create_notification(user_id, message, booking_id=None, borrowed_item_id=None, admin_only=False, link=None):
    try:
        # If no link is provided but we have a booking_id, create a link to the booking details
        if not link and booking_id:
            if admin_only:
                link = f"/admin/booking/{booking_id}"  # Admin view
            else:
                link = f"/booking_details/{booking_id}"  # User view
        
        notification_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "message": message,
            "booking_id": booking_id,
            "borrowed_item_id": borrowed_item_id,
            "admin_only": admin_only,
            "link": link,
            "is_read": False,
            "created_at": datetime.now().isoformat()
        }
        supabase.table("notifications").insert(notification_data).execute()
        return True
    except Exception as e:
        print(f"Error creating notification: {e}")
        return False
    
def get_email_template(
    status,
    user_first_name,
    ticket_number,
    event_date=None,
    event_type=None,
    reason=None,
    link=None,
    booking_date=None,
    equipment=None,
    contact_number=None,
    email_address=None,
    status_override=None,
    notes=None,
    full_name=None,
    barangay_id=None,
    address_text=None,
    date_joined=None,
    suspended_since=None,
):
    """
    Returns a beautiful, email-compatible HTML template using inline styles only.
    All variables preserved as-is: {user_first_name}, {ticket_number}, {event_date}, etc.
    Center-aligned for maximum visual harmony and professionalism.
    """
    
    # Define status-based configurations
    status_config = {
        'pending': {
            'gradient': '#023e8a',
            'emoji': '⏳',
            'title': 'Booking Pending',
            'badge_bg': '#e3f2fd',
            'badge_color': '#1976d2',
            'message': "Thank you for your booking request! We are currently reviewing your reservation.",
            'footer': "You will receive another email once your booking is approved or rejected."
        },
        'approved': {
            'gradient': '#023e8a',
            'emoji': '✅',
            'title': 'Booking Approved',
            'badge_bg': '#d1f7c4',
            'badge_color': '#27ae60',
            'message': "Great news! Your booking request has been <strong>approved</strong>.",
            'footer': "You may now proceed with your plans. Thank you for using our booking system!"
        },
        'borrowed': {
            'gradient': '#023e8a',
            'emoji': '🚚',
            'title': 'In Progress',
            'badge_bg': '#e0f2fe',
            'badge_color': '#0284c7',
            'message': "Your booking is now <strong>In Progress</strong>. Items have been released.",
            'footer': "Please return the items on time and in good condition."
        },
        'rejected': {
            'gradient': '#023e8a',
            'emoji': '❌',
            'title': 'Booking Rejected',
            'badge_bg': '#ffcdd2',
            'badge_color': '#c0392b',
            'message': "We're sorry, but your booking request has been <strong>rejected</strong>.",
            'footer': "Thank you for your understanding."
        },
        'cancelled': {
            'gradient': '#023e8a',
            'emoji': '⚠️',
            'title': 'Booking Cancelled',
            'badge_bg': '#ffeaa7',
            'badge_color': '#d35400',
            'message': "Your booking has been successfully <strong>cancelled</strong>.",
            'footer': "If this was a mistake, please create a new booking."
        },
        'suspended': {
            'gradient': '#023e8a',
            'emoji': '🚫',
            'title': 'Account Suspended',
            'badge_bg': '#ffe4e6',
            'badge_color': '#dc2626',
            'message': "Your account has been <strong>suspended</strong> by an administrator.",
            'footer': "If you believe this is a mistake, please contact support."
        },
        'completed': {
            'gradient': '#023e8a',
            'emoji': '✔️',
            'title': 'Booking Completed',
            'badge_bg': '#dcfce7',
            'badge_color': '#16a34a',
            'message': "Your booking has been <strong>completed</strong>. Thank you!",
            'footer': "We appreciate your cooperation."
        },
        'unsuspended': {
            'gradient': '#023e8a',
            'emoji': '✅',
            'title': 'Your account is unsuspended',
            'badge_bg': '#d1f7c4',
            'badge_color': '#27ae60',
            'message': "Your account has been <strong>unsuspended</strong>. You may now sign in again.",
            'footer': "If you encounter issues, please contact support."
        }
    }
    
    # Get config for current status or use default
    config = status_config.get(status, {
        'gradient': '#023e8a',
        'emoji': 'ℹ️',
        'title': 'Booking Update',
        'badge_bg': '#f0f0f0',
        'badge_color': '#555',
        'message': "Your booking status has been updated.",
        'footer': ""
    })
    
    # Build optional rows
    details_title = 'Booking Details'
    if status in ('suspended', 'unsuspended'):
        details_title = 'Account Details'
    event_type_row = ""
    if event_type is not None:
        event_type_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Event Type:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{event_type or "N/A"}</td>
        </tr>'''
    
    event_date_row = ""
    if event_date is not None:
        event_date_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Event Date:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{event_date or "N/A"}</td>
        </tr>'''
    booking_date_row = ""
    if booking_date is not None:
        booking_date_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Booking Date:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{booking_date or "N/A"}</td>
        </tr>'''
    equipment_row = ""
    if equipment is not None:
        equipment_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left; vertical-align: top;">Equipment:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500; white-space: pre-wrap;">{equipment or "N/A"}</td>
        </tr>'''
    contact_row = ""
    if contact_number is not None:
        contact_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Contact Number:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{contact_number or "N/A"}</td>
        </tr>'''
    email_row = ""
    if email_address is not None:
        email_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Email:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{email_address or "N/A"}</td>
        </tr>'''
    status_row = ""
    if status_override is not None:
        status_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Status:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{status_override or (status.upper())}</td>
        </tr>'''
    
    reason_row = ""
    if status in ("rejected", "suspended", "cancelled"):
        reason_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Reason:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{reason or "Please contact the administrator for more information."}</td>
        </tr>'''
    notes_row = ""
    if status == "suspended" and (notes is not None):
        notes_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Notes:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500; white-space: pre-wrap;">{notes or ""}</td>
        </tr>'''

    # Account-specific optional rows
    full_name_row = ""
    if full_name is not None:
        full_name_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Name:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{full_name or "N/A"}</td>
        </tr>'''
    barangay_row = ""
    if barangay_id is not None:
        barangay_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Barangay ID:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{barangay_id or "N/A"}</td>
        </tr>'''
    address_row = ""
    if address_text is not None:
        address_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Address:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500; white-space: pre-wrap;">{address_text or "N/A"}</td>
        </tr>'''
    joined_row = ""
    if date_joined is not None:
        joined_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Date Joined:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{date_joined or "N/A"}</td>
        </tr>'''
    suspended_since_row = ""
    if suspended_since is not None:
        suspended_since_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Suspended Since:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{suspended_since or "N/A"}</td>
        </tr>'''

    # Optional Ticket row (hide for non-booking emails)
    ticket_row = ""
    if ticket_number is not None and str(ticket_number).strip() != "":
        ticket_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Ticket ID:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{ticket_number}</td>
        </tr>'''

    # Build button only for non-account notices
    show_button = status not in ('suspended', 'unsuspended')
    if show_button:
        button_html = f'''
                <!-- Action Button (Bulletproof) -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 30px auto; max-width: 220px;">
                    <tr>
                        <td align="center" style="background-color: #023e8a; border-radius: 6px; text-align: center; border: 2px solid #023e8a;">
                            <a href="{build_external_url(link or 'signin')}" 
                               style="display: block; padding: 14px 20px; color: white; text-decoration: none; font-weight: 600; font-size: 16px; letter-spacing: 0.5px; border-radius: 50px;">
                                View Booking Details
                            </a>
                        </td>
                    </tr>
                </table>'''
    else:
        button_html = ''

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Booking Update</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; color: #333;">
    <!-- Main Email Container -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <!-- Header (DYNAMIC BASED ON STATUS) -->
        <tr>
            <td style="padding: 30px; text-align: center; background: {config['gradient']}; color: white;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600;">
                    {config['emoji']} {config['title']}
                </h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Court & Equipment Booking System</p>
            </td>
        </tr>

        <!-- Content -->
        <tr>
            <td style="padding: 30px; color: #333; line-height: 1.7; text-align: center;">
                <h2 style="color: #023e8a; margin-top: 0; font-size: 20px;">Hello {user_first_name}!</h2>

                <!-- Status Badge -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 20px auto; max-width: 250px;">
                    <tr>
                        <td style="background-color: {config['badge_bg']}; color: {config['badge_color']}; padding: 10px 20px; border-radius: 20px; font-weight: 600; text-transform: uppercase; font-size: 14px; text-align: center;">
                            {status.upper()}
                        </td>
                    </tr>
                </table>

                <!-- Message -->
                <p style="margin: 20px 0; font-size: 16px; line-height: 1.6;">
                    {config['message']}
                </p>

                <!-- Details Card -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8f9fa; border-radius: 8px; overflow: hidden; margin: 25px auto; border: 1px solid #e9ecef; max-width: 500px;">
                    <tr>
                        <td style="padding: 20px; text-align: left;">
                            <h3 style="color: #023e8a; margin: 0 0 15px 0; font-size: 18px; text-align: center;">{details_title}</h3>
                            
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                {ticket_row}
                                {event_type_row}
                                {event_date_row}
                                {booking_date_row}
                                {equipment_row}
                                {contact_row}
                                {email_row}
                                {status_row}
                                {reason_row}
                                {notes_row}
                                {full_name_row}
                                {barangay_row}
                                {address_row}
                                {joined_row}
                                {suspended_since_row}
                            </table>
                        </td>
                    </tr>
                </table>

                {button_html}

                <!-- Footer Text -->
                <p style="margin: 30px 0 15px 0; font-size: 15px; color: #666; line-height: 1.6;">
                    {config['footer']}
                </p>
            </td>
        </tr>

        <!-- Footer -->
        <tr>
            <td style="padding: 20px; text-align: center; color: #7f8c8d; font-size: 14px; background-color: #f8f9fa;">
                <p style="margin: 0;">&copy; 2025 Barangay Baritan Malabon | 
                    <a href="mailto:Baritan.Malabonkmgs@gmail.com" style="color: #022e6a; text-decoration: none; font-weight: 500;">Contact Us</a>
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
    """
    return html
def get_password_reset_email_template(user_first_name, reset_link):
    """
    Returns a beautiful HTML email template for password reset.
    """
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; color: #333;">
    <!-- Main Email Container -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <!-- Header -->
        <tr>
            <td style="padding: 30px; text-align: center; background: #023e8a; color: white;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600;">
                    🔐 Password Reset Request
                </h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Court & Equipment Booking System</p>
            </td>
        </tr>

        <!-- Content -->
        <tr>
            <td style="padding: 30px; color: #333; line-height: 1.7; text-align: center;">
                <h2 style="color: #023e8a; margin-top: 0; font-size: 20px;">Hello {user_first_name}!</h2>

                <!-- Message -->
                <p style="margin: 20px 0; font-size: 16px; line-height: 1.6;">
                    We received a request to reset your password. If you didn't make this request, you can safely ignore this email.
                </p>

                <p style="margin: 20px 0; font-size: 16px; line-height: 1.6;">
                    To reset your password, click the button below. This link will expire in 24 hours for security reasons.
                </p>

                <!-- Reset Button -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 30px auto; max-width: 250px;">
                    <tr>
                        <td align="center" style="background-color: #023e8a; border-radius: 6px; text-align: center; border: 2px solid #023e8a;">
                            <a href="{reset_link}" 
                               style="display: block; padding: 14px 20px; color: white; text-decoration: none; font-weight: 600; font-size: 16px; letter-spacing: 0.5px; border-radius: 6px;">
                                Reset My Password
                            </a>
                        </td>
                    </tr>
                </table>

                <!-- Alternative Link -->
                <p style="margin: 30px 0 15px 0; font-size: 14px; color: #666; line-height: 1.6;">
                    If the button doesn't work, copy and paste this link into your browser:
                </p>
                <p style="margin: 0 0 20px 0; font-size: 14px; color: #023e8a; word-break: break-all;">
                    {reset_link}
                </p>

                <!-- Security Notice -->
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: left;">
                    <p style="margin: 0; font-size: 14px; color: #856404;">
                        <strong>Security Notice:</strong> This password reset link will expire in 24 hours. If you didn't request this reset, please contact our support team immediately.
                    </p>
                </div>
            </td>
        </tr>

        <!-- Footer -->
        <tr>
            <td style="padding: 20px; text-align: center; color: #7f8c8d; font-size: 14px; background-color: #f8f9fa;">
                <p style="margin: 0;">&copy; 2025 Barangay Baritan Malabon | 
                    <a href="mailto:Baritan.Malabonkmgs@gmail.com" style="color: #022e6a; text-decoration: none; font-weight: 500;">Contact Us</a>
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
    """
    return html

def send_email_notification(to_email, subject, message):
    """
    Sends an email notification to the specified email address.
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'html'))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, to_email, text)
        server.quit()

        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False



@app.route("/")
def home():
    return render_template("index.html")

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'GET':
        return render_template("signup.html", form={})
    
    # Process POST request
    fname = request.form['first_name']
    lname = request.form['last_name']
    bid = request.form['barangay_id']
    email = request.form['email']
    password = request.form["password"]
    confirm = request.form['confirm_password']
    address = request.form['address']

    form_data = {
        "first_name": fname,
        "last_name": lname,
        "barangay_id": bid,
        "email": email,
        "address": address
    }

    # Validation
    if not validate_email_format(email):
        flash("Invalid email address!", "error")
        return render_template("signup.html", form=form_data)
    
    if password_error := validate_password_strength(password):
        flash(password_error, "error")
        return render_template("signup.html", form=form_data)
    
    if len(fname) < 2 or len(lname) < 2:
        flash("First and last name must be at least 2 characters!", "error")
        return render_template("signup.html", form=form_data)

    if len(address) < 5:
        flash("Address is too short!", "error")
        return render_template("signup.html", form=form_data)

    if password != confirm:
        flash("Passwords do not match!", "error")
        return render_template("signup.html", form=form_data)
    
    # Check for existing users
    if get_user_by_email(email).data:
        flash("Email already exists!", "error")
        return render_template("signup.html", form=form_data)

    if get_user_by_barangay_id(bid).data:
        flash("Barangay ID already exists!", "error")
        return render_template("signup.html", form=form_data)

    # Create user
    hashed_password = generate_password_hash(password)

    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        if auth_response.user:
            supabase.table("users").insert({
                "id": str(auth_response.user.id),
                "first_name": fname,
                "last_name": lname,
                "barangay_id": bid,
                "email": email,
                "password": hashed_password,
                "address": address,
                "role": "user",
                "is_verified": False
            }).execute()

            flash("Account created! Please check your email and verify before signing in.", "success")
            return redirect(url_for("signin"))

    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            flash("Email already exists!", "error")
        else:
            flash(f"Registration failed: {error_msg}", "error")
        return render_template("signup.html", form=form_data)

@app.route("/verify_success")
def verify_success():
    user_id = request.args.get("id")
    if user_id:
        supabase.table("users").update({"is_verified": True}).eq("id", user_id).execute()
    return render_template("verify_success.html")

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'GET':
        return render_template("signin.html")
    
    # Process POST request
    email = request.form['email'].strip()
    password = request.form['password']

    # Validate email format
    if not validate_email_format(email):
        flash("Invalid email format!", "error")
        return redirect(url_for("signin"))

    try:
        # First, try to authenticate with Supabase Auth
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # If we get here, Supabase auth succeeded
            user_data = None
            
            # Try to get user from custom table
            user_query = get_user_by_email(email)
            if user_query.data:
                user_data = user_query.data[0]
            
            # Determine Supabase verification state and sync to custom table if needed
            supa_user = getattr(auth_response, 'user', None)
            supa_verified = False
            try:
                # Supabase user may have email_confirmed_at or confirmed_at
                if supa_user is not None:
                    supa_verified = bool(getattr(supa_user, 'email_confirmed_at', None) or getattr(supa_user, 'confirmed_at', None))
            except Exception:
                supa_verified = False
            
            # If Supabase says verified but our table says not, update our table to verified
            if supa_verified and user_data and not user_data.get('is_verified', False):
                try:
                    supabase.table("users").update({"is_verified": True}).eq("email", email).execute()
                    user_data['is_verified'] = True
                except Exception:
                    pass
            
            # Block login if neither Supabase nor our table indicates verification
            if (not supa_verified) and user_data and not user_data.get('is_verified', False):
                try:
                    supabase.auth.sign_out()
                except Exception:
                    pass
                flash("Please verify your email first before signing in.", "error")
                return redirect(url_for("signin"))
            
            # If user exists in custom table, update their password hash
            if user_data:
                hashed_password = generate_password_hash(password)
                supabase.table("users").update({"password": hashed_password}).eq("email", email).execute()
            
            # Set session
            session['user'] = {
                'id': user_data['id'] if user_data else str(uuid.uuid4()),
                'email': email,
                'first_name': user_data['first_name'] if user_data else 'User',
                'role': user_data['role'] if user_data else 'user'
            }

            # If account is suspended (non-admin), continue login; booking page will display suspended notice

            flash("Login successful!", "success")
            if user_data and user_data.get('role') == 'admin':
                return redirect(url_for('admin_portal'))
            return redirect(url_for('booking'))
            
        except Exception as auth_error:
            print(f"Supabase auth error: {str(auth_error)}")
            # If Supabase auth fails, fall back to custom table check
            user_query = get_user_by_email(email)
            if not user_query.data:
                flash("Email not registered!", "error")
                return redirect(url_for("signin"))

            user_data = user_query.data[0]

            # Check password in custom table
            if not check_password_hash(user_data["password"], password):
                flash("Incorrect password!", "error")
                return redirect(url_for("signin"))

            # Block login if email not verified in our users table (fallback path)
            if not user_data.get('is_verified', False):
                flash("Please verify your email first before signing in.", "error")
                return redirect(url_for("signin"))

            # Set session
            session['user'] = {
                'id': user_data['id'],
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'role': user_data['role']
            }

            # If account is suspended (non-admin), continue login; booking page will display suspended notice

            flash("Login successful!", "success")
            if user_data['role'] == 'admin':
                return redirect(url_for('admin_portal'))
            return redirect(url_for('booking'))

    except Exception as e:
        print(f"Login error: {str(e)}")
        flash("Login failed. Please check your credentials and try again.", "error")
        return redirect(url_for("signin"))


@app.route("/booking")
def booking():
    if "user" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("signin"))
    
    user_id = session["user"]["id"]

    # Get user info
    user_data = supabase.table("users").select("*").eq("id", user_id).execute()
    user = user_data.data[0] if user_data.data else None

    # If suspended (non-admin), render booking page with suspension context
    suspended = bool(user and user.get('role') != 'admin' and user.get('is_suspended', False))
    # Prefer new column suspend_notes, fallback to legacy suspend_reason
    suspend_notes = (user.get('suspend_notes') or None) if user else None
    suspend_reason = (user.get('suspend_reason') or suspend_notes or 'No reason provided') if user else None

    # Helper function to parse other_items string
    def parse_other_items(items_str):
        if not items_str:
            return []
        items = []
        for item_str in items_str.split(", "):
            if " x" in item_str:
                name, qty_str = item_str.rsplit(" x", 1)
                try:
                    quantity = int(qty_str)
                    items.append({
                        "name": name.strip(),
                        "quantity": quantity
                    })
                except ValueError:
                    continue
        return items

    # My Bookings: Pending, Approved, or Borrowed (sorted by created_at in descending order - newest first)
    bookings_data = supabase.table("bookings") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("status", ["Pending", "Approved", "Borrowed"]) \
        .order("created_at", desc=True) \
        .execute()
    bookings = bookings_data.data if bookings_data.data else []

    for booking in bookings:
        booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))

    # Booking History (sorted by created_at in descending order - newest first)
    history_data = supabase.table("bookings") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("status", ["Completed", "Cancelled", "Rejected"]) \
        .order("created_at", desc=True) \
        .execute()
    booking_history = history_data.data if history_data.data else []

    for booking in booking_history:
        booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
    
    # ✅ FIXED: Simplified unread count - TANGGALIN ANG last_notif_read_at
    try:
        unread_notif_data = supabase.table("notifications") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("is_read", False) \
            .execute()
        unread_count = len(unread_notif_data.data) if unread_notif_data.data else 0
    except Exception as e:
        print(f"Error getting unread count: {e}")
        unread_count = 0

    # ✅ FIXED: Get recent notifications list
    notifications_data = supabase.table("notifications") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()
    notifications = notifications_data.data if notifications_data.data else []

    return render_template(
        "booking.html", 
        user=user, 
        bookings=bookings, 
        booking_history=booking_history,
        unread_count=unread_count,
        notifications=notifications,
        suspended=suspended,
        suspend_reason=suspend_reason,
        suspend_notes=suspend_notes
    )

@app.route("/booking_details/<booking_id>")
def booking_details(booking_id):
    if "user" not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "Please login first"}), 401
        flash("Please login first!", "error")
        return redirect(url_for("signin"))
    
    try:
        # Check if user is admin
        is_admin = session.get("user", {}).get("role") == "admin"
        
        # Build the query to include user info
        query = supabase.table("bookings").select("*, users(first_name, last_name, barangay_id)")
        
        # Add conditions based on user role
        if is_admin:
            query = query.eq("id", booking_id)
        else:
            query = query.eq("id", booking_id).eq("user_id", session["user"]["id"])
        
        # Execute the query
        booking_data = query.execute()
        
        if not booking_data.data:
            return jsonify({"success": False, "message": "Booking not found"}), 404
        
        booking = booking_data.data[0]

        # Kunin ang listahan ng lahat ng active equipment para i-map (kasama na ang category_id)
        try:
            equipment_data = supabase.table("inventory").select("id, name, category_id").eq("is_active", True).execute()
            # Gumawa ng map: name → category_id (para sa matching)
            name_to_category = {item['name']: item['category_id'] for item in equipment_data.data} if equipment_data.data else {}
        except Exception as e:
            name_to_category = {}
            print(f"Error fetching equipment map: {e}")

        # I-decode ang other_items field at i-assign ang category_id
        equipment_list = []
        if booking.get("other_items"):
            for item_str in booking["other_items"].split(", "):
                if " x" in item_str:
                    name_part, qty_str = item_str.rsplit(" x", 1)
                    name = name_part.strip()  # Important: i-strip para walang space
                    try:
                        qty = int(qty_str)
                        # Hanapin ang category_id base sa name
                        category_id = name_to_category.get(name, "cat6")  # Default: cat6 (Other)
                        equipment_list.append({
                            "name": name,
                            "quantity": qty,
                            "category_id": category_id  # ✅ Ito ang idinagdag para sa JS emoji logic
                        })
                    except ValueError:
                        continue

        # I-override ang booking data para isama ang decoded equipment (kasama category_id)
        booking["equipment_list"] = equipment_list
        
        # If snapshot query params are present (from notification link), include them in the response
        try:
            status_at_time = request.args.get('status_at_time')
            cancel_reason_qs = request.args.get('cancel_reason')
            if status_at_time:
                booking["status_snapshot"] = status_at_time
            if cancel_reason_qs:
                booking["cancel_reason_snapshot"] = cancel_reason_qs
        except Exception:
            pass

        # Mark notification as read if coming from notification
        if request.args.get('from_notification'):
            try:
                notification_id = request.args.get('notification_id')
                if notification_id:
                    supabase.table("notifications") \
                        .update({"is_read": True}) \
                        .eq("id", notification_id) \
                        .eq("user_id", session["user"]["id"]) \
                        .execute()
            except Exception as e:
                print(f"Error marking notification as read: {e}")

        # Always return JSON response
        return jsonify({"success": True, "data": booking})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.get('/get_unread_count')
def get_unread_count():
    """Return unread notifications count for the logged-in user."""
    if "user" not in session:
        return jsonify({"success": False, "unread_count": 0}), 401

    try:
        user_id = session["user"]["id"]
        # ✅ SIMPLIFIED: Direct count without timestamp dependency
        res = supabase.table("notifications") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("is_read", False) \
            .execute()
        count = len(res.data) if res.data else 0
        return jsonify({"success": True, "unread_count": count})
    except Exception as e:
        print(f"/get_unread_count error: {e}")
        return jsonify({"success": False, "unread_count": 0}), 500


@app.post('/mark_notifications_as_read')
def mark_notifications_as_read():
    """Mark all notifications as read for the logged-in user."""
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401

    try:
        user_id = session["user"]["id"]
        # ✅ Mark unread notifications as read - TANGGALIN ANG last_notif_read_at
        supabase.table("notifications") \
            .update({"is_read": True}) \
            .eq("user_id", user_id) \
            .eq("is_read", False) \
            .execute()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"/mark_notifications_as_read error: {e}")
        return jsonify({"success": False}), 500


@app.get('/api/approved_dates')
def api_approved_dates():
    """Return list of dates (YYYY-MM-DD) that already have Approved bookings.
    Filter by type: type=equipment -> event_type == 'Equipment Booking';
    type=court -> event_type != 'Equipment Booking'.
    """
    try:
        btype = (request.args.get('type') or 'court').strip().lower()
        base = supabase.table("bookings").select("event_date").eq("status", "Approved")
        if btype == 'equipment':
            query = base.eq("event_type", "Equipment Booking")
        else:
            query = base.neq("event_type", "Equipment Booking")
        res = query.execute()
        dates = sorted({row.get('event_date') for row in (res.data or []) if row.get('event_date')})
        return jsonify({"success": True, "dates": dates})
    except Exception as e:
        print(f"/api/approved_dates error: {e}")
        return jsonify({"success": False, "dates": []}), 500

@app.post('/mark_notification_as_read')
def mark_notification_as_read():
    """Mark a single notification as read for the logged-in user."""
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401

    try:
        data = request.get_json(silent=True) or {}
        notif_id = data.get('notification_id')
        if not notif_id:
            return jsonify({"success": False, "message": "notification_id required"}), 400

        user_id = session["user"]["id"]
        supabase.table("notifications").update({"is_read": True}).eq("id", notif_id).eq("user_id", user_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"/mark_notification_as_read error: {e}")
        return jsonify({"success": False}), 500

@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first!"})
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        cancel_reason = (data.get('cancel_reason') or '').strip()
        
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"})
        if not cancel_reason:
            return jsonify({"success": False, "message": "Cancellation reason is required"}), 400
        
        # Get previous status and items BEFORE updating
        prev_info = supabase.table("bookings").select("status, other_items").eq("id", booking_id).eq("user_id", session["user"]["id"]).limit(1).execute()
        prev_status = (prev_info.data or [{}])[0].get("status") if prev_info.data else None
        other_items_before = (prev_info.data or [{}])[0].get("other_items", "") if prev_info.data else ""

        # Update status to Cancelled instead of deleting
        supabase.table("bookings") \
            .update({
                "status": "Cancelled",
                "cancel_reason": cancel_reason,
                "cancelled_at": datetime.now().isoformat(),
                "cancelled_by": session["user"]["id"]
            }) \
            .eq("id", booking_id) \
            .eq("user_id", session["user"]["id"]) \
            .execute()
        
        # --- UPDATED: Restore inventory ONLY if previously Approved or Borrowed ---
        try:
            if prev_status in ("Approved", "Borrowed"):
                other_items_str = other_items_before

                # Parse items: Format "Name xQTY, Name2 xQTY2"
                items = []
                if other_items_str:
                    for item_str in other_items_str.split(", "):
                        if " x" in item_str:
                            name_part, qty_str = item_str.rsplit(" x", 1)
                            try:
                                items.append({"name": name_part.strip(), "quantity": int(qty_str)})
                            except ValueError:
                                continue

                if items:
                    # Map inventory by name
                    inv_data = supabase.table("inventory").select("id, name, quantity_available").execute()
                    name_to_item = {row["name"]: row for row in (inv_data.data or [])}

                    for it in items:
                        inv_row = name_to_item.get(it["name"])  # Only restore if the name exists in inventory
                        if inv_row:
                            new_av = int(inv_row.get("quantity_available", 0)) + int(it["quantity"])
                            supabase.table("inventory").update({"quantity_available": new_av}).eq("id", inv_row["id"]).execute()
        except Exception as inv_restore_err:
            print(f"Warning: Failed to restore inventory on cancel: {inv_restore_err}")

        # Kunin ang email at name ng user
        user_data = supabase.table("users").select("email, first_name, last_name").eq("id", session["user"]["id"]).execute()
        if user_data.data:
            user_email = user_data.data[0]['email']
            user_first_name = user_data.data[0]['first_name']
            user_last_name = user_data.data[0].get('last_name') or ''
            user_full_name = f"{user_first_name} {user_last_name}".strip()

        # Kunin ang event_date, ticket_number at iba pang detalye mula sa booking
        booking_data = supabase.table("bookings").select("event_date, ticket_number, other_items, contact_number, email, created_at").eq("id", booking_id).execute()
        event_date = None
        ticket_number = None
        other_items_str = None
        booking_contact = None
        booking_email = None
        booking_created_at = None
        if booking_data.data:
            row = booking_data.data[0]
            event_date = row.get('event_date')
            ticket_number = row.get('ticket_number')
            other_items_str = row.get('other_items')
            booking_contact = row.get('contact_number')
            booking_email = row.get('email')
            booking_created_at = row.get('created_at')

        # --- Create Notification for User (use Ticket Number in message) ---
        cancel_link = url_for('booking_details', booking_id=booking_id)
        create_notification(
            user_id=session["user"]["id"],
            message=f"Your booking (Ticket: {ticket_number}) has been cancelled. Reason: {cancel_reason}",
            booking_id=booking_id,
            link=cancel_link
        )

        # Magpadala ng tamang datos sa email (with reason and more details)
        send_email_notification(
            to_email=user_email,
            subject="⚠️ Booking Cancelled",
            message=get_email_template(
                status="cancelled",
                user_first_name=user_first_name,
                ticket_number=ticket_number,
                event_date=event_date,
                reason=cancel_reason,
                link=f"booking_details/{booking_id}",
                booking_date=booking_created_at,
                equipment=other_items_str,
                contact_number=booking_contact,
                email_address=user_email,
                status_override="Cancelled"
            )
        )
        
        # Notify all admins with the cancel reason and link to admin booking details
        try:
            admins = supabase.table("users").select("id").eq("role", "admin").execute()
            if admins.data:
                for adm in admins.data:
                    create_notification(
                        user_id=adm["id"],
                        message=f"{user_full_name or 'A user'} cancelled booking {ticket_number}. Reason: {cancel_reason}",
                        booking_id=booking_id,
                        admin_only=True,
                        link=url_for('admin_booking_details', booking_id=booking_id)
                    )
        except Exception as anerr:
            print(f"Warning: admin cancel notifications failed: {anerr}")
        
        return jsonify({"success": True, "message": "Booking cancelled successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/booking2", methods=["GET"])
def booking2_page():
    if "user" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("signin"))
    
    # ✅ ILALAGAY MO ANG CODE DITO ✅
    try:
        equipment_data = supabase.table("inventory").select("*").eq("is_active", True).execute()
        equipment_list = equipment_data.data if equipment_data.data else []

        # I-group ang equipment sa categories
        categories = {
            "cat1": {"name": "🏕️ Tents & Shelters", "items": []},
            "cat2": {"name": "🪑 Furniture", "items": []},
            "cat3": {"name": "🏀 Sports Equipment", "items": []},
            "cat4": {"name": "🎤 Sound Equipment", "items": []},
            "cat5": {"name": "🍳 Cooking Equipment", "items": []},
            "cat6": {"name": "📦 Other Equipment", "items": []}
        }

        for item in equipment_list:
            cat_id = item.get("category_id", "cat6")  # default to "Other"
            if cat_id in categories:
                categories[cat_id]["items"].append(item)
            else:
                categories["cat6"]["items"].append(item)

        # I-filter ang categories na may laman
        active_categories = {k: v for k, v in categories.items() if v["items"]}
    except Exception as e:
        active_categories = {}
        print(f"Error fetching equipment: {e}")

    return render_template("booking2.html", active_categories=active_categories)

@app.route("/booking3", methods=["GET", "POST"])
def booking3():
    if "user" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("signin"))

    if request.method == "GET":
        try:
            equipment_data = supabase.table("inventory").select("*").eq("is_active", True).execute()
            equipment_list = equipment_data.data if equipment_data.data else []

            # I-group ang equipment sa categories
            categories = {
                "cat1": {"name": "🏕️ Tents & Shelters", "items": []},
                "cat2": {"name": "🪑 Furniture", "items": []},
                "cat3": {"name": "🏀 Sports Equipment", "items": []},
                "cat4": {"name": "🎤 Sound Equipment", "items": []},
                "cat5": {"name": "🍳 Cooking Equipment", "items": []},
                "cat6": {"name": "📦 Other Equipment", "items": []}
            }

            for item in equipment_list:
                cat_id = item.get("category_id", "cat6")  # default to "Other"
                if cat_id in categories:
                    categories[cat_id]["items"].append(item)
                else:
                    categories["cat6"]["items"].append(item)

            # I-filter ang categories na may laman
            active_categories = {k: v for k, v in categories.items() if v["items"]}
        except Exception as e:
            active_categories = {}
            print(f"Error fetching equipment: {e}")

        return render_template("booking3.html", active_categories=active_categories)
    
    # Process POST request
    user_id = session["user"]["id"]

    # Check if user already has a pending/approved booking
    existing_booking = supabase.table("bookings") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("status", ["Pending", "Approved"]) \
        .execute()

    if existing_booking.data:
        flash("You already booked! You can't book multiple.", "error")
        return redirect(url_for("booking3"))

    # ✅ Kunin muna ang listahan ng lahat ng active equipment para i-map
    try:
        equipment_data = supabase.table("inventory").select("id, name").eq("is_active", True).execute()
        equipment_map = {item['id']: item['name'] for item in equipment_data.data} if equipment_data.data else {}
    except Exception as e:
        equipment_map = {}
        print(f"Error fetching equipment map: {e}")

    # ✅ I-store ang quantities sa dictionary
    equipment_quantities = {}

    for item_id in equipment_map.keys():
        qty_key = f"{item_id}_qty"  # Hal. "abc123_qty"
        qty = int(request.form.get(qty_key, 0) or 0)
        if qty > 0:
            equipment_quantities[item_id] = {
                "name": equipment_map[item_id],
                "quantity": qty
            }

    # ✅ I-combine ang lahat ng selected equipment (both main list and "other" items)
    all_equipment_list = []

    # Add from main equipment list
    for item_id, info in equipment_quantities.items():
        all_equipment_list.append(f"{info['name']} x{info['quantity']}")

    # Add from "Other Equipment" section
    other_item_name = request.form.get("other_items", "").strip()
    other_qty = int(request.form.get("others_qty", 0) or 0)
    if other_item_name and other_qty > 0:
        all_equipment_list.append(f"{other_item_name} x{other_qty}")

    # ✅ I-combine lahat
    all_other_items = ", ".join(all_equipment_list) if all_equipment_list else ""
    total_others_qty = sum(info['quantity'] for info in equipment_quantities.values()) + (other_qty or 0)

    # Collect form data
    event_date = request.form.get("event_date", "").strip()
    contact_number = request.form.get("phone", "").strip()
    # Always use the logged-in user's email (account email), not from form
    email = session.get('user', {}).get('email', '')
    if not email:
        try:
            user_email_res = supabase.table("users").select("email").eq("id", user_id).execute()
            email = (user_email_res.data[0]["email"] if user_email_res.data else "")
        except Exception:
            email = ""

    # Generate IDs with appropriate ticket number format (4 digits)
    booking_id = str(uuid.uuid4())
    # For equipment bookings (from booking3), use sequential TKT-E{4-digit-number}
    try:
        reset_from = RESET_FROM_ISO
        res = (
            supabase
            .table("bookings")
            .select("ticket_number, created_at")
            .eq("event_type", "Equipment Booking")
            .gte("created_at", reset_from)
            .like("ticket_number", "TKT-E%")
            .order("ticket_number", desc=True)
            .limit(1)
            .execute()
        )
        last_ticket = (res.data[0]["ticket_number"] if res.data else "")
        m = re.match(r"^TKT-E(\d{4})$", last_ticket or "")
        next_num = (int(m.group(1)) + 1) if m else 1
        ticket_number = f"TKT-E{str(next_num).zfill(4)}"
    except Exception:
        ticket_number = "TKT-E0001"

    # ✅ KUNIN ANG USER'S FIRST_NAME AT LAST_NAME MULA SA DATABASE
    try:
        user_response = supabase.table("users").select("first_name, last_name").eq("id", user_id).execute()
        user_data = user_response.data[0] if user_response.data else {}
        user_first_name = user_data.get("first_name", "")
        user_last_name = user_data.get("last_name", "")
    except Exception as e:
        # Kung may error, gamitin ang empty string para hindi mabigong mag-insert
        user_first_name = ""
        user_last_name = ""
        print(f"Error fetching user data: {e}")

    # ✅ Gumamit na ng bagong `all_other_items` at `total_others_qty`
    # ✅ IDINAGDAG NA ANG first_name AT last_name
    booking_data = {
        "id": booking_id,
        "user_id": user_id,
        "ticket_number": ticket_number,
        "first_name": user_first_name,  # ✅ ADDED
        "last_name": user_last_name,   # ✅ ADDED
        "event_type": "Equipment Booking",  # Set event_type for equipment bookings
        "event_date": event_date,
        "contact_number": contact_number,
        "email": email,
        "others_qty": total_others_qty,      # ← ITO ANG TOTAL QUANTITY
        "other_items": all_other_items,      # ← ITO ANG LAHAT NG ITEM DESCRIPTIONS
        "status": "Pending",
        "created_at": datetime.now().isoformat()
    }

    try:
        # --- UPDATED: Validate availability only (no deduction on submission) ---
        if equipment_quantities:
            # Kunin ang current availability para sa lahat ng items na may quantity > 0
            item_ids = list(equipment_quantities.keys())
            inv_resp = supabase.table("inventory").select("id, quantity_available").in_("id", item_ids).execute()
            availability_map = {row["id"]: row["quantity_available"] for row in (inv_resp.data or [])}

            # Validate availability
            insufficient = []
            for iid, info in equipment_quantities.items():
                available = availability_map.get(iid, 0)
                if info["quantity"] > available:
                    insufficient.append(f"{info['name']} (requested {info['quantity']}, available {available})")

            if insufficient:
                flash("Not enough stock for: " + ", ".join(insufficient), "error")
                return redirect(url_for("booking3"))

        # Insert booking with retry on unique ticket_number conflict
        for _ in range(5):
            try:
                # Recompute next ticket just in case of race/conflict
                try:
                    res = (
                        supabase
                        .table("bookings")
                        .select("ticket_number, created_at")
                        .eq("event_type", "Equipment Booking")
                        .gte("created_at", RESET_FROM_ISO)
                        .like("ticket_number", "TKT-E%")
                        .order("ticket_number", desc=True)
                        .limit(1)
                        .execute()
                    )
                    last_ticket = (res.data[0]["ticket_number"] if res.data else "")
                    m = re.match(r"^TKT-E(\d{4})$", last_ticket or "")
                    next_num = (int(m.group(1)) + 1) if m else 1
                    ticket_number = f"TKT-E{str(next_num).zfill(4)}"
                    booking_data["ticket_number"] = ticket_number
                except Exception:
                    # keep existing ticket_number if recompute fails
                    pass
                supabase.table("bookings").insert(booking_data).execute()
                break
            except Exception as insert_err:
                if "bookings_ticket_number_key" in str(insert_err):
                    continue
                raise
        flash(f"Booking submitted successfully! Ticket: {ticket_number}", "success")
        
        # --- NEW: Create Notification for User ---
        # Include snapshot so notification details modal shows Pending even if status changes later
        pending_link = url_for('booking_details', booking_id=booking_id) + "?status_at_time=Pending"
        create_notification(
            user_id=user_id,
            message=f"Your booking request (Ticket: {ticket_number}) has been submitted and is now pending approval.",
            booking_id=booking_id,
            link=pending_link,
        )

        send_email_notification(
            to_email=email,
            subject="⏳ Booking Pending Approval",
            message=get_email_template(
                status="pending",
                user_first_name=user_first_name,
                ticket_number=ticket_number,
                event_date=event_date,
                event_type="Equipment Booking",
                link=f"booking_details/{booking_id}",
                booking_date=booking_data["created_at"],
                equipment=all_other_items,
                contact_number=contact_number,
                email_address=email,
                status_override="Pending"
            )
        )
        
        return redirect(url_for("booking3"))
    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "error")
        return redirect(url_for("booking3"))


@app.route("/book_event", methods=["POST"])
def book_event():
    if "user" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("signin"))

    user_id = session["user"]["id"]

    # Check if user already has a pending or approved booking
    existing_booking = supabase.table("bookings") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("status", ["Pending", "Approved"]) \
        .execute()

    if existing_booking.data:
        flash("You already booked! You can't book multiple.", "error")
        return redirect(url_for("booking2_page"))

    try:
        # Get form data (event info, contact info)
        event_type = request.form.get("event_type", "").strip()
        custom_event_type = request.form.get("custom_event_type", "").strip()
        
        # Use custom event type if "Other" is selected
        if event_type == "other" and custom_event_type:
            event_type = custom_event_type
            
        event_date = request.form.get("event_date", "").strip()
        contact_number = request.form.get("phone", "").strip()
        # Always use the logged-in user's email (account email), not from form
        email = session.get('user', {}).get('email', '')
        if not email:
            try:
                user_email_res = supabase.table("users").select("email").eq("id", user_id).execute()
                email = (user_email_res.data[0]["email"] if user_email_res.data else "")
            except Exception:
                email = ""

        # ✅ Kunin muna ang listahan ng lahat ng active equipment para i-map
        try:
            equipment_data = supabase.table("inventory").select("id, name").eq("is_active", True).execute()
            equipment_map = {item['id']: item['name'] for item in equipment_data.data} if equipment_data.data else {}
        except Exception as e:
            equipment_map = {}
            print(f"Error fetching equipment map: {e}")

        # ✅ I-store ang quantities sa dictionary
        equipment_quantities = {}

        for item_id in equipment_map.keys():
            qty_key = f"{item_id}_qty"  # Hal. "abc123_qty"
            qty = int(request.form.get(qty_key, 0) or 0)
            if qty > 0:
                equipment_quantities[item_id] = {
                    "name": equipment_map[item_id],
                    "quantity": qty
                }

        # ✅ I-combine ang lahat ng selected equipment (both main list and "other" items)
        all_equipment_list = []

        # Add from main equipment list
        for item_id, info in equipment_quantities.items():
            all_equipment_list.append(f"{info['name']} x{info['quantity']}")

        # Add from "Other Equipment" section
        main_other_item = request.form.get("other_items", "").strip()
        main_other_qty = request.form.get("other_qty", "0").strip()
        
        if main_other_item and int(main_other_qty) > 0:
            all_equipment_list.append(f"{main_other_item} x{main_other_qty}")
        
        # Kunin ang mga dynamically added other items
        additional_items = request.form.getlist("other_items[]")
        for item in additional_items:
            if item.strip():  # Kung may laman
                all_equipment_list.append(item.strip())

        # I-combine lahat
        all_other_items = ", ".join(all_equipment_list) if all_equipment_list else ""
        
        # Calculate total others quantity
        others_qty = sum(int(qty) for item in all_equipment_list for qty in item.split('x')[1:] if 'x' in item)

        # Generate IDs with appropriate ticket number format (4 digits)
        booking_id = str(uuid.uuid4())
        # For court bookings (from booking2), use sequential TKT-C{4-digit-number}
        # Determine next ticket by the highest ticket_number within the reset window
        try:
            reset_from = RESET_FROM_ISO
            res = (
                supabase
                .table("bookings")
                .select("ticket_number, created_at")
                .neq("event_type", "Equipment Booking")
                .gte("created_at", reset_from)
                .like("ticket_number", "TKT-C%")
                .order("ticket_number", desc=True)
                .limit(1)
                .execute()
            )
            last_ticket = (res.data[0]["ticket_number"] if res.data else "")
            m = re.match(r"^TKT-C(\d{4})$", last_ticket or "")
            next_num = (int(m.group(1)) + 1) if m else 1
            ticket_number = f"TKT-C{str(next_num).zfill(4)}"
        except Exception:
            ticket_number = "TKT-C0001"

        # ✅ KUNIN ANG USER'S FIRST_NAME AT LAST_NAME MULA SA DATABASE
        try:
            user_response = supabase.table("users").select("first_name, last_name").eq("id", user_id).execute()
            user_data = user_response.data[0] if user_response.data else {}
            user_first_name = user_data.get("first_name", "")
            user_last_name = user_data.get("last_name", "")
        except Exception as e:
            # Kung may error, gamitin ang empty string para hindi mabigong mag-insert
            user_first_name = ""
            user_last_name = ""
            print(f"Error fetching user  {e}")

        # ✅ Gumamit na ng bagong `all_other_items` at `total_others_qty`
        # ✅ IDINAGDAG NA ANG first_name AT last_name
        booking_data = {
            "id": booking_id,
            "user_id": user_id,
            "ticket_number": ticket_number,
            "first_name": user_first_name,  # ✅ ADDED
            "last_name": user_last_name,   # ✅ ADDED
            "event_type": event_type,
            "event_date": event_date,
            "contact_number": contact_number,
            "email": email,
            "others_qty": others_qty,      # ← ITO ANG TOTAL QUANTITY
            "other_items": all_other_items,   # ← ITO ANG LAHAT NG ITEM DESCRIPTIONS
            "status": "Pending",
            "created_at": datetime.now().isoformat()
        }

        # --- UPDATED: Validate availability only (no deduction on submission) ---
        if equipment_quantities:
            item_ids = list(equipment_quantities.keys())
            inv_resp = supabase.table("inventory").select("id, quantity_available").in_("id", item_ids).execute()
            availability_map = {row["id"]: row["quantity_available"] for row in (inv_resp.data or [])}

            insufficient = []
            for iid, info in equipment_quantities.items():
                available = availability_map.get(iid, 0)
                if info["quantity"] > available:
                    insufficient.append(f"{info['name']} (requested {info['quantity']}, available {available})")

            if insufficient:
                flash("Not enough stock for: " + ", ".join(insufficient), "error")
                return redirect(url_for("booking2_page"))

        # Insert into Supabase with retry on unique ticket_number conflict
        for _ in range(5):
            try:
                # Recompute next ticket just in case of race/conflict
                try:
                    res = (
                        supabase
                        .table("bookings")
                        .select("ticket_number, created_at")
                        .neq("event_type", "Equipment Booking")
                        .gte("created_at", RESET_FROM_ISO)
                        .like("ticket_number", "TKT-C%")
                        .order("ticket_number", desc=True)
                        .limit(1)
                        .execute()
                    )
                    last_ticket = (res.data[0]["ticket_number"] if res.data else "")
                    m = re.match(r"^TKT-C(\d{4})$", last_ticket or "")
                    next_num = (int(m.group(1)) + 1) if m else 1
                    ticket_number = f"TKT-C{str(next_num).zfill(4)}"
                    booking_data["ticket_number"] = ticket_number
                except Exception:
                    # keep existing ticket_number if recompute fails
                    pass
                supabase.table("bookings").insert(booking_data).execute()
                break
            except Exception as insert_err:
                if "bookings_ticket_number_key" in str(insert_err):
                    continue
                raise

        flash(f"Booking submitted successfully! Ticket: {ticket_number}", "success")

        # --- NEW: Create Notification for User ---
        # Include snapshot so notification details modal shows Pending even if status changes later
        pending_link2 = url_for('booking_details', booking_id=booking_id) + "?status_at_time=Pending"
        create_notification(
            user_id=user_id,
            message=f"Your event booking request (Ticket: {ticket_number}) has been submitted and is now pending approval.",
            booking_id=booking_id,
            link=pending_link2,
        )

        send_email_notification(
            to_email=email,
            subject="⏳ Booking Pending Approval",
            message=get_email_template(
                status="pending",
                user_first_name=user_first_name,
                ticket_number=ticket_number,
                event_date=event_date,
                event_type=event_type,
                link=f"booking_details/{booking_id}",
                booking_date=booking_data["created_at"],
                equipment=all_other_items,
                contact_number=contact_number,
                email_address=email,
                status_override="Pending"
            )
        )

        admin_users = supabase.table("users").select("id").eq("role", "admin").execute()
        if admin_users.data:
            for admin in admin_users.data:
                create_notification(
                    user_id=admin['id'],
                    message=f"New event booking from {user_first_name} {user_last_name} (Ticket: {ticket_number})",
                    booking_id=booking_id,
                    admin_only=True,
                    link=url_for('admin_booking_details', booking_id=booking_id)
                )

        return redirect(url_for("booking2_page"))

    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "error")
        return redirect(url_for("booking2_page"))
    


@app.route("/admin_portal")
def admin_portal():
    if "user" not in session or session["user"]["role"] != "admin":
        flash("Admins only!", "error")
        return redirect(url_for("admin_login"))
    
    try:
        # Kunin ang mga stats para sa admin dashboard
        total_bookings = supabase.table("bookings").select("*").execute()
        total_users = supabase.table("users").select("*").execute()
        
        # Kunin ang mga pending approvals KASAMA ANG USER INFO at created_at (newest first)
        pending_approvals_data = supabase.table("bookings") \
            .select("*, users(first_name, last_name), created_at") \
            .eq("status", "Pending") \
            .order("created_at", desc=True) \
            .execute()
        
        # ✅ Helper function to parse other_items
        def parse_other_items(items_str):
            if not items_str:
                return []
            items = []
            for item_str in items_str.split(", "):
                if " x" in item_str:
                    name, qty_str = item_str.rsplit(" x", 1)
                    try:
                        quantity = int(qty_str)
                        items.append({
                            "name": name.strip(),
                            "quantity": quantity
                        })
                    except ValueError:
                        continue
            return items

        # ✅ Parse other_items for each pending approval
        pending_approvals = []
        if pending_approvals_data.data:
            for booking in pending_approvals_data.data:
                booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
                pending_approvals.append(booking)

        # Kunin ang lahat ng bookings (newest first)
        all_bookings_data = supabase.table("bookings") \
            .select("*, users(first_name, last_name)") \
            .order("created_at", desc=True) \
            .execute()
            
        all_bookings = []
        if all_bookings_data.data:
            for booking in all_bookings_data.data:
                booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
                all_bookings.append(booking)

        # Kunin ang lahat ng equipment (alphabetical by name)
        equipment_data = supabase.table("inventory").select("*").order("name", desc=False).execute()
        equipment_items = equipment_data.data if equipment_data.data else []
        # Inject computed quantity_defective (from description)
        for it in equipment_items:
            it["quantity_defective"] = parse_defective_from_description(it.get("description", ""))
        
        # Get all users for user management
        users_data = supabase.table("users").select("*").order("created_at", desc=True).execute()
        users = users_data.data if users_data.data else []
        
        # I-prepare ang data
        stats = {
            "total_bookings": len(total_bookings.data) if total_bookings.data else 0,
            "total_users": len(total_users.data) if total_users.data else 0,
            "pending_approvals": len(pending_approvals),
            "total_equipment": len(equipment_items)
        }
        
        # ✅ GET ADMIN NOTIFICATIONS (show read and unread, only for current admin)
        # Fetch notifications for the current admin user_id (covers both admin_only and user-targeted)
        all_admin_notifs = supabase.table("notifications") \
            .select("*") \
            .eq("user_id", session['user']['id']) \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()

        admin_notifications = all_admin_notifs.data if all_admin_notifs.data else []
        # Sort and limit to 10 for display
        admin_notifications = sorted(
            admin_notifications,
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )[:10]

        # Compute unread count separately for accurate badge
        unread_res = supabase.table("notifications") \
            .select("id") \
            .eq("user_id", session['user']['id']) \
            .eq("is_read", False) \
            .execute()
        unread_admin_count = len(unread_res.data) if unread_res.data else 0

        return render_template(
            "admin_portal.html", 
            stats=stats,
            pending_approvals=pending_approvals,
            all_bookings=all_bookings,
            equipment_items=equipment_items,
            admin_notifications=admin_notifications,
            unread_admin_count=unread_admin_count,
            users=users
        )
    
    except Exception as e:
        flash(f"Error loading admin portal: {str(e)}", "error")
        return redirect(url_for("admin_login"))

@app.route("/admin/booking_details/<booking_id>")
def admin_booking_details(booking_id):
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        # Kunin ang booking details kasama ang user info
        booking_data = supabase.table("bookings").select("*, users(first_name, last_name, barangay_id)").eq("id", booking_id).execute()
        
        if not booking_data.data:
            return jsonify({"success": False, "message": "Booking not found"})
        
        booking = booking_data.data[0]

        # Kunin ang listahan ng lahat ng active equipment para i-map (kasama na ang category_id)
        try:
            equipment_data = supabase.table("inventory").select("id, name, category_id").eq("is_active", True).execute()
            # Gumawa ng map: name → category_id (para sa matching)
            name_to_category = {item['name']: item['category_id'] for item in equipment_data.data} if equipment_data.data else {}
        except Exception as e:
            name_to_category = {}
            print(f"Error fetching equipment map: {e}")

        # I-decode ang other_items field at i-assign ang category_id
        equipment_list = []
        if booking.get("other_items"):
            for item_str in booking["other_items"].split(", "):
                if " x" in item_str:
                    name_part, qty_str = item_str.rsplit(" x", 1)
                    name = name_part.strip()  # Important: i-strip para walang space
                    try:
                        qty = int(qty_str)
                        # Hanapin ang category_id base sa name
                        category_id = name_to_category.get(name, "cat6")  # Default: cat6 (Other)
                        equipment_list.append({
                            "name": name,
                            "quantity": qty,
                            "category_id": category_id  # ✅ Ito ang idinagdag para sa JS emoji logic
                        })
                    except ValueError:
                        continue

        # I-override ang booking data para isama ang decoded equipment (kasama category_id)
        booking["equipment_list"] = equipment_list

        return jsonify({"success": True, "data": booking})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/admin/booking_details_by_ticket/<ticket_number>")
def admin_booking_details_by_ticket(ticket_number):
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})

    try:
        # Find booking by ticket_number
        booking_data = supabase.table("bookings").select("*, users(first_name, last_name, barangay_id)") \
            .eq("ticket_number", ticket_number).limit(1).execute()
        if not booking_data.data:
            return jsonify({"success": False, "message": "Booking not found"})

        booking = booking_data.data[0]

        # Map equipment names to category_id for rendering icons
        try:
            equipment_data = supabase.table("inventory").select("id, name, category_id").eq("is_active", True).execute()
            name_to_category = {item['name']: item['category_id'] for item in equipment_data.data} if equipment_data.data else {}
        except Exception:
            name_to_category = {}

        equipment_list = []
        if booking.get("other_items"):
            for item_str in booking["other_items"].split(", "):
                if " x" in item_str:
                    name_part, qty_str = item_str.rsplit(" x", 1)
                    name = name_part.strip()
                    try:
                        qty = int(qty_str)
                        category_id = name_to_category.get(name, "cat6")
                        equipment_list.append({
                            "name": name,
                            "quantity": qty,
                            "category_id": category_id
                        })
                    except ValueError:
                        continue

        booking["equipment_list"] = equipment_list
        return jsonify({"success": True, "data": booking})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/admin/approve_booking", methods=["POST"])
def admin_approve_booking():
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        items_override = data.get('items')  # Optional: [{name, quantity}]
        
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"})
        
        # Fetch booking details including items to validate/deduct inventory
        booking_data = supabase.table("bookings").select("user_id, ticket_number, email, first_name, event_type, event_date, other_items, contact_number, created_at").eq("id", booking_id).execute()
        if booking_data.data:
            user_id = booking_data.data[0]['user_id']
            ticket_number = booking_data.data[0]['ticket_number']
            user_email = booking_data.data[0]['email']
            user_first_name = booking_data.data[0]['first_name']
            other_items_str = booking_data.data[0].get('other_items') or ""

            # Build items from override if provided; else parse other_items
            items = []
            if items_override and isinstance(items_override, list):
                for it in items_override:
                    try:
                        nm = str(it.get('name', '')).strip()
                        qt = int(it.get('quantity', 0))
                        if nm and qt >= 0:
                            items.append({"name": nm, "quantity": qt})
                    except Exception:
                        continue
            else:
                if other_items_str:
                    for item_str in other_items_str.split(", "):
                        if " x" in item_str:
                            name_part, qty_str = item_str.rsplit(" x", 1)
                            try:
                                items.append({"name": name_part.strip(), "quantity": int(qty_str)})
                            except ValueError:
                                continue

            # Validate inventory on approval (no deduction at this stage)
            if items:
                inv_data = supabase.table("inventory").select("id, name, quantity_available").in_("name", [it["name"] for it in items]).execute()
                name_to_item = {row["name"]: row for row in (inv_data.data or [])}

                insufficient = []
                for it in items:
                    inv_row = name_to_item.get(it["name"]) or {}
                    available = int(inv_row.get("quantity_available", 0)) if inv_row else 0
                    if it["quantity"] > available:
                        insufficient.append(f"{it['name']} (requested {it['quantity']}, available {available})")

                if insufficient:
                    return jsonify({"success": False, "message": "Not enough stock for: " + ", ".join(insufficient)}), 400

            # If override provided, store the final approved quantities back to other_items
            try:
                if items_override and items:
                    new_other = ", ".join([f"{it['name']} x{int(it['quantity'])}" for it in items if int(it['quantity']) > 0])
                    supabase.table("bookings").update({"other_items": new_other}).eq("id", booking_id).execute()
            except Exception:
                pass

            # Update booking status to Approved AFTER successful deduction
            supabase.table("bookings").update({"status": "Approved"}).eq("id", booking_id).execute()

            approved_link = url_for('booking_details', booking_id=booking_id) + "?status_at_time=Approved"
            create_notification(
                user_id=user_id,
                message=f"Great news! Your booking request (Ticket: {ticket_number}) has been approved.",
                booking_id=booking_id,
                link=approved_link,
            )

            # --- NEW: Send Email Notification ---
            send_email_notification(
                to_email=user_email,
                subject="✅ Booking Approved!",
                message=get_email_template(
                    status="approved",
                    user_first_name=user_first_name,
                    ticket_number=ticket_number,
                    event_date=booking_data.data[0].get('event_date'),
                    event_type=booking_data.data[0].get('event_type'),
                    link=f"booking_details/{booking_id}",
                    booking_date=booking_data.data[0].get('created_at'),
                    equipment=other_items_str,
                    contact_number=booking_data.data[0].get('contact_number'),
                    email_address=user_email,
                    status_override="Approved"
                )
            )
        
        return jsonify({"success": True, "message": "Booking approved successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/admin/reject_booking", methods=["POST"])
def admin_reject_booking():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        booking_id = data.get("booking_id")
        reject_reason = (data.get("reject_reason") or "").strip()
        reject_notes = (data.get("reject_notes") or "").strip()

        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"}), 400
        if not reject_reason:
            return jsonify({"success": False, "message": "Reject reason is required"}), 400

        # Fetch previous status and items BEFORE updating
        prev_info = supabase.table("bookings").select("status, other_items").eq("id", booking_id).limit(1).execute()
        prev_status = (prev_info.data or [{}])[0].get("status") if prev_info.data else None
        other_items_before = (prev_info.data or [{}])[0].get("other_items", "") if prev_info.data else ""

        response = supabase.table("bookings") \
            .update({"status": "Rejected", "reject_reason": reject_reason}) \
            .eq("id", booking_id) \
            .execute()

        if not response.data:
            return jsonify({"success": False, "message": "Booking not found"}), 404

        # --- UPDATED: Restore inventory ONLY if previously Approved or Borrowed ---
        try:
            if prev_status in ("Approved", "Borrowed"):
                other_items_str = other_items_before
                items = []
                if other_items_str:
                    for item_str in other_items_str.split(", "):
                        if " x" in item_str:
                            name_part, qty_str = item_str.rsplit(" x", 1)
                            try:
                                items.append({"name": name_part.strip(), "quantity": int(qty_str)})
                            except ValueError:
                                continue

                if items:
                    inv_data = supabase.table("inventory").select("id, name, quantity_available").execute()
                    name_to_item = {row["name"]: row for row in (inv_data.data or [])}
                    for it in items:
                        inv_row = name_to_item.get(it["name"])  # Only restore if the name exists in inventory
                        if inv_row:
                            new_av = int(inv_row.get("quantity_available", 0)) + int(it["quantity"])
                            supabase.table("inventory").update({"quantity_available": new_av}).eq("id", inv_row["id"]).execute()
        except Exception as inv_restore_err:
            print(f"Warning: Failed to restore inventory on reject: {inv_restore_err}")

        # --- NEW: Fetch user_id and notify user ---
        booking_data = supabase.table("bookings").select("user_id, ticket_number, email, first_name, event_type, event_date, other_items, contact_number, created_at").eq("id", booking_id).execute()
        if booking_data.data:
            user_id = booking_data.data[0]['user_id']
            ticket_number = booking_data.data[0]['ticket_number']
            user_email = booking_data.data[0]['email']
            user_first_name = booking_data.data[0]['first_name']

            # Build combined text for message output only
            reason_text = reject_reason + (f" | Notes: {reject_notes}" if reject_notes else "")

            create_notification(
                user_id=user_id,
                message=f"We're sorry, your booking request (Ticket: {ticket_number}) has been rejected. Reason: {reason_text}",
                booking_id=booking_id,
                link=url_for('booking_details', booking_id=booking_id)
            )

            # --- NEW: Send Email Notification ---
            send_email_notification(
                to_email=user_email,
                subject="❌ Booking Rejected",
                message=get_email_template(
                    status="rejected",
                    user_first_name=user_first_name,
                    ticket_number=ticket_number,
                    event_date=booking_data.data[0].get('event_date'),
                    event_type=booking_data.data[0].get('event_type'),
                    reason=reason_text,
                    link=f"booking_details/{booking_id}",
                    booking_date=booking_data.data[0].get('created_at'),
                    equipment=booking_data.data[0].get('other_items'),
                    contact_number=booking_data.data[0].get('contact_number'),
                    email_address=user_email,
                    status_override="Rejected"
                )
            )

        return jsonify({"success": True, "message": "Booking rejected successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# --- NEW: Equipment management endpoints (used by Admin UI) ---
@app.get('/admin/equipment/<item_id>')
def get_equipment_item(item_id):
    try:
        if "user" not in session or session["user"].get("role") != "admin":
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        item_id = (item_id or '').strip()
        if not item_id:
            return jsonify({"success": False, "message": "Missing item_id"}), 400
        res = supabase.table("inventory").select("*").eq("id", item_id).limit(1).execute()
        if not res.data:
            return jsonify({"success": False, "message": "Not Found"}), 404
        item = res.data[0]
        item["quantity_defective"] = parse_defective_from_description(item.get("description", ""))
        return jsonify({"success": True, "item": item})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.post('/admin/equipment/add')
def add_equipment():
    try:
        if "user" not in session or session["user"].get("role") != "admin":
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        data = request.get_json(force=True) or {}
        name = (data.get('name') or '').strip()
        category_id = (data.get('category_id') or 'cat6').strip()
        qty_total = _to_int(data.get('quantity_total'), 0)
        qty_avail = _to_int(data.get('quantity_available'), 0)
        qty_def = _to_int(data.get('quantity_defective'), 0)
        is_active = str(data.get('is_active')).lower() != 'false'
        if not name:
            return jsonify({"success": False, "message": "Name is required"}), 400
        qty_total = max(qty_total, 0)
        qty_avail = max(min(qty_avail, qty_total), 0)
        qty_def = max(qty_def, 0)
        desc = set_defective_in_description(data.get('description') or '', qty_def)
        new_item = {
            "id": str(uuid.uuid4()),
            "name": name,
            "category_id": category_id,
            "description": desc,
            "quantity_total": qty_total,
            "quantity_available": qty_avail,
            "is_active": is_active,
            "created_at": datetime.now().isoformat()
        }
        supabase.table("inventory").insert(new_item).execute()
        new_item["quantity_defective"] = qty_def
        return jsonify({"success": True, "item": new_item})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.post('/admin/equipment/update')
def update_equipment():
    try:
        if "user" not in session or session["user"].get("role") != "admin":
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        data = request.get_json(force=True) or {}
        item_id = (data.get('id') or '').strip()
        if not item_id:
            return jsonify({"success": False, "message": "Missing id"}), 400
        # Fetch existing to merge description/defective
        cur = supabase.table("inventory").select("*").eq("id", item_id).limit(1).execute()
        if not cur.data:
            return jsonify({"success": False, "message": "Not Found"}), 404
        cur_item = cur.data[0]
        # Parse inputs (blank strings fallback to current values)
        name_in = data.get('name')
        name = (name_in if (isinstance(name_in, str) and name_in.strip() != "") else cur_item.get('name') or '').strip()
        cat_in = data.get('category_id')
        category_id = (cat_in if (isinstance(cat_in, str) and cat_in.strip() != "") else cur_item.get('category_id') or 'cat6').strip()
        qt_in = data.get('quantity_total')
        qa_in = data.get('quantity_available')
        qd_in = data.get('quantity_defective')
        qty_total = _to_int(qt_in, cur_item.get('quantity_total') or 0)
        qty_avail = _to_int(qa_in, cur_item.get('quantity_available') or 0)
        qty_def = _to_int(qd_in, parse_defective_from_description(cur_item.get('description') or ''))
        is_active = cur_item.get('is_active', True)
        if 'is_active' in data:
            is_active = str(data.get('is_active')).lower() != 'false'
        # Clamp
        qty_total = max(qty_total, 0)
        qty_avail = max(min(qty_avail, qty_total), 0)
        qty_def = max(qty_def, 0)
        # Merge description with defective
        desc = set_defective_in_description(cur_item.get('description') or '', qty_def)
        update = {
            "name": name,
            "category_id": category_id,
            "description": desc,
            "quantity_total": qty_total,
            "quantity_available": qty_avail,
            "is_active": is_active,
        }
        supabase.table("inventory").update(update).eq("id", item_id).execute()
        update_out = {**cur_item, **update, "id": item_id, "quantity_defective": qty_def}
        return jsonify({"success": True, "item": update_out})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.post('/admin/equipment/delete')
def delete_equipment():
    try:
        if "user" not in session or session["user"].get("role") != "admin":
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        data = request.get_json(force=True) or {}
        item_id = (data.get('id') or '').strip()
        if not item_id:
            return jsonify({"success": False, "message": "Missing id"}), 400
        # Ensure item exists before delete
        existing = supabase.table("inventory").select("id").eq("id", item_id).limit(1).execute()
        if not existing.data:
            return jsonify({"success": False, "message": "Item not found"}), 404
        supabase.table("inventory").delete().eq("id", item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.post('/admin/inventory/by_names')
def inventory_by_names():
    try:
        if "user" not in session or session["user"].get("role") != "admin":
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        payload = request.get_json(force=True) or {}
        names = payload.get('names') or []
        if not isinstance(names, list) or not names:
            return jsonify({"success": True, "items": []})
        res = supabase.table("inventory").select("*").in_("name", names).execute()
        items = []
        for r in (res.data or []):
            r["quantity_defective"] = parse_defective_from_description(r.get("description", ""))
            items.append(r)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# --- Admin: Update booking items (quantities) prior to approval ---
@app.route("/admin/booking_items/update", methods=["POST"])
def admin_update_booking_items():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        data = request.get_json() or {}
        booking_id = data.get("booking_id")
        items = data.get("items") or []  # [{name, quantity}]
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"}), 400
        # Ensure booking is Pending before editing requested quantities
        bq = supabase.table("bookings").select("status").eq("id", booking_id).limit(1).execute()
        status = (bq.data or [{}])[0].get("status") if bq.data else None
        if status != "Pending":
            return jsonify({"success": False, "message": "Only Pending bookings can be edited"}), 400

        # Build new other_items string from provided items
        normalized = []
        if isinstance(items, list):
            for it in items:
                try:
                    nm = str(it.get("name", "")).strip()
                    qt = int(it.get("quantity", 0))
                    if nm and qt >= 0:
                        normalized.append({"name": nm, "quantity": qt})
                except Exception:
                    continue
        # Keep only >0 in display string; 0 means remove
        other_str = ", ".join([f"{it['name']} x{int(it['quantity'])}" for it in normalized if int(it['quantity']) > 0])

        supabase.table("bookings").update({"other_items": other_str}).eq("id", booking_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# --- NEW: Mark booking as Borrowed ---
@app.route("/admin/mark_borrowed", methods=["POST"])
def admin_mark_borrowed():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        booking_id = data.get("booking_id")
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"}), 400

        # Update status to Borrowed only if currently Approved
        current = supabase.table("bookings").select("status, user_id, ticket_number, first_name, email, event_type, event_date, other_items, contact_number, created_at").eq("id", booking_id).limit(1).execute()
        if not current.data:
            return jsonify({"success": False, "message": "Booking not found"}), 404
        cur = current.data[0]
        if cur.get("status") != "Approved":
            return jsonify({"success": False, "message": "Only approved bookings can be marked as borrowed"}), 400

        # Parse requested items from other_items string: "Name xQty, Name2 xQty2"
        items = []
        other_items_str = cur.get("other_items") or ""
        if other_items_str:
            for item_str in other_items_str.split(", "):
                if " x" in item_str:
                    name_part, qty_str = item_str.rsplit(" x", 1)
                    try:
                        qty = int(qty_str)
                    except ValueError:
                        continue
                    if qty > 0:
                        items.append({"name": name_part.strip(), "quantity": qty})

        # If there are equipment items, verify availability and subtract
        if items:
            inv_data = supabase.table("inventory").select("id, name, quantity_available").execute()
            name_to_item = {row["name"]: row for row in (inv_data.data or [])}

            # Check availability first
            for it in items:
                inv_row = name_to_item.get(it["name"])  # skip if not found in inventory
                if inv_row:
                    available = int(inv_row.get("quantity_available", 0))
                    if available < int(it["quantity"]):
                        return jsonify({
                            "success": False,
                            "message": f"Insufficient stock for '{it['name']}'. Available: {available}, required: {it['quantity']}"
                        }), 400

            # All good; subtract quantities
            for it in items:
                inv_row = name_to_item.get(it["name"])  # subtract only if exists
                if inv_row:
                    new_av = int(inv_row.get("quantity_available", 0)) - int(it["quantity"])
                    if new_av < 0:
                        new_av = 0  # safety clamp; should not happen due to check above
                    supabase.table("inventory").update({"quantity_available": new_av}).eq("id", inv_row["id"]).execute()

        # Finally update booking status
        supabase.table("bookings").update({"status": "Borrowed"}).eq("id", booking_id).execute()

        # Notify user (app notification)
        try:
            create_notification(
                user_id=cur.get("user_id"),
                message=f"Your booking (Ticket: {cur.get('ticket_number')}) items have been released. Status: Borrowed.",
                booking_id=booking_id,
                link=url_for('booking_details', booking_id=booking_id)
            )
        except Exception as nerr:
            print(f"notify borrowed err: {nerr}")

        # Email user (In Progress)
        try:
            send_email_notification(
                to_email=cur.get("email"),
                subject="🚚 In Progress",
                message=get_email_template(
                    status="borrowed",
                    user_first_name=cur.get("first_name") or "",
                    ticket_number=cur.get("ticket_number") or "",
                    event_date=cur.get("event_date"),
                    event_type=cur.get("event_type"),
                    link=f"booking_details/{booking_id}",
                    booking_date=cur.get("created_at"),
                    equipment=cur.get("other_items"),
                    contact_number=cur.get("contact_number"),
                    email_address=cur.get("email"),
                    status_override="In Progress"
                )
            )
        except Exception as e:
            print(f"borrowed email send err: {e}")

        return jsonify({"success": True, "message": "Booking marked as Borrowed"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# --- NEW: Mark booking as Completed (return). Also restore inventory ---
@app.route("/admin/mark_completed", methods=["POST"])
def admin_mark_completed():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        booking_id = data.get("booking_id")
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"}), 400

        # Ensure booking exists and is Borrowed (or Approved -> allow force return?)
        current = supabase.table("bookings").select("status, other_items, user_id, ticket_number, first_name, email, event_date, event_type, contact_number, created_at").eq("id", booking_id).limit(1).execute()
        if not current.data:
            return jsonify({"success": False, "message": "Booking not found"}), 404
        cur = current.data[0]
        if cur.get("status") not in ("Borrowed", "Approved"):
            return jsonify({"success": False, "message": "Only borrowed/approved bookings can be completed"}), 400

        # Restore inventory quantities for reserved items
        try:
            other_items_str = cur.get("other_items") or ""
            items = []
            if other_items_str:
                for item_str in other_items_str.split(", "):
                    if " x" in item_str:
                        name_part, qty_str = item_str.rsplit(" x", 1)
                        try:
                            items.append({"name": name_part.strip(), "quantity": int(qty_str)})
                        except ValueError:
                            continue

            if items:
                inv_data = supabase.table("inventory").select("id, name, quantity_available").execute()
                name_to_item = {row["name"]: row for row in (inv_data.data or [])}
                for it in items:
                    inv_row = name_to_item.get(it["name"])  # restore only if exists
                    if inv_row:
                        new_av = int(inv_row.get("quantity_available", 0)) + int(it["quantity"])
                        supabase.table("inventory").update({"quantity_available": new_av}).eq("id", inv_row["id"]).execute()
        except Exception as inv_err:
            print(f"Warning: Failed to restore inventory on completed: {inv_err}")

        # Update status to Completed
        supabase.table("bookings").update({"status": "Completed"}).eq("id", booking_id).execute()

        # Notify user (app notification)
        try:
            create_notification(
                user_id=cur.get("user_id"),
                message=f"Your booking (Ticket: {cur.get('ticket_number')}) has been completed. All items returned.",
                booking_id=booking_id,
                link=url_for('booking_details', booking_id=booking_id)
            )
        except Exception as nerr:
            print(f"notify completed err: {nerr}")

        # Email user (Completed)
        try:
            send_email_notification(
                to_email=cur.get("email"),
                subject="✔️ Booking Completed",
                message=get_email_template(
                    status="completed",
                    user_first_name=cur.get("first_name") or "",
                    ticket_number=cur.get("ticket_number") or "",
                    event_date=cur.get("event_date"),
                    event_type=cur.get("event_type"),
                    link=f"booking_details/{booking_id}",
                    booking_date=cur.get("created_at"),
                    equipment=cur.get("other_items"),
                    contact_number=cur.get("contact_number"),
                    email_address=cur.get("email"),
                    status_override="Completed"
                )
            )
        except Exception as e:
            print(f"completed email send err: {e}")

        return jsonify({"success": True, "message": "Booking marked as Completed"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# --- NEW: Mark booking as Completed (return). Also restore inventory ---
@app.route("/admin/complete_with_adjustments", methods=["POST"])
def admin_complete_with_adjustments():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        data = request.get_json() or {}
        booking_id = data.get("booking_id")
        adj_items = data.get("items") or []  # [{name, quantity_total, quantity_defective, return_qty}]
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"}), 400

        # Validate booking exists and is Borrowed or Approved
        current = supabase.table("bookings").select("status, other_items, user_id, ticket_number, first_name, email, event_date, event_type, contact_number, created_at").eq("id", booking_id).limit(1).execute()
        if not current.data:
            return jsonify({"success": False, "message": "Booking not found"}), 404
        cur = current.data[0]
        if cur.get("status") not in ("Borrowed", "Approved"):
            return jsonify({"success": False, "message": "Only borrowed/approved bookings can be completed"}), 400

        # Build requested quantities map from booking.other_items (e.g., "Tent x2, Chair x3")
        requested_map = {}
        try:
            items_list = parse_other_items(cur.get("other_items", ""))
            for it in items_list:
                # it expected like {"name": str, "quantity": int}
                nm = (it.get("name") or "").strip()
                if nm:
                    requested_map[nm] = int(it.get("quantity", 0) or 0)
        except Exception:
            requested_map = {}

        # Apply adjustments to inventory
        updated_names = []
        for it in adj_items:
            name = (it.get("name") or "").strip()
            if not name:
                continue
            # Fetch current row by name
            inv_q = supabase.table("inventory").select("id, quantity_total, quantity_available, description").eq("name", name).limit(1).execute()
            if not inv_q.data:
                continue
            row = inv_q.data[0]
            total = int(row.get("quantity_total", 0) or 0)
            defective = int(it.get("quantity_defective", parse_defective_from_description(row.get("description", ""))) or 0)
            return_qty = int(it.get("return_qty", 0) or 0)
            # Prefer explicit in_progress from client if provided; else infer from requested
            if it.get("in_progress") is not None:
                try:
                    inprog = max(int(it.get("in_progress") or 0), 0)
                except Exception:
                    inprog = 0
            else:
                requested_qty = int(requested_map.get(name, 0) or 0)
                inprog = requested_qty - max(int(defective), 0) - max(return_qty, 0)
                if inprog < 0:
                    inprog = 0
            # Set availability so that: in_progress (table) = total - available - defective = inprog
            # => available = total - defective - inprog
            max_avail = max(total - max(defective, 0), 0)
            avail_target = max(total - max(int(defective), 0) - inprog, 0)
            # Clamp to valid range [0, total - defective]
            avail = min(max(avail_target, 0), max_avail)
            new_desc = set_defective_in_description(row.get("description", ""), defective)
            supabase.table("inventory").update({
                "quantity_total": total,
                "description": new_desc,
                "quantity_available": avail
            }).eq("id", row["id"]).execute()
            updated_names.append(name)

        # Mark booking as Completed
        supabase.table("bookings").update({"status": "Completed"}).eq("id", booking_id).execute()

        # Notify user (app notification)
        try:
            create_notification(
                user_id=cur.get("user_id"),
                message=f"Your booking (Ticket: {cur.get('ticket_number')}) has been completed. Items processed.",
                booking_id=booking_id,
                link=url_for('booking_details', booking_id=booking_id)
            )
        except Exception as nerr:
            print(f"notify completed with adjustments err: {nerr}")

        # Email user (Completed)
        try:
            send_email_notification(
                to_email=cur.get("email"),
                subject="✔️ Booking Completed",
                message=get_email_template(
                    status="completed",
                    user_first_name=cur.get("first_name") or "",
                    ticket_number=cur.get("ticket_number") or "",
                    event_date=cur.get("event_date"),
                    event_type=cur.get("event_type"),
                    link=f"booking_details/{booking_id}",
                    booking_date=cur.get("created_at"),
                    equipment=cur.get("other_items"),
                    contact_number=cur.get("contact_number"),
                    email_address=cur.get("email"),
                    status_override="Completed"
                )
            )
        except Exception as e:
            print(f"completed (adjust) email send err: {e}")

        return jsonify({"success": True, "updated": updated_names})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")
    
    # Process POST request
    email = request.form["email"].strip().lower()
    password = request.form["password"]

    try:
        # Get admin from custom users table
        response = supabase.table("users").select("*").eq("email", email).eq("role", "admin").execute()

        if not response.data:
            flash("Admin not found!", "error")
            return redirect(url_for("admin_login"))

        user = response.data[0]

        # Check if verified
        if not user["is_verified"]:
            flash("Admin not verified yet!", "error")
            return redirect(url_for("admin_login"))

        # Check password
        if not check_password_hash(user["password"], password):
            flash("Invalid password!", "error")
            return redirect(url_for("admin_login"))

        session["user"] = {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "role": user["role"]
        }
        return redirect(url_for("admin_portal"))

    except Exception as e:
        flash(f"Login failed: {str(e)}", "error")
        return redirect(url_for("admin_login"))

@app.route('/adminlogout', methods=['POST'])
def admin_logout():
    try:
        uid = session.get("user", {}).get("id")
        if uid:
            try:
                supabase.table('users').update({'last_seen': None}).eq('id', uid).execute()
            except Exception:
                pass
    finally:
        session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('admin_login'))

@app.route('/logout', methods=['POST'])
def logout():
    try:
        uid = session.get("user", {}).get("id")
        if uid:
            try:
                supabase.table('users').update({'last_seen': None}).eq('id', uid).execute()
            except Exception:
                pass
    finally:
        session.pop("user", None)
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))

@app.route("/signout", methods=["POST"])
def signout():
    try:
        uid = session.get("user", {}).get("id")
        if uid:
            try:
                supabase.table('users').update({'last_seen': None}).eq('id', uid).execute()
            except Exception:
                pass
    finally:
        session.pop("user", None)
    return redirect(url_for("home"))

def get_unread_notification_count(user_id):
    try:
        unread_notif_data = supabase.table("notifications") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .eq("is_read", False) \
            .execute()
        return len(unread_notif_data.data) if unread_notif_data.data else 0
    except:
        return 0





@app.route('/change_password', methods=['POST'])
def change_password():
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first!"})
    
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        # Validation
        if not current_password or not new_password or not confirm_password:
            return jsonify({"success": False, "message": "All fields are required!"})
        
        if new_password != confirm_password:
            return jsonify({"success": False, "message": "New passwords do not match!"})
        
        if len(new_password) < 8:
            return jsonify({"success": False, "message": "New password must be at least 8 characters long!"})
        
        if current_password == new_password:
            return jsonify({"success": False, "message": "New password must be different from current password!"})
        
        # Get current user
        user_id = session["user"]["id"]
        user_data = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not user_data.data:
            return jsonify({"success": False, "message": "User not found!"})
        
        user = user_data.data[0]
        
        # Verify current password
        if not check_password_hash(user["password"], current_password):
            return jsonify({"success": False, "message": "Current password is incorrect!"})
        
        # Validate new password strength
        password_error = validate_password_strength(new_password)
        if password_error:
            return jsonify({"success": False, "message": password_error})
        
        # Hash new password
        new_hashed_password = generate_password_hash(new_password)
        
        # Update password in database
        supabase.table("users").update({
            "password": new_hashed_password
        }).eq("id", user_id).execute()
        
        # Also update in Supabase Auth
        try:
            supabase.auth.update_user({
                "password": new_password
            })
        except Exception as e:
            print(f"Warning: Could not update Supabase Auth password: {e}")
        
        return jsonify({"success": True, "message": "Password changed successfully!"})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error changing password: {str(e)}"})

# --- Suspended account page ---
@app.route('/suspended')
def suspended():
    try:
        user_id = session.get('user', {}).get('id')
        reason = None
        if user_id:
            res = get_user_by_id(user_id)
            if res.data:
                user = res.data[0]
                # Only non-admin suspended users should land here
                if user.get('role') != 'admin' and user.get('is_suspended', False):
                    reason = user.get('suspend_notes') or user.get('suspend_reason')
        return render_template('suspended.html', reason=reason or 'Your account has been suspended by an administrator.')
    except Exception:
        return render_template('suspended.html', reason='Your account has been suspended by an administrator.')

# --- Admin: User CRUD minimal endpoints used by UI ---
@app.get('/admin/users/<user_id>')
def admin_get_user(user_id):
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    res = get_user_by_id(user_id)
    if not res.data:
        return jsonify({"success": False, "message": "User not found"}), 404
    user = res.data[0]
    # Return plain JSON object (not wrapped) to match existing frontend usage
    return jsonify(user)

@app.post('/admin/users/<user_id>/update')
def admin_update_user(user_id):
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        data = request.get_json() or {}
        update_data = {
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email"),
            "barangay_id": data.get("barangay_id"),
            "role": data.get("role", "user"),
            "address": data.get("address", "")
        }
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        supabase.table("users").update(update_data).eq("id", user_id).execute()
        return jsonify({"success": True, "message": "User updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.post('/admin/users/add')
def admin_add_user():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        data = request.get_json() or {}
        required = ["first_name", "last_name", "email", "password", "role"]
        for f in required:
            if not data.get(f):
                return jsonify({"success": False, "message": f"Missing field: {f}"}), 400
        # Create in Supabase Auth
        try:
            supabase.auth.sign_up({
                "email": data["email"],
                "password": data["password"]
            })
        except Exception:
            pass
        user_row = {
            "id": str(uuid.uuid4()),
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "email": data["email"],
            "password": generate_password_hash(data["password"]),
            "barangay_id": data.get("barangay_id"),
            "address": data.get("address", ""),
            "role": data.get("role", "user"),
            "is_verified": True,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        supabase.table("users").insert(user_row).execute()
        return jsonify({"success": True, "message": "User added"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# --- Admin: Suspend/Unsuspend ---
@app.post('/admin/users/<user_id>/suspend')
def admin_suspend_user(user_id):
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        payload = request.get_json() or {}
        reason = (payload.get('reason') or '').strip()
        notes = (payload.get('notes') or '').strip()
        if not reason:
            return jsonify({"success": False, "message": "Reason is required"}), 400
        # Prevent self-suspension
        if user_id == session['user']['id']:
            return jsonify({"success": False, "message": "You cannot suspend your own account"}), 400
        supabase.table('users').update({
            'is_suspended': True,
            # Keep legacy field for compatibility
            'suspend_reason': reason,
            # New notes field (optional)
            'suspend_notes': notes if notes else None,
            'suspended_at': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        # Send suspension email notification (with full account details)
        try:
            user_q = supabase.table('users').select('email, first_name, last_name, barangay_id, address, created_at, suspended_at').eq('id', user_id).limit(1).execute()
            if user_q.data:
                u = user_q.data[0]
                to_email = u.get('email')
                first_name = (u.get('first_name') or '').strip()
                last_name = (u.get('last_name') or '').strip()
                full_name = (f"{first_name} {last_name}".strip()) or first_name or last_name or ''
                barangay_id = u.get('barangay_id') or ''
                address_text = u.get('address') or ''
                date_joined = u.get('created_at') or ''
                suspended_since = u.get('suspended_at') or ''
                if to_email:
                    send_email_notification(
                        to_email=to_email,
                        subject='🚫 Account Suspended',
                        message=get_email_template(
                            status='suspended',
                            user_first_name=first_name,
                            ticket_number=None,
                            reason=reason,
                            notes=notes,
                            link='suspended',
                            email_address=to_email,
                            status_override='Suspended',
                            full_name=full_name,
                            barangay_id=barangay_id,
                            address_text=address_text,
                            date_joined=date_joined,
                            suspended_since=suspended_since
                        )
                    )
        except Exception as e2:
            print(f"suspend email send err: {e2}")
        return jsonify({"success": True, "message": "User suspended"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.post('/admin/users/<user_id>/unsuspend')
def admin_unsuspend_user(user_id):
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        # Prevent self-unsuspending logic is not necessary, but keep symmetry with suspend
        supabase.table('users').update({
            'is_suspended': False,
            'suspend_reason': None,
            'suspend_notes': None,
            'suspended_at': None
        }).eq('id', user_id).execute()
        # Send unsuspended email notification (with account details)
        try:
            user_q = supabase.table('users').select('email, first_name, last_name, barangay_id, address, created_at').eq('id', user_id).limit(1).execute()
            if user_q.data:
                u = user_q.data[0]
                to_email = u.get('email')
                first_name = (u.get('first_name') or '').strip()
                last_name = (u.get('last_name') or '').strip()
                full_name = (f"{first_name} {last_name}".strip()) or first_name or last_name or ''
                barangay_id = u.get('barangay_id') or ''
                address_text = u.get('address') or ''
                date_joined = u.get('created_at') or ''
                if to_email:
                    send_email_notification(
                        to_email=to_email,
                        subject='✅ Your account is unsuspended',
                        message=get_email_template(
                            status='unsuspended',
                            user_first_name=first_name,
                            ticket_number=None,
                            link='signin',
                            email_address=to_email,
                            status_override='Unsuspended',
                            full_name=full_name,
                            barangay_id=barangay_id,
                            address_text=address_text,
                            date_joined=date_joined
                        )
                    )
        except Exception as e2:
            print(f"unsuspend email send err: {e2}")
        return jsonify({"success": True, "message": "User unsuspended"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# --- Presence / Heartbeat ---
@app.post('/presence/heartbeat')
def presence_heartbeat():
    """Client heartbeat to mark user as online by updating last_seen."""
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    try:
        uid = session["user"]["id"]
        supabase.table('users').update({
            'last_seen': datetime.now().isoformat()
        }).eq('id', uid).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.get('/admin/users/online_status')
def admin_users_online_status():
    """Return {id, last_seen} for all users for presence display. Admin-only."""
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        res = supabase.table('users').select('id, last_seen, is_suspended').execute()
        data = res.data or []
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/test_email_config', methods=['GET'])
def test_email_config():
    """
    Test email configuration - for debugging purposes
    """
    try:
        # Test connection without sending email
        import smtplib
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.quit()

        return jsonify({
            "success": True,
            "message": "Email configuration is working correctly",
            "config": {
                "host": EMAIL_HOST,
                "port": EMAIL_PORT,
                "user": EMAIL_USER[:3] + "***" + EMAIL_USER[-10:]  # Mask email partially
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        email = request.args.get('email', '')
        return render_template("forgot_password.html", email=email)

    email = request.form.get('email', '').strip().lower()
    
    if not email:
        return jsonify({
            'success': False,
            'error': 'Please enter your email address'
        }), 400

    if not validate_email_format(email):
        return jsonify({
            'success': False,
            'error': 'Please enter a valid email address'
        }), 400

    try:
        # First check if user exists by attempting to sign in
        try:
            # This will fail with 'Invalid login credentials' if email doesn't exist
            # We don't care about the actual password here
            supabase.auth.sign_in_with_password({
                'email': email,
                'password': 'dummy_password_123!@#'
            })
        except Exception as auth_error:
            error_msg = str(auth_error).lower()
            if 'email' in error_msg and ('not found' in error_msg or 'invalid' in error_msg):
                return jsonify({
                    'success': False,
                    'error': 'No account found with this email address.'
                }), 404
            # If it's a different error, continue with reset attempt
        
        # Generate reset link with redirect, preserving the exact host used (127.0.0.1 vs localhost)
        reset_url = request.host_url.rstrip('/') + url_for('reset_password')
        # Make sure to use HTTPS in non-local environments
        if ('localhost' not in reset_url and '127.0.0.1' not in reset_url) and reset_url.startswith('http://'):
            reset_url = reset_url.replace('http://', 'https://', 1)
        
        # Log the reset URL for debugging
        print(f"Sending password reset to {email} with redirect to: {reset_url}")
        
        try:
            # Send password reset email through Supabase (Python SDK uses reset_password_email)
            response = supabase.auth.reset_password_email(
                email,
                options={"redirect_to": reset_url}
            )
            
            print(f"Password reset email sent to {email}")
            print(f"Supabase response: {response}")
            
            # Return success response
            return jsonify({
                'success': True,
                'message': 'A password reset link has been sent to your email.'
            })
            
        except Exception as reset_error:
            print(f"Error sending reset email: {str(reset_error)}")
            # Return generic error message for security
            return jsonify({
                'success': False,
                'error': 'Failed to send reset email. Please try again later.'
            }), 500
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"Error in forgot_password: {error_msg}")
        
        # Log the full error for debugging
        import traceback
        traceback.print_exc()
        
        # Return error message
        return jsonify({
            'success': False,
            'error': 'An error occurred. Please try again later.'
        }), 500



@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        # Check if we have the access token in the URL hash (handled by frontend)
        return render_template('reset_password.html')
    
    try:
        print("\n=== Reset Password Request ===")
        print(f"Form Data: {request.form}")
        
        # Get form data
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        access_token = request.form.get('access_token')
        refresh_token = request.form.get('refresh_token')
        
        print(f"Email: {email}")
        print(f"Access Token: {access_token[:10]}..." if access_token else "No Access Token")
        print(f"Refresh Token: {refresh_token[:10]}..." if refresh_token else "No Refresh Token")
        
        # Validate required fields
        if not all([email, new_password, confirm_password, access_token, refresh_token]):
            missing = [field for field in ['email', 'new_password', 'confirm_password', 'access_token', 'refresh_token'] 
                      if not request.form.get(field)]
            error_msg = f'Missing required fields: {", ".join(missing)}'
            print(f"Validation Error: {error_msg}")
            flash(error_msg, 'error')
            return redirect(url_for('reset_password'))
            
        # Check if passwords match
        if new_password != confirm_password:
            print("Error: Passwords do not match")
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('reset_password'))
            
        # Validate password strength
        password_error = validate_password_strength(new_password)
        if password_error:
            print(f"Password Error: {password_error}")
            flash(password_error, 'error')
            return redirect(url_for('reset_password'))
            
        try:
            print("\n=== Starting Password Reset Process ===")
            print(f"Email: {email}")
            print(f"Access token present: {'Yes' if access_token else 'No'}")
            print(f"Access token length: {len(access_token) if access_token else 0}")
            print(f"New password length: {len(new_password) if new_password else 0}")
            
            # Verify we have the required parameters
            if not access_token or not email:
                error_msg = f'Missing required parameters: access_token={access_token is not None}, email={email is not None}'
                print(error_msg)
                return jsonify({
                    'success': False,
                    'error': 'Missing required parameters. Please try the reset link again.'
                }), 400
                
            print(f"Resetting password for email: {email}")
            
            try:
                # Use the existing Supabase client
                if not supabase:
                    raise Exception('Supabase client not initialized')
                
                # Verify the token and get user info
                print("Verifying reset token...")
                try:
                    # Get user info directly with the access token
                    user_response = supabase.auth.get_user(access_token)
                    print(f"User response type: {type(user_response)}")
                    print(f"User response: {user_response}")
                    
                    # If we got here, the token is valid
                    print("Token is valid")
                    
                except Exception as e:
                    print(f"Error verifying token: {str(e)}")
                    print(f"Error type: {type(e).__name__}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        'success': False,
                        'error': 'Invalid or expired reset link. Please request a new password reset.'
                    }), 400
                
                if not user_response or not hasattr(user_response, 'user') or not user_response.user:
                    print("No user in response")
                    return jsonify({
                        'success': False,
                        'error': 'Invalid or expired reset link. Please request a new password reset.'
                    }), 400
                
                current_user = user_response.user
                current_email = getattr(current_user, 'email', '').lower()
                
                print(f"Authenticated as user: {current_email}")
                
                # Verify the email matches
                if current_email != email.lower():
                    error_msg = f'Email does not match: {current_email} (token) != {email} (form)'
                    print(error_msg)
                    return jsonify({
                        'success': False,
                        'error': 'Email does not match the reset token.'
                    }), 400
                
                # Update the password using Supabase Admin API
                print("Updating password using Admin API...")
                try:
                    # Get the user ID from the token
                    user_id = user_response.user.id
                    
                    # Use the Admin API to update the password
                    admin_response = supabase.auth.admin.update_user_by_id(
                        user_id,
                        {"password": new_password}
                    )
                    
                    print(f"Admin update response type: {type(admin_response)}")
                    print(f"Admin update response: {admin_response}")
                    
                    if hasattr(admin_response, 'error') and admin_response.error:
                        error_msg = f'Failed to update password: {admin_response.error.message if hasattr(admin_response.error, "message") else "Unknown error"}'
                        print(error_msg)
                        return jsonify({
                            'success': False,
                            'error': 'Failed to update password. The link may have expired.'
                        }), 400
                    
                    print("Password updated successfully in Supabase Auth")
                    
                    # Sign out all sessions for security
                    print("Signing out all sessions...")
                    try:
                        # Use the admin API to sign out all sessions
                        admin_response = supabase.auth.admin.sign_out(user_id)
                        print("Successfully signed out all sessions")
                    except Exception as signout_error:
                        print(f"Warning: Error during sign out: {str(signout_error)}")
                        # Continue even if sign out fails
                    
                    # Update password in custom users table
                    try:
                        hashed_password = generate_password_hash(new_password)
                        result = supabase.table('users')\
                                         .update({'password': hashed_password})\
                                         .eq('email', email)\
                                         .execute()
                        
                        if hasattr(result, 'error') and result.error:
                            print(f"Warning: Failed to update password in custom users table: {result.error}")
                            # Don't fail the request, just log the error
                        else:
                            print("Password updated in custom users table")
                            
                    except Exception as e:
                        print(f"Error updating custom users table: {str(e)}")
                        # Don't fail the request, just log the error
                    
                    # Return success response
                    return jsonify({
                        'success': True,
                        'message': 'Password updated successfully! You can now log in with your new password.',
                        'redirect': url_for('signin')
                    })
                        
                except Exception as update_error:
                    print(f"Error updating password: {str(update_error)}")
                    print(f"Error type: {type(update_error).__name__}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update password. Please try again.'
                    }), 400
                
            except Exception as e:
                error_msg = f'Password update failed: {str(e)}. The reset link may have expired or is invalid.'
                print(error_msg)
                print(f"Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                raise Exception(error_msg)
            
        except Exception as e:
            # Ensure we don't reference an undefined variable when logging
            error_text = str(e)
            error_text_lower = error_text.lower()
            print(f"Unexpected error in reset_password: {error_text}")
            import traceback
            traceback.print_exc()  # This will print the full traceback to console

            if "invalid" in error_text_lower or "expired" in error_text_lower:
                message = 'Invalid or expired reset link. Please request a new password reset.'
            elif "auth session" in error_text_lower:
                message = 'Your session has expired. Please request a new password reset link.'
            elif "password" in error_text_lower and "weak" in error_text_lower:
                message = 'Password is too weak. Please use a stronger password.'
            else:
                message = f'An error occurred: {error_text}'

            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        print(f"Unexpected error in reset_password: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }), 500

@app.route('/admin/users')
def get_all_users():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        # Fetch all users from the database
        response = supabase.table('users').select('*').order('created_at', desc=True).execute()
        users = response.data if hasattr(response, 'data') else []
        return jsonify(users)
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/admin/users/<user_id>')
def get_user(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        # Fetch a single user by ID
        response = supabase.table('users').select('*').eq('id', user_id).single().execute()
        if hasattr(response, 'data') and response.data:
            return jsonify(response.data)
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        print(f"Error fetching user: {str(e)}")
        return jsonify({'error': 'Failed to fetch user'}), 500

@app.route('/admin/users/add', methods=['POST'])
def add_user():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field.replace("_", " ").title()} is required'}), 400
        
        # Check if email already exists
        existing_user = supabase.table('users').select('email').eq('email', data['email']).execute()
        if hasattr(existing_user, 'data') and existing_user.data:
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Hash the password
        hashed_password = generate_password_hash(data['password'])
        
        # Prepare user data
        user_data = {
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'password_hash': hashed_password,
            'role': data['role'],
            'is_active': True,
            'barangay_id': data.get('barangay_id'),
            'address': data.get('address')
        }
        
        # Insert the new user
        response = supabase.table('users').insert(user_data).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({'success': True, 'message': 'User added successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add user'}), 500
            
    except Exception as e:
        print(f"Error adding user: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while adding the user'}), 500

@app.route('/admin/users/<user_id>/update', methods=['POST'])
def update_user(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    try:
        data = request.get_json()
        
        # Check if user exists
        existing_user = supabase.table('users').select('*').eq('id', user_id).single().execute()
        if not hasattr(existing_user, 'data') or not existing_user.data:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Prepare update data
        update_data = {
            'first_name': data.get('first_name', existing_user.data['first_name']),
            'last_name': data.get('last_name', existing_user.data['last_name']),
            'email': data.get('email', existing_user.data['email']),
            'role': data.get('role', existing_user.data['role']),
            'barangay_id': data.get('barangay_id', existing_user.data.get('barangay_id')),
            'address': data.get('address', existing_user.data.get('address')),
            'is_active': data.get('is_active', existing_user.data.get('is_active', True))
        }
        
        # If password is provided, update it
        if data.get('password'):
            update_data['password_hash'] = generate_password_hash(data['password'])
        
        # Update the user
        response = supabase.table('users').update(update_data).eq('id', user_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return jsonify({'success': True, 'message': 'User updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update user'}), 500
            
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while updating the user'}), 500

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
