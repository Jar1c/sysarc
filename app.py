# from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
# from supabase import create_client, Client
# from werkzeug.security import generate_password_hash, check_password_hash
# from datetime import datetime
# import uuid
# import os
# import re  # Moved to top
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart

# # Email Configuration
# EMAIL_HOST = "smtp.gmail.com"  # o kung ano ang SMTP mo
# EMAIL_PORT = 587
# EMAIL_USER = "brgybaritan1@gmail.com"  # palitan mo
# EMAIL_PASSWORD = "ogqkndywpqznqout"  # gamitin ang App Password, hindi yung regular password

# app = Flask(__name__)
# app.secret_key = os.urandom(24) 

# # Constants
# SUPABASE_URL = "https://vehpeqlxmucsgasedcuh.supabase.co"
# SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZlaHBlcWx4bXVjc2dhc2VkY3VoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjYxNjIyMiwiZXhwIjoyMDcyMTkyMjIyfQ.Xp5JiKtJVPMfZR1ethvOwguVBwjbIYKapi-1STLLfd8"
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



# # Helper functions
# def validate_email_format(email):
#     return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# def validate_password_strength(password):
#     if len(password) < 8:
#         return "Password must be at least 8 characters long!"
#     if not re.search(r"[A-Z]", password):
#         return "Password must contain at least 1 uppercase letter!"
#     if not re.search(r"\d", password):
#         return "Password must contain at least 1 number!"
#     return None

# def get_user_by_email(email):
#     return supabase.table("users").select("*").eq("email", email).execute()

# def get_user_by_barangay_id(bid):
#     return supabase.table("users").select("*").eq("barangay_id", bid).execute()

# # --- NEW: Notification Helper Function ---
# def create_notification(user_id, message, booking_id=None, borrowed_item_id=None, admin_only=False, link=None):
#     try:
#         notification_data = {
#             "id": str(uuid.uuid4()),
#             "user_id": user_id,
#             "message": message,
#             "booking_id": booking_id,
#             "borrowed_item_id": borrowed_item_id,
#             "admin_only": admin_only,
#             "link": link,
#             "is_read": False,
#             "created_at": datetime.now().isoformat()
#         }
#         supabase.table("notifications").insert(notification_data).execute()
#         return True
#     except Exception as e:
#         print(f"Error creating notification: {e}")
#         return False
    
    
# def send_email_notification(to_email, subject, message):
#     """
#     Sends an email notification to the specified email address.
#     """
#     try:
#         msg = MIMEMultipart()
#         msg['From'] = EMAIL_USER
#         msg['To'] = to_email
#         msg['Subject'] = subject

#         msg.attach(MIMEText(message, 'html'))

#         server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
#         server.starttls()
#         server.login(EMAIL_USER, EMAIL_PASSWORD)
#         text = msg.as_string()
#         server.sendmail(EMAIL_USER, to_email, text)
#         server.quit()

#         print(f"Email sent to {to_email}")
#         return True
#     except Exception as e:
#         print(f"Error sending email: {e}")
#         return False



# @app.route("/")
# def home():
#     return render_template("index.html")

# @app.route('/signup', methods=['GET','POST'])
# def signup():
#     if request.method == 'GET':
#         return render_template("signup.html", form={})
    
#     # Process POST request
#     fname = request.form['first_name']
#     lname = request.form['last_name']
#     bid = request.form['barangay_id']
#     email = request.form['email']
#     password = request.form["password"]
#     confirm = request.form['confirm_password']
#     address = request.form['address']

#     form_data = {
#         "first_name": fname,
#         "last_name": lname,
#         "barangay_id": bid,
#         "email": email,
#         "address": address
#     }

#     # Validation
#     if not validate_email_format(email):
#         flash("Invalid email address!", "error")
#         return render_template("signup.html", form=form_data)
    
#     if password_error := validate_password_strength(password):
#         flash(password_error, "error")
#         return render_template("signup.html", form=form_data)
    
#     if len(fname) < 2 or len(lname) < 2:
#         flash("First and last name must be at least 2 characters!", "error")
#         return render_template("signup.html", form=form_data)

#     if len(address) < 5:
#         flash("Address is too short!", "error")
#         return render_template("signup.html", form=form_data)

#     if password != confirm:
#         flash("Passwords do not match!", "error")
#         return render_template("signup.html", form=form_data)
    
#     # Check for existing users
#     if get_user_by_email(email).data:
#         flash("Email already exists!", "error")
#         return render_template("signup.html", form=form_data)

#     if get_user_by_barangay_id(bid).data:
#         flash("Barangay ID already exists!", "error")
#         return render_template("signup.html", form=form_data)

#     # Create user
#     hashed_password = generate_password_hash(password)

#     try:
#         auth_response = supabase.auth.sign_up({
#             "email": email,
#             "password": password
#         })

#         if auth_response.user:
#             supabase.table("users").insert({
#                 "id": str(auth_response.user.id),
#                 "first_name": fname,
#                 "last_name": lname,
#                 "barangay_id": bid,
#                 "email": email,
#                 "password": hashed_password,
#                 "address": address,
#                 "role": "user",
#                 "is_verified": False
#             }).execute()

#             flash("Account created! Please check your email and verify before signing in.", "success")
#             return redirect(url_for("signin"))

#     except Exception as e:
#         error_msg = str(e)
#         if "already registered" in error_msg.lower():
#             flash("Email already exists!", "error")
#         else:
#             flash(f"Registration failed: {error_msg}", "error")
#         return render_template("signup.html", form=form_data)

# @app.route("/verify_success")
# def verify_success():
#     user_id = request.args.get("id")
#     if user_id:
#         supabase.table("users").update({"is_verified": True}).eq("id", user_id).execute()
#     return render_template("verify_success.html")

# @app.route('/signin', methods=['GET', 'POST'])
# def signin():
#     if request.method == 'GET':
#         return render_template("signin.html")
    
#     # Process POST request
#     email = request.form['email'].strip()
#     password = request.form['password']

#     # Validate email format
#     if not validate_email_format(email):
#         flash("Invalid email format!", "error")
#         return redirect(url_for("signin"))

#     try:
#         # Fetch user from custom table
#         user_query = get_user_by_email(email)
#         if not user_query.data:
#             flash("Email not registered!", "error")
#             return redirect(url_for("signin"))

#         user_data = user_query.data[0]

#         # Check password
#         if not check_password_hash(user_data["password"], password):
#             flash("Incorrect password!", "error")
#             return redirect(url_for("signin"))

#         # Sign in via Supabase Auth to check confirmed_at
#         auth_response = supabase.auth.sign_in_with_password({
#             "email": email,
#             "password": password
#         })

#         # Auto-sync verified status
#         if auth_response.user and getattr(auth_response.user, "confirmed_at", None):
#             supabase.table("users").update({"is_verified": True}).eq("email", email).execute()
#             user_data["is_verified"] = True

#         # Check verification in custom table
#         if not user_data.get("is_verified", False):
#             flash("Open your Gmail to verify your account!", "error")
#             return redirect(url_for("signin"))

#         # Set session
#         session['user'] = {
#             'id': user_data['id'],
#             'email': user_data['email'],
#             'first_name': user_data['first_name'],
#             'role': user_data['role']
#         }

#         flash("Login successful!", "success")
#         if user_data['role'] == 'admin':
#             return redirect(url_for('admin_portal'))
#         return redirect(url_for('booking'))

#     except Exception as e:
#         flash("Login failed. Please check your email to verify your account.", "error")
#         return redirect(url_for("signin"))


# @app.route("/booking")
# def booking():
#     if "user" not in session:
#         flash("Please login first!", "error")
#         return redirect(url_for("signin"))
    
#     user_id = session["user"]["id"]

#     # Get user info
#     user_data = supabase.table("users").select("*").eq("id", user_id).execute()
#     user = user_data.data[0] if user_data.data else None

#     # Helper function to parse other_items string
#     def parse_other_items(items_str):
#         if not items_str:
#             return []
#         items = []
#         for item_str in items_str.split(", "):
#             if " x" in item_str:
#                 name, qty_str = item_str.rsplit(" x", 1)
#                 try:
#                     quantity = int(qty_str)
#                     items.append({
#                         "name": name.strip(),
#                         "quantity": quantity
#                     })
#                 except ValueError:
#                     continue
#         return items

#     # My Bookings: Pending or Approved only
#     bookings_data = supabase.table("bookings") \
#         .select("*") \
#         .eq("user_id", user_id) \
#         .in_("status", ["Pending", "Approved"]) \
#         .order("event_date", desc=False) \
#         .execute()
#     bookings = bookings_data.data if bookings_data.data else []

#     for booking in bookings:
#         booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))

#     # Booking History
#     history_data = supabase.table("bookings") \
#         .select("*") \
#         .eq("user_id", user_id) \
#         .in_("status", ["Completed", "Cancelled"]) \
#         .order("event_date", desc=True) \
#         .execute()
#     booking_history = history_data.data if history_data.data else []

#     for booking in booking_history:
#         booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
    
#     # ✅ GET UNREAD NOTIFICATIONS COUNT
#     unread_notif_data = supabase.table("notifications") \
#         .select("id") \
#         .eq("user_id", user_id) \
#         .eq("is_read", False) \
#         .execute()
#     unread_count = len(unread_notif_data.data) if unread_notif_data.data else 0

#     # ✅ GET RECENT NOTIFICATIONS LIST (e.g., last 10)
#     notifications_data = supabase.table("notifications") \
#         .select("*") \
#         .eq("user_id", user_id) \
#         .order("created_at", desc=True) \
#         .limit(10) \
#         .execute()
#     notifications = notifications_data.data if notifications_data.data else []

#     return render_template(
#         "booking.html", 
#         user=user, 
#         bookings=bookings, 
#         booking_history=booking_history,
#         unread_count=unread_count,
#         notifications=notifications  # ✅ ITO ANG IDINAGDAG
#     )

# @app.route("/booking_details/<booking_id>")
# def booking_details(booking_id):
#     if "user" not in session:
#         return jsonify({"success": False, "message": "Please login first"})
    
#     try:
#         # Kunin ang booking details
#         booking_data = supabase.table("bookings").select("*").eq("id", booking_id).eq("user_id", session["user"]["id"]).execute()
        
#         if not booking_data.data:
#             return jsonify({"success": False, "message": "Booking not found"})
        
#         booking = booking_data.data[0]
        
#         # Kunin ang listahan ng lahat ng active equipment para i-map (kasama na ang category_id)
#         try:
#             equipment_data = supabase.table("inventory").select("id, name, category_id").eq("is_active", True).execute()
#             # Gumawa ng map: name → category_id (para sa matching)
#             name_to_category = {item['name']: item['category_id'] for item in equipment_data.data} if equipment_data.data else {}
#         except Exception as e:
#             name_to_category = {}
#             print(f"Error fetching equipment map: {e}")

#         # I-decode ang other_items field at i-assign ang category_id
#         equipment_list = []
#         if booking.get("other_items"):
#             for item_str in booking["other_items"].split(", "):
#                 if " x" in item_str:
#                     name_part, qty_str = item_str.rsplit(" x", 1)
#                     name = name_part.strip()  # Important: i-strip para walang space
#                     try:
#                         qty = int(qty_str)
#                         # Hanapin ang category_id base sa name
#                         category_id = name_to_category.get(name, "cat6")  # Default: cat6 (Other)
#                         equipment_list.append({
#                             "name": name,
#                             "quantity": qty,
#                             "category_id": category_id  # ✅ Ito ang idinagdag para sa JS emoji logic
#                         })
#                     except ValueError:
#                         continue

#         # I-override ang booking data para isama ang decoded equipment (kasama category_id)
#         booking["equipment_list"] = equipment_list

#         return jsonify({"success": True, "data": booking})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)})


# @app.route('/cancel_booking', methods=['POST'])
# def cancel_booking():
#     if "user" not in session:
#         return jsonify({"success": False, "message": "Please login first!"})
    
#     try:
#         data = request.get_json()
#         booking_id = data.get('booking_id')
        
#         if not booking_id:
#             return jsonify({"success": False, "message": "No booking ID provided"})
        
#         # Update status to Cancelled instead of deleting
#         supabase.table("bookings") \
#             .update({"status": "Cancelled"}) \
#             .eq("id", booking_id) \
#             .eq("user_id", session["user"]["id"]) \
#             .execute()
        
#         # --- NEW: Create Notification for User ---
#         create_notification(
#             user_id=session["user"]["id"],
#             message=f"Your booking (ID: {booking_id}) has been cancelled.",
#             booking_id=booking_id,
#             link=url_for('booking_details', booking_id=booking_id)
#         )

#         # --- NEW: Send Email Notification ---
#         # Kunin ang email at name ng user
#         user_data = supabase.table("users").select("email, first_name").eq("id", session["user"]["id"]).execute()
#         if user_data.data:
#             user_email = user_data.data[0]['email']
#             user_first_name = user_data.data[0]['first_name']

#             send_email_notification(
#                 to_email=user_email,
#                 subject="Booking Cancelled",
#                 message=f"""
#                 <h3>Hello {user_first_name},</h3>
#                 <p>Your booking has been successfully cancelled.</p>
#                 <p><strong>Booking ID:</strong> {booking_id}</p>
#                 <p>If this was a mistake, please create a new booking.</p>
#                 <p>Thank you!</p>
#                 """
#             )
        
#         return jsonify({"success": True, "message": "Booking cancelled successfully"})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {str(e)}"})

# @app.route("/booking2", methods=["GET"])
# def booking2_page():
#     if "user" not in session:
#         flash("Please login first!", "error")
#         return redirect(url_for("signin"))
    
#     # ✅ ILALAGAY MO ANG CODE DITO ✅
#     try:
#         equipment_data = supabase.table("inventory").select("*").eq("is_active", True).execute()
#         equipment_list = equipment_data.data if equipment_data.data else []

#         # I-group ang equipment sa categories
#         categories = {
#             "cat1": {"name": "🏕️ Tents & Shelters", "items": []},
#             "cat2": {"name": "🪑 Furniture", "items": []},
#             "cat3": {"name": "🏀 Sports Equipment", "items": []},
#             "cat4": {"name": "🎤 Sound Equipment", "items": []},
#             "cat5": {"name": "🍳 Cooking Equipment", "items": []},
#             "cat6": {"name": "📦 Other Equipment", "items": []}
#         }

#         for item in equipment_list:
#             cat_id = item.get("category_id", "cat6")  # default to "Other"
#             if cat_id in categories:
#                 categories[cat_id]["items"].append(item)
#             else:
#                 categories["cat6"]["items"].append(item)

#         # I-filter ang categories na may laman
#         active_categories = {k: v for k, v in categories.items() if v["items"]}
#     except Exception as e:
#         active_categories = {}
#         print(f"Error fetching equipment: {e}")

#     return render_template("booking2.html", active_categories=active_categories)

# @app.route("/booking3", methods=["GET", "POST"])
# def booking3():
#     if "user" not in session:
#         flash("Please login first!", "error")
#         return redirect(url_for("signin"))

#     if request.method == "GET":
#         try:
#             equipment_data = supabase.table("inventory").select("*").eq("is_active", True).execute()
#             equipment_list = equipment_data.data if equipment_data.data else []

#             # I-group ang equipment sa categories
#             categories = {
#                 "cat1": {"name": "🏕️ Tents & Shelters", "items": []},
#                 "cat2": {"name": "🪑 Furniture", "items": []},
#                 "cat3": {"name": "🏀 Sports Equipment", "items": []},
#                 "cat4": {"name": "🎤 Sound Equipment", "items": []},
#                 "cat5": {"name": "🍳 Cooking Equipment", "items": []},
#                 "cat6": {"name": "📦 Other Equipment", "items": []}
#             }

#             for item in equipment_list:
#                 cat_id = item.get("category_id", "cat6")  # default to "Other"
#                 if cat_id in categories:
#                     categories[cat_id]["items"].append(item)
#                 else:
#                     categories["cat6"]["items"].append(item)

#             # I-filter ang categories na may laman
#             active_categories = {k: v for k, v in categories.items() if v["items"]}
#         except Exception as e:
#             active_categories = {}
#             print(f"Error fetching equipment: {e}")

#         return render_template("booking3.html", active_categories=active_categories)
    
#     # Process POST request
#     user_id = session["user"]["id"]

#     # Check if user already has a pending/approved booking
#     existing_booking = supabase.table("bookings") \
#         .select("*") \
#         .eq("user_id", user_id) \
#         .in_("status", ["Pending", "Approved"]) \
#         .execute()

#     if existing_booking.data:
#         flash("You already booked! You can't book multiple.", "error")
#         return redirect(url_for("booking3"))

#     # ✅ Kunin muna ang listahan ng lahat ng active equipment para i-map
#     try:
#         equipment_data = supabase.table("inventory").select("id, name").eq("is_active", True).execute()
#         equipment_map = {item['id']: item['name'] for item in equipment_data.data} if equipment_data.data else {}
#     except Exception as e:
#         equipment_map = {}
#         print(f"Error fetching equipment map: {e}")

#     # ✅ I-store ang quantities sa dictionary
#     equipment_quantities = {}

#     for item_id in equipment_map.keys():
#         qty_key = f"{item_id}_qty"  # Hal. "abc123_qty"
#         qty = int(request.form.get(qty_key, 0) or 0)
#         if qty > 0:
#             equipment_quantities[item_id] = {
#                 "name": equipment_map[item_id],
#                 "quantity": qty
#             }

#     # ✅ I-combine ang lahat ng selected equipment (both main list and "other" items)
#     all_equipment_list = []

#     # Add from main equipment list
#     for item_id, info in equipment_quantities.items():
#         all_equipment_list.append(f"{info['name']} x{info['quantity']}")

#     # Add from "Other Equipment" section
#     other_item_name = request.form.get("other_items", "").strip()
#     other_qty = int(request.form.get("others_qty", 0) or 0)
#     if other_item_name and other_qty > 0:
#         all_equipment_list.append(f"{other_item_name} x{other_qty}")

#     # ✅ I-combine lahat
#     all_other_items = ", ".join(all_equipment_list) if all_equipment_list else ""
#     total_others_qty = sum(info['quantity'] for info in equipment_quantities.values()) + (other_qty or 0)

#     # Collect form data
#     event_date = request.form.get("event_date", "").strip()
#     contact_number = request.form.get("phone", "").strip()
#     email = request.form.get("email", "").strip()

#     # Generate IDs
#     booking_id = str(uuid.uuid4())
#     ticket_number = "TKT-" + str(uuid.uuid4())[:8].upper()

#     # ✅ KUNIN ANG USER'S FIRST_NAME AT LAST_NAME MULA SA DATABASE
#     try:
#         user_response = supabase.table("users").select("first_name, last_name").eq("id", user_id).execute()
#         user_data = user_response.data[0] if user_response.data else {}
#         user_first_name = user_data.get("first_name", "")
#         user_last_name = user_data.get("last_name", "")
#     except Exception as e:
#         # Kung may error, gamitin ang empty string para hindi mabigong mag-insert
#         user_first_name = ""
#         user_last_name = ""
#         print(f"Error fetching user data: {e}")

#     # ✅ Gumamit na ng bagong `all_other_items` at `total_others_qty`
#     # ✅ IDINAGDAG NA ANG first_name AT last_name
#     booking_data = {
#         "id": booking_id,
#         "user_id": user_id,
#         "ticket_number": ticket_number,
#         "first_name": user_first_name,  # ✅ ADDED
#         "last_name": user_last_name,   # ✅ ADDED
#         "event_date": event_date,
#         "contact_number": contact_number,
#         "email": email,
#         "others_qty": total_others_qty,      # ← ITO ANG TOTAL QUANTITY
#         "other_items": all_other_items,      # ← ITO ANG LAHAT NG ITEM DESCRIPTIONS
#         "status": "Pending",
#         "created_at": datetime.now().isoformat()
#     }

#     try:
#         supabase.table("bookings").insert(booking_data).execute()
#         flash(f"Booking submitted successfully! Ticket: {ticket_number}", "success")
        
#         # --- NEW: Create Notification for User ---
#         create_notification(
#             user_id=user_id,
#             message=f"Your booking request (Ticket: {ticket_number}) has been submitted and is now pending approval.",
#             booking_id=booking_id,
#             link=url_for('booking_details', booking_id=booking_id)
#         )

#         send_email_notification(
#             to_email=email,  # kunin mo sa form data
#             subject="Booking Submitted - Pending Approval",
#             message=f"""
#             <h3>Hello {user_first_name},</h3>
#             <p>Your booking request has been submitted successfully!</p>
#             <p><strong>Ticket ID:</strong> {ticket_number}</p>
#             <p><strong>Status:</strong> Pending Approval</p>
#             <p>You will be notified once your booking is approved or rejected.</p>
#             <p>Thank you!</p>
#             """
#         )
        
#         return redirect(url_for("booking3"))
#     except Exception as e:
#         flash(f"Unexpected error: {str(e)}", "error")
#         return redirect(url_for("booking3"))


# @app.route("/book_event", methods=["POST"])
# def book_event():
#     if "user" not in session:
#         flash("Please login first!", "error")
#         return redirect(url_for("signin"))

#     user_id = session["user"]["id"]

#     # Check if user already has a pending or approved booking
#     existing_booking = supabase.table("bookings") \
#         .select("*") \
#         .eq("user_id", user_id) \
#         .in_("status", ["Pending", "Approved"]) \
#         .execute()

#     if existing_booking.data:
#         flash("You already booked! You can't book multiple.", "error")
#         return redirect(url_for("booking2_page"))

#     try:
#         # Get form data (event info, contact info)
#         event_type = request.form.get("event_type", "").strip()
#         event_date = request.form.get("event_date", "").strip()
#         contact_number = request.form.get("phone", "").strip()
#         email = request.form.get("email", "").strip()

#         # ✅ Kunin muna ang listahan ng lahat ng active equipment para i-map
#         try:
#             equipment_data = supabase.table("inventory").select("id, name").eq("is_active", True).execute()
#             equipment_map = {item['id']: item['name'] for item in equipment_data.data} if equipment_data.data else {}
#         except Exception as e:
#             equipment_map = {}
#             print(f"Error fetching equipment map: {e}")

#         # ✅ I-store ang quantities sa dictionary
#         equipment_quantities = {}

#         for item_id in equipment_map.keys():
#             qty_key = f"{item_id}_qty"  # Hal. "abc123_qty"
#             qty = int(request.form.get(qty_key, 0) or 0)
#             if qty > 0:
#                 equipment_quantities[item_id] = {
#                     "name": equipment_map[item_id],
#                     "quantity": qty
#                 }

#         # ✅ I-combine ang lahat ng selected equipment (both main list and "other" items)
#         all_equipment_list = []

#         # Add from main equipment list
#         for item_id, info in equipment_quantities.items():
#             all_equipment_list.append(f"{info['name']} x{info['quantity']}")

#         # Add from "Other Equipment" section
#         main_other_item = request.form.get("other_items", "").strip()
#         main_other_qty = request.form.get("other_qty", "0").strip()
        
#         if main_other_item and int(main_other_qty) > 0:
#             all_equipment_list.append(f"{main_other_item} x{main_other_qty}")
        
#         # Kunin ang mga dynamically added other items
#         additional_items = request.form.getlist("other_items[]")
#         for item in additional_items:
#             if item.strip():  # Kung may laman
#                 all_equipment_list.append(item.strip())

#         # I-combine lahat
#         all_other_items = ", ".join(all_equipment_list) if all_equipment_list else ""
        
#         # Calculate total others quantity
#         others_qty = sum(int(qty) for item in all_equipment_list for qty in item.split('x')[1:] if 'x' in item)

#         # Generate IDs
#         booking_id = str(uuid.uuid4())
#         ticket_number = "TKT-" + str(uuid.uuid4())[:8].upper()

#         # ✅ KUNIN ANG USER'S FIRST_NAME AT LAST_NAME MULA SA DATABASE
#         try:
#             user_response = supabase.table("users").select("first_name, last_name").eq("id", user_id).execute()
#             user_data = user_response.data[0] if user_response.data else {}
#             user_first_name = user_data.get("first_name", "")
#             user_last_name = user_data.get("last_name", "")
#         except Exception as e:
#             # Kung may error, gamitin ang empty string para hindi mabigong mag-insert
#             user_first_name = ""
#             user_last_name = ""
#             print(f"Error fetching user  {e}")

#         # ✅ Gumamit na ng bagong `all_other_items` at `total_others_qty`
#         # ✅ IDINAGDAG NA ANG first_name AT last_name
#         booking_data = {
#             "id": booking_id,
#             "user_id": user_id,
#             "ticket_number": ticket_number,
#             "first_name": user_first_name,  # ✅ ADDED
#             "last_name": user_last_name,   # ✅ ADDED
#             "event_type": event_type,
#             "event_date": event_date,
#             "contact_number": contact_number,
#             "email": email,
#             "others_qty": others_qty,      # ← ITO ANG TOTAL QUANTITY
#             "other_items": all_other_items,   # ← ITO ANG LAHAT NG ITEM DESCRIPTIONS
#             "status": "Pending",
#             "created_at": datetime.now().isoformat()
#         }

#         # Insert into Supabase
#         supabase.table("bookings").insert(booking_data).execute()

#         flash(f"Booking submitted successfully! Ticket: {ticket_number}", "success")

#         # --- NEW: Create Notification for User ---
#         create_notification(
#             user_id=user_id,
#             message=f"Your event booking request (Ticket: {ticket_number}) has been submitted and is now pending approval.",
#             booking_id=booking_id,
#             link=url_for('booking_details', booking_id=booking_id)
#         )

#         send_email_notification(
#             to_email=email,
#             subject="Event Booking Submitted - Pending Approval",
#             message=f"""
#             <h3>Hello {user_first_name},</h3>
#             <p>Your event booking request has been submitted successfully!</p>
#             <p><strong>Ticket ID:</strong> {ticket_number}</p>
#             <p><strong>Event Type:</strong> {event_type}</p>
#             <p><strong>Event Date:</strong> {event_date}</p>
#             <p><strong>Status:</strong> Pending Approval</p>
#             <p>You will be notified once your booking is approved or rejected.</p>
#             <p>Thank you!</p>
#             """
#         )

#         admin_users = supabase.table("users").select("id").eq("role", "admin").execute()
#         if admin_users.data:
#             for admin in admin_users.data:
#                 create_notification(
#                     user_id=admin['id'],
#                     message=f"New event booking from {user_first_name} {user_last_name} (Ticket: {ticket_number})",
#                     admin_only=True,
#                     link=url_for('admin_portal') + "#pending-approvals"
#                 )

#         return redirect(url_for("booking2_page"))

#     except Exception as e:
#         flash(f"Unexpected error: {str(e)}", "error")
#         return redirect(url_for("booking2_page"))
    


# @app.route("/admin_portal")
# def admin_portal():
#     if "user" not in session or session["user"]["role"] != "admin":
#         flash("Admins only!", "error")
#         return redirect(url_for("admin_login"))
    
#     try:
#         # Kunin ang mga stats para sa admin dashboard
#         total_bookings = supabase.table("bookings").select("*").execute()
#         total_users = supabase.table("users").select("*").execute()
        
#         # Kunin ang mga pending approvals KASAMA ANG USER INFO
#         pending_approvals_data = supabase.table("bookings").select("*, users(first_name, last_name)").eq("status", "Pending").execute()
        
#         # ✅ Helper function to parse other_items
#         def parse_other_items(items_str):
#             if not items_str:
#                 return []
#             items = []
#             for item_str in items_str.split(", "):
#                 if " x" in item_str:
#                     name, qty_str = item_str.rsplit(" x", 1)
#                     try:
#                         quantity = int(qty_str)
#                         items.append({
#                             "name": name.strip(),
#                             "quantity": quantity
#                         })
#                     except ValueError:
#                         continue
#             return items

#         # ✅ Parse other_items for each pending approval
#         pending_approvals = []
#         if pending_approvals_data.data:
#             for booking in pending_approvals_data.data:
#                 booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
#                 pending_approvals.append(booking)

#         # Kunin ang lahat ng bookings
#         all_bookings_data = supabase.table("bookings").select("*, users(first_name, last_name)").execute()
#         all_bookings = []
#         if all_bookings_data.data:
#             for booking in all_bookings_data.data:
#                 booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
#                 all_bookings.append(booking)

#         # Kunin ang lahat ng equipment
#         equipment_data = supabase.table("inventory").select("*").execute()
#         equipment_items = equipment_data.data if equipment_data.data else []
        
#         # I-prepare ang data
#         stats = {
#             "total_bookings": len(total_bookings.data) if total_bookings.data else 0,
#             "total_users": len(total_users.data) if total_users.data else 0,
#             "pending_approvals": len(pending_approvals),
#             "total_equipment": len(equipment_items)
#         }
        
#         # ✅ GET ADMIN NOTIFICATIONS
#         admin_notif_data = supabase.table("notifications") \
#             .select("*") \
#             .or_("admin_only.eq.true,user_id.eq." + session["user"]["id"]) \
#             .eq("is_read", False) \
#             .order("created_at", desc=True) \
#             .limit(10) \
#             .execute()
#         admin_notifications = admin_notif_data.data if admin_notif_data.data else []
#         unread_admin_count = len(admin_notif_data.data) if admin_notif_data.data else 0

#         return render_template(
#             "admin_portal.html", 
#             stats=stats,
#             pending_approvals=pending_approvals,
#             all_bookings=all_bookings,
#             equipment_items=equipment_items,
#             admin_notifications=admin_notifications,  # ✅ ITO ANG IDINAGDAG
#             unread_admin_count=unread_admin_count   # ✅ ITO ANG IDINAGDAG
#         )
    
#     except Exception as e:
#         flash(f"Error loading admin portal: {str(e)}", "error")
#         return redirect(url_for("admin_login"))

# @app.route("/admin/booking_details/<booking_id>")
# def admin_booking_details(booking_id):
#     if "user" not in session or session["user"]["role"] != "admin":
#         return jsonify({"success": False, "message": "Unauthorized"})
    
#     try:
#         # Kunin ang booking details kasama ang user info
#         booking_data = supabase.table("bookings").select("*, users(first_name, last_name, barangay_id)").eq("id", booking_id).execute()
        
#         if not booking_data.data:
#             return jsonify({"success": False, "message": "Booking not found"})
        
#         booking = booking_data.data[0]

#         # Kunin ang listahan ng lahat ng active equipment para i-map (kasama na ang category_id)
#         try:
#             equipment_data = supabase.table("inventory").select("id, name, category_id").eq("is_active", True).execute()
#             # Gumawa ng map: name → category_id (para sa matching)
#             name_to_category = {item['name']: item['category_id'] for item in equipment_data.data} if equipment_data.data else {}
#         except Exception as e:
#             name_to_category = {}
#             print(f"Error fetching equipment map: {e}")

#         # I-decode ang other_items field at i-assign ang category_id
#         equipment_list = []
#         if booking.get("other_items"):
#             for item_str in booking["other_items"].split(", "):
#                 if " x" in item_str:
#                     name_part, qty_str = item_str.rsplit(" x", 1)
#                     name = name_part.strip()  # Important: i-strip para walang space
#                     try:
#                         qty = int(qty_str)
#                         # Hanapin ang category_id base sa name
#                         category_id = name_to_category.get(name, "cat6")  # Default: cat6 (Other)
#                         equipment_list.append({
#                             "name": name,
#                             "quantity": qty,
#                             "category_id": category_id  # ✅ Ito ang idinagdag para sa JS emoji logic
#                         })
#                     except ValueError:
#                         continue

#         # I-override ang booking data para isama ang decoded equipment (kasama category_id)
#         booking["equipment_list"] = equipment_list

#         return jsonify({"success": True, "data": booking})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)})

# @app.route("/admin/approve_booking", methods=["POST"])
# def admin_approve_booking():
#     if "user" not in session or session["user"]["role"] != "admin":
#         return jsonify({"success": False, "message": "Unauthorized"})
    
#     try:
#         data = request.get_json()
#         booking_id = data.get('booking_id')
        
#         if not booking_id:
#             return jsonify({"success": False, "message": "No booking ID provided"})
        
#         # I-update ang status ng booking
#         supabase.table("bookings") \
#             .update({"status": "Approved"}) \
#             .eq("id", booking_id) \
#             .execute()
        
#         # --- NEW: Fetch user_id and notify user ---
#         booking_data = supabase.table("bookings").select("user_id, ticket_number, email, first_name").eq("id", booking_id).execute()
#         if booking_data.data:
#             user_id = booking_data.data[0]['user_id']
#             ticket_number = booking_data.data[0]['ticket_number']
#             user_email = booking_data.data[0]['email']
#             user_first_name = booking_data.data[0]['first_name']

#             create_notification(
#                 user_id=user_id,
#                 message=f"Great news! Your booking request (Ticket: {ticket_number}) has been approved.",
#                 booking_id=booking_id,
#                 link=url_for('booking_details', booking_id=booking_id)
#             )

#             # --- NEW: Send Email Notification ---
#             send_email_notification(
#                 to_email=user_email,
#                 subject="Booking Approved!",
#                 message=f"""
#                 <h3>Hello {user_first_name},</h3>
#                 <p>Great news! Your booking has been approved.</p>
#                 <p><strong>Ticket ID:</strong> {ticket_number}</p>
#                 <p>You may now proceed with your plans.</p>
#                 <p>Thank you for using our booking system!</p>
#                 """
#             )
        
#         return jsonify({"success": True, "message": "Booking approved successfully"})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {str(e)}"})

# @app.route("/admin/reject_booking", methods=["POST"])
# def admin_reject_booking():
#     if "user" not in session or session["user"].get("role") != "admin":
#         return jsonify({"success": False, "message": "Unauthorized"}), 403

#     try:
#         data = request.get_json()
#         booking_id = data.get("booking_id")

#         if not booking_id:
#             return jsonify({"success": False, "message": "No booking ID provided"}), 400

#         response = supabase.table("bookings") \
#             .update({"status": "Rejected"}) \
#             .eq("id", booking_id) \
#             .execute()

#         if not response.data:
#             return jsonify({"success": False, "message": "Booking not found"}), 404

#         # --- NEW: Fetch user_id and notify user ---
#         booking_data = supabase.table("bookings").select("user_id, ticket_number, email, first_name").eq("id", booking_id).execute()
#         if booking_data.data:
#             user_id = booking_data.data[0]['user_id']
#             ticket_number = booking_data.data[0]['ticket_number']
#             user_email = booking_data.data[0]['email']
#             user_first_name = booking_data.data[0]['first_name']

#             create_notification(
#                 user_id=user_id,
#                 message=f"We're sorry, your booking request (Ticket: {ticket_number}) has been rejected.",
#                 booking_id=booking_id,
#                 link=url_for('booking_details', booking_id=booking_id)
#             )

#             # --- NEW: Send Email Notification ---
#             send_email_notification(
#                 to_email=user_email,
#                 subject="Booking Rejected",
#                 message=f"""
#                 <h3>Hello {user_first_name},</h3>
#                 <p>We're sorry, but your booking request has been rejected.</p>
#                 <p><strong>Ticket ID:</strong> {ticket_number}</p>
#                 <p>Please contact the administrator for more information.</p>
#                 <p>Thank you for your understanding.</p>
#                 """
#             )

#         return jsonify({"success": True, "message": "Booking rejected successfully"})

#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# # Equipment Management Routes
# @app.route("/admin/equipment")
# def admin_equipment_management():
#     if "user" not in session or session["user"]["role"] != "admin":
#         flash("Admins only!", "error")
#         return redirect(url_for("admin_login"))
    
#     try:
#         # Kunin ang lahat ng equipment
#         equipment_data = supabase.table("inventory").select("*").execute()
#         equipment_items = equipment_data.data if equipment_data.data else []
        
#         return render_template(
#             "admin_portal.html",  # Dapat naka-set na ito sa iyong admin portal
#             equipment_items=equipment_items,
#             active_tab="equipment-management"  # Para ma-highlight ang tamang tab
#         )
    
#     except Exception as e:
#         flash(f"Error loading equipment: {str(e)}", "error")
#         return redirect(url_for("admin_portal"))

# @app.route("/admin/equipment/<item_id>")
# def get_equipment_item(item_id):
#     if "user" not in session or session["user"]["role"] != "admin":
#         return jsonify({"success": False, "message": "Unauthorized"})
    
#     try:
#         equipment_data = supabase.table("inventory").select("*").eq("id", item_id).execute()
        
#         if not equipment_data.data:
#             return jsonify({"success": False, "message": "Equipment not found"})
        
#         return jsonify({"success": True, "item": equipment_data.data[0]})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)})

# @app.route("/admin/equipment/add", methods=["POST"])
# def add_equipment():
#     if "user" not in session or session["user"]["role"] != "admin":
#         return jsonify({"success": False, "message": "Unauthorized"})
    
#     try:
#         data = request.get_json()
        
#         # Validation
#         required_fields = ["name", "category_id", "quantity_total", "quantity_available"]
#         for field in required_fields:
#             if not data.get(field):
#                 return jsonify({"success": False, "message": f"Missing required field: {field}"})
        
#         # Create equipment data
#         equipment_data = {
#             "id": str(uuid.uuid4()),
#             "name": data["name"],
#             "category_id": data["category_id"],
#             "description": data.get("description", ""),
#             "quantity_total": int(data["quantity_total"]),
#             "quantity_available": int(data["quantity_available"]),
#             "is_active": data.get("is_active", True),
#             "created_at": datetime.now().isoformat()
#         }
        
#         # Insert into database
#         supabase.table("inventory").insert(equipment_data).execute()
        
#         return jsonify({"success": True, "message": "Equipment added successfully"})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {str(e)}"})

# @app.route("/admin/equipment/update", methods=["POST"])
# def update_equipment():
#     if "user" not in session or session["user"]["role"] != "admin":
#         return jsonify({"success": False, "message": "Unauthorized"})
    
#     try:
#         data = request.get_json()
#         item_id = data.get("id")
        
#         if not item_id:
#             return jsonify({"success": False, "message": "No equipment ID provided"})
        
#         # Prepare update data
#         update_data = {
#             "name": data["name"],
#             "category_id": data["category_id"],
#             "description": data.get("description", ""),
#             "quantity_total": int(data["quantity_total"]),
#             "quantity_available": int(data["quantity_available"]),
#             "is_active": data.get("is_active", True)
#         }
        
#         # Update database
#         supabase.table("inventory").update(update_data).eq("id", item_id).execute()
        
#         return jsonify({"success": True, "message": "Equipment updated successfully"})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {str(e)}"})

# @app.route("/admin/equipment/delete", methods=["POST"])
# def delete_equipment():
#     if "user" not in session or session["user"]["role"] != "admin":
#         return jsonify({"success": False, "message": "Unauthorized"})
    
#     try:
#         data = request.get_json()
#         item_id = data.get("id")
        
#         if not item_id:
#             return jsonify({"success": False, "message": "No equipment ID provided"})
        
#         # Delete from database
#         supabase.table("inventory").delete().eq("id", item_id).execute()
        
#         return jsonify({"success": True, "message": "Equipment deleted successfully"})
    
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {str(e)}"})


# @app.route("/admin_login", methods=["GET", "POST"])
# def admin_login():
#     if request.method == "GET":
#         return render_template("admin_login.html")
    
#     # Process POST request
#     email = request.form["email"].strip().lower()
#     password = request.form["password"]

#     try:
#         # Get admin from custom users table
#         response = supabase.table("users").select("*").eq("email", email).eq("role", "admin").execute()

#         if not response.data:
#             flash("Admin not found!", "error")
#             return redirect(url_for("admin_login"))

#         user = response.data[0]

#         # Check if verified
#         if not user["is_verified"]:
#             flash("Admin not verified yet!", "error")
#             return redirect(url_for("admin_login"))

#         # Check password
#         if not check_password_hash(user["password"], password):
#             flash("Invalid password!", "error")
#             return redirect(url_for("admin_login"))

#         session["user"] = {
#             "id": user["id"],
#             "email": user["email"],
#             "first_name": user["first_name"],
#             "role": user["role"]
#         }
#         return redirect(url_for("admin_portal"))

#     except Exception as e:
#         flash(f"Login failed: {str(e)}", "error")
#         return redirect(url_for("admin_login"))

# @app.route('/adminlogout', methods=['POST'])
# def admin_logout():
#     session.clear()
#     flash("You have been logged out.", "success")
#     return redirect(url_for('admin_login'))

# @app.route('/logout', methods=['POST'])
# def logout():
#     session.pop("user", None)
#     flash("You have been logged out.", "success")
#     return redirect(url_for('home'))

# @app.route("/signout", methods=["POST"])
# def signout():
#     session.pop("user", None)
#     return redirect(url_for("admin_login"))


# @app.route('/mark_notifications_as_read', methods=['POST'])
# def mark_notifications_as_read():
#     if "user" not in session:
#         return jsonify({"success": False, "message": "Please login first!"})

#     try:
#         user_id = session["user"]["id"]
#         supabase.table("notifications") \
#             .update({"is_read": True}) \
#             .eq("user_id", user_id) \
#             .eq("is_read", False) \
#             .execute()

#         return jsonify({"success": True, "message": "Notifications marked as read"})
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {str(e)}"})
    

# @app.route('/get_unread_count', methods=['GET'])
# def get_unread_count():
#     if "user" not in session:
#         return jsonify({"success": False, "unread_count": 0})

#     try:
#         user_id = session["user"]["id"]
#         unread_notif_data = supabase.table("notifications") \
#             .select("id") \
#             .eq("user_id", user_id) \
#             .eq("is_read", False) \
#             .execute()
#         unread_count = len(unread_notif_data.data) if unread_notif_data.data else 0
#         return jsonify({"success": True, "unread_count": unread_count})
#     except Exception as e:
#         return jsonify({"success": False, "unread_count": 0})





# if __name__ == "__main__":

#     app.run(host='127.0.0.1', port=5000, debug=True)


from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import os
import re  # Moved to top
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email Configuration
EMAIL_HOST = "smtp.gmail.com"  # o kung ano ang SMTP mo
EMAIL_PORT = 587
EMAIL_USER = "brgybaritan1@gmail.com"  # palitan mo
EMAIL_PASSWORD = "ogqkndywpqznqout"  # gamitin ang App Password, hindi yung regular password

app = Flask(__name__)
app.secret_key = os.urandom(24) 

# Constants
SUPABASE_URL = "https://vehpeqlxmucsgasedcuh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZlaHBlcWx4bXVjc2dhc2VkY3VoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjYxNjIyMiwiZXhwIjoyMDcyMTkyMjIyfQ.Xp5JiKtJVPMfZR1ethvOwguVBwjbIYKapi-1STLLfd8"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



# Helper functions
def validate_email_format(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_password_strength(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long!"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least 1 uppercase letter!"
    if not re.search(r"\d", password):
        return "Password must contain at least 1 number!"
    return None

def get_user_by_email(email):
    return supabase.table("users").select("*").eq("email", email).execute()

def get_user_by_barangay_id(bid):
    return supabase.table("users").select("*").eq("barangay_id", bid).execute()

# --- NEW: Notification Helper Function ---
def create_notification(user_id, message, booking_id=None, borrowed_item_id=None, admin_only=False, link=None):
    try:
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
    
def get_email_template(status, user_first_name, ticket_number, event_date=None, event_type=None, reason=None):
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
    
    reason_row = ""
    if status == "rejected":
        reason_row = f'''
        <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Reason:</td>
            <td style="padding: 10px 0; text-align: left; font-weight: 500;">{reason or "Please contact the administrator for more information."}</td>
        </tr>'''

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
                            <h3 style="color: #023e8a; margin: 0 0 15px 0; font-size: 18px; text-align: center;">Booking Details</h3>
                            
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; font-weight: 600; color: #555; width: 140px; text-align: left;">Ticket ID:</td>
                                    <td style="padding: 10px 0; text-align: left; font-weight: 500;">{ticket_number}</td>
                                </tr>
                                {event_type_row}
                                {event_date_row}
                                {reason_row}
                            </table>
                        </td>
                    </tr>
                </table>

                <!-- Action Button (Bulletproof) -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 30px auto; max-width: 220px;">
                    <tr>
                        <td align="center" style="background-color: #023e8a; border-radius: 6px; text-align: center; border: 2px solid #023e8a;">
                            <a href="https://brgybaritan.onrender.com/signin" 
                               style="display: block; padding: 14px 20px; color: white; text-decoration: none; font-weight: 600; font-size: 16px; letter-spacing: 0.5px; border-radius: 50px;">
                                View Booking Details
                            </a>
                        </td>
                    </tr>
                </table>

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
        # Fetch user from custom table
        user_query = get_user_by_email(email)
        if not user_query.data:
            flash("Email not registered!", "error")
            return redirect(url_for("signin"))

        user_data = user_query.data[0]

        # Check password
        if not check_password_hash(user_data["password"], password):
            flash("Incorrect password!", "error")
            return redirect(url_for("signin"))

        # Sign in via Supabase Auth to check confirmed_at
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        # Auto-sync verified status
        if auth_response.user and getattr(auth_response.user, "confirmed_at", None):
            supabase.table("users").update({"is_verified": True}).eq("email", email).execute()
            user_data["is_verified"] = True

        # Check verification in custom table
        if not user_data.get("is_verified", False):
            flash("Open your Gmail to verify your account!", "error")
            return redirect(url_for("signin"))

        # Set session
        session['user'] = {
            'id': user_data['id'],
            'email': user_data['email'],
            'first_name': user_data['first_name'],
            'role': user_data['role']
        }

        flash("Login successful!", "success")
        if user_data['role'] == 'admin':
            return redirect(url_for('admin_portal'))
        return redirect(url_for('booking'))

    except Exception as e:
        flash("Login failed. Please check your email to verify your account.", "error")
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

    # My Bookings: Pending or Approved only
    bookings_data = supabase.table("bookings") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("status", ["Pending", "Approved"]) \
        .order("event_date", desc=False) \
        .execute()
    bookings = bookings_data.data if bookings_data.data else []

    for booking in bookings:
        booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))

    # Booking History
    history_data = supabase.table("bookings") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("status", ["Completed", "Cancelled"]) \
        .order("event_date", desc=True) \
        .execute()
    booking_history = history_data.data if history_data.data else []

    for booking in booking_history:
        booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
    
    # ✅ GET UNREAD NOTIFICATIONS COUNT
    unread_notif_data = supabase.table("notifications") \
        .select("id") \
        .eq("user_id", user_id) \
        .eq("is_read", False) \
        .execute()
    unread_count = len(unread_notif_data.data) if unread_notif_data.data else 0

    # ✅ GET RECENT NOTIFICATIONS LIST (e.g., last 10)
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
        notifications=notifications  # ✅ ITO ANG IDINAGDAG
    )

@app.route("/booking_details/<booking_id>")
def booking_details(booking_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first"})
    
    try:
        # Kunin ang booking details
        booking_data = supabase.table("bookings").select("*").eq("id", booking_id).eq("user_id", session["user"]["id"]).execute()
        
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


@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first!"})
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"})
        
        # Update status to Cancelled instead of deleting
        supabase.table("bookings") \
            .update({"status": "Cancelled"}) \
            .eq("id", booking_id) \
            .eq("user_id", session["user"]["id"]) \
            .execute()
        
        # --- NEW: Create Notification for User ---
        create_notification(
            user_id=session["user"]["id"],
            message=f"Your booking (ID: {booking_id}) has been cancelled.",
            booking_id=booking_id,
            link=url_for('booking_details', booking_id=booking_id)
        )

        # Kunin ang email at name ng user
        user_data = supabase.table("users").select("email, first_name").eq("id", session["user"]["id"]).execute()
        if user_data.data:
            user_email = user_data.data[0]['email']
            user_first_name = user_data.data[0]['first_name']

        # Kunin ang event_date at ticket_number mula sa booking
        booking_data = supabase.table("bookings").select("event_date, ticket_number").eq("id", booking_id).execute()
        if booking_data.data:
            event_date = booking_data.data[0]['event_date']
            ticket_number = booking_data.data[0]['ticket_number']  # ← TAMA na ito

        # Magpadala ng tamang datos sa email
        send_email_notification(
            to_email=user_email,
            subject="⚠️ Booking Cancelled",
            message=get_email_template(
                status="cancelled",
                user_first_name=user_first_name,
                ticket_number=ticket_number,  # ← Tama na
                event_date=event_date  # ← Tama na
            )
        )
        
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
    email = request.form.get("email", "").strip()

    # Generate IDs
    booking_id = str(uuid.uuid4())
    ticket_number = "TKT-" + str(uuid.uuid4())[:8].upper()

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
        "event_date": event_date,
        "contact_number": contact_number,
        "email": email,
        "others_qty": total_others_qty,      # ← ITO ANG TOTAL QUANTITY
        "other_items": all_other_items,      # ← ITO ANG LAHAT NG ITEM DESCRIPTIONS
        "status": "Pending",
        "created_at": datetime.now().isoformat()
    }

    try:
        supabase.table("bookings").insert(booking_data).execute()
        flash(f"Booking submitted successfully! Ticket: {ticket_number}", "success")
        
        # --- NEW: Create Notification for User ---
        create_notification(
            user_id=user_id,
            message=f"Your booking request (Ticket: {ticket_number}) has been submitted and is now pending approval.",
            booking_id=booking_id,
            link=url_for('booking_details', booking_id=booking_id)
        )

        send_email_notification(
            to_email=email,
            subject="⏳ Booking Pending Approval",
            message=get_email_template(
                status="pending",
                user_first_name=user_first_name,
                ticket_number=ticket_number,
                event_date=event_date,
                event_type="Equipment Rental"  # Dahil sa booking3, wala naman event type
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
        event_date = request.form.get("event_date", "").strip()
        contact_number = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

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

        # Generate IDs
        booking_id = str(uuid.uuid4())
        ticket_number = "TKT-" + str(uuid.uuid4())[:8].upper()

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

        # Insert into Supabase
        supabase.table("bookings").insert(booking_data).execute()

        flash(f"Booking submitted successfully! Ticket: {ticket_number}", "success")

        # --- NEW: Create Notification for User ---
        create_notification(
            user_id=user_id,
            message=f"Your event booking request (Ticket: {ticket_number}) has been submitted and is now pending approval.",
            booking_id=booking_id,
            link=url_for('booking_details', booking_id=booking_id)
        )

        send_email_notification(
            to_email=email,
            subject="Event Booking Submitted - Pending Approval",
            message=get_email_template(
                status="pending",
                user_first_name=user_first_name,
                ticket_number=ticket_number,
                event_date=event_date,
                event_type=event_type
            )
        )

        admin_users = supabase.table("users").select("id").eq("role", "admin").execute()
        if admin_users.data:
            for admin in admin_users.data:
                create_notification(
                    user_id=admin['id'],
                    message=f"New event booking from {user_first_name} {user_last_name} (Ticket: {ticket_number})",
                    admin_only=True,
                    link=url_for('admin_portal') + "#pending-approvals"
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
        
        # Kunin ang mga pending approvals KASAMA ANG USER INFO
        pending_approvals_data = supabase.table("bookings").select("*, users(first_name, last_name)").eq("status", "Pending").execute()
        
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

        # Kunin ang lahat ng bookings
        all_bookings_data = supabase.table("bookings").select("*, users(first_name, last_name)").execute()
        all_bookings = []
        if all_bookings_data.data:
            for booking in all_bookings_data.data:
                booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))
                all_bookings.append(booking)

        # Kunin ang lahat ng equipment
        equipment_data = supabase.table("inventory").select("*").execute()
        equipment_items = equipment_data.data if equipment_data.data else []
        
        # I-prepare ang data
        stats = {
            "total_bookings": len(total_bookings.data) if total_bookings.data else 0,
            "total_users": len(total_users.data) if total_users.data else 0,
            "pending_approvals": len(pending_approvals),
            "total_equipment": len(equipment_items)
        }
        
        # ✅ GET ADMIN NOTIFICATIONS
        admin_notif_data = supabase.table("notifications") \
            .select("*") \
            .or_("admin_only.eq.true,user_id.eq." + session["user"]["id"]) \
            .eq("is_read", False) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        admin_notifications = admin_notif_data.data if admin_notif_data.data else []
        unread_admin_count = len(admin_notif_data.data) if admin_notif_data.data else 0

        return render_template(
            "admin_portal.html", 
            stats=stats,
            pending_approvals=pending_approvals,
            all_bookings=all_bookings,
            equipment_items=equipment_items,
            admin_notifications=admin_notifications,  # ✅ ITO ANG IDINAGDAG
            unread_admin_count=unread_admin_count   # ✅ ITO ANG IDINAGDAG
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

@app.route("/admin/approve_booking", methods=["POST"])
def admin_approve_booking():
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"})
        
        # I-update ang status ng booking
        supabase.table("bookings") \
            .update({"status": "Approved"}) \
            .eq("id", booking_id) \
            .execute()
        
        # --- NEW: Fetch user_id and notify user ---
        booking_data = supabase.table("bookings").select("user_id, ticket_number, email, first_name, event_type, event_date").eq("id", booking_id).execute()
        if booking_data.data:
            user_id = booking_data.data[0]['user_id']
            ticket_number = booking_data.data[0]['ticket_number']
            user_email = booking_data.data[0]['email']
            user_first_name = booking_data.data[0]['first_name']

            create_notification(
                user_id=user_id,
                message=f"Great news! Your booking request (Ticket: {ticket_number}) has been approved.",
                booking_id=booking_id,
                link=url_for('booking_details', booking_id=booking_id)
            )

            # --- NEW: Send Email Notification ---
            send_email_notification(
                to_email=user_email,
                subject="✅ Booking Approved!",
                message=get_email_template(
                    status="approved",
                    user_first_name=user_first_name,
                    ticket_number=ticket_number,
                    event_date=booking_data.data[0].get('event_date', 'N/A'),
                    event_type=booking_data.data[0].get('event_type', 'N/A')
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
        data = request.get_json()
        booking_id = data.get("booking_id")

        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"}), 400

        response = supabase.table("bookings") \
            .update({"status": "Rejected"}) \
            .eq("id", booking_id) \
            .execute()

        if not response.data:
            return jsonify({"success": False, "message": "Booking not found"}), 404

        # --- NEW: Fetch user_id and notify user ---
        booking_data = supabase.table("bookings").select("user_id, ticket_number, email, first_name, event_type, event_date").eq("id", booking_id).execute()
        if booking_data.data:
            user_id = booking_data.data[0]['user_id']
            ticket_number = booking_data.data[0]['ticket_number']
            user_email = booking_data.data[0]['email']
            user_first_name = booking_data.data[0]['first_name']

            create_notification(
                user_id=user_id,
                message=f"We're sorry, your booking request (Ticket: {ticket_number}) has been rejected.",
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
                    event_date=booking_data.data[0].get('event_date', 'N/A'),
                    event_type=booking_data.data[0].get('event_type', 'N/A'),
                    reason="The requested date is no longer available."  # Optional: Kunin mo sa form kung may reason field
                )
            )

        return jsonify({"success": True, "message": "Booking rejected successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# Equipment Management Routes
@app.route("/admin/equipment")
def admin_equipment_management():
    if "user" not in session or session["user"]["role"] != "admin":
        flash("Admins only!", "error")
        return redirect(url_for("admin_login"))
    
    try:
        # Kunin ang lahat ng equipment
        equipment_data = supabase.table("inventory").select("*").execute()
        equipment_items = equipment_data.data if equipment_data.data else []
        
        return render_template(
            "admin_portal.html",  # Dapat naka-set na ito sa iyong admin portal
            equipment_items=equipment_items,
            active_tab="equipment-management"  # Para ma-highlight ang tamang tab
        )
    
    except Exception as e:
        flash(f"Error loading equipment: {str(e)}", "error")
        return redirect(url_for("admin_portal"))

@app.route("/admin/equipment/<item_id>")
def get_equipment_item(item_id):
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        equipment_data = supabase.table("inventory").select("*").eq("id", item_id).execute()
        
        if not equipment_data.data:
            return jsonify({"success": False, "message": "Equipment not found"})
        
        return jsonify({"success": True, "item": equipment_data.data[0]})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/admin/equipment/add", methods=["POST"])
def add_equipment():
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ["name", "category_id", "quantity_total", "quantity_available"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"success": False, "message": f"Missing required field: {field}"})
        
        # Create equipment data
        equipment_data = {
            "id": str(uuid.uuid4()),
            "name": data["name"],
            "category_id": data["category_id"],
            "description": data.get("description", ""),
            "quantity_total": int(data["quantity_total"]),
            "quantity_available": int(data["quantity_available"]),
            "is_active": data.get("is_active", True),
            "created_at": datetime.now().isoformat()
        }
        
        # Insert into database
        supabase.table("inventory").insert(equipment_data).execute()
        
        return jsonify({"success": True, "message": "Equipment added successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/admin/equipment/update", methods=["POST"])
def update_equipment():
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        data = request.get_json()
        item_id = data.get("id")
        
        if not item_id:
            return jsonify({"success": False, "message": "No equipment ID provided"})
        
        # Prepare update data
        update_data = {
            "name": data["name"],
            "category_id": data["category_id"],
            "description": data.get("description", ""),
            "quantity_total": int(data["quantity_total"]),
            "quantity_available": int(data["quantity_available"]),
            "is_active": data.get("is_active", True)
        }
        
        # Update database
        supabase.table("inventory").update(update_data).eq("id", item_id).execute()
        
        return jsonify({"success": True, "message": "Equipment updated successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/admin/equipment/delete", methods=["POST"])
def delete_equipment():
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        data = request.get_json()
        item_id = data.get("id")
        
        if not item_id:
            return jsonify({"success": False, "message": "No equipment ID provided"})
        
        # Delete from database
        supabase.table("inventory").delete().eq("id", item_id).execute()
        
        return jsonify({"success": True, "message": "Equipment deleted successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


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
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('admin_login'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))

@app.route("/signout", methods=["POST"])
def signout():
    session.pop("user", None)
    return redirect(url_for("admin_login"))


@app.route('/mark_notifications_as_read', methods=['POST'])
def mark_notifications_as_read():
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first!"})

    try:
        user_id = session["user"]["id"]
        supabase.table("notifications") \
            .update({"is_read": True}) \
            .eq("user_id", user_id) \
            .eq("is_read", False) \
            .execute()

        return jsonify({"success": True, "message": "Notifications marked as read"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})
    

@app.route('/get_unread_count', methods=['GET'])
def get_unread_count():
    if "user" not in session:
        return jsonify({"success": False, "unread_count": 0})

    try:
        user_id = session["user"]["id"]
        unread_notif_data = supabase.table("notifications") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("is_read", False) \
            .execute()
        unread_count = len(unread_notif_data.data) if unread_notif_data.data else 0
        return jsonify({"success": True, "unread_count": unread_count})
    except Exception as e:
        return jsonify({"success": False, "unread_count": 0})





if __name__ == "__main__":

    app.run(host='127.0.0.1', port=5000, debug=True)
