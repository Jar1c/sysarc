from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import os
import re  # Moved to top

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
                    # Skip if can't parse quantity
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

    # Parse other_items for each booking
    for booking in bookings:
        booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))

    # Booking History: Completed, Cancelled
    history_data = supabase.table("bookings") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("status", ["Completed", "Cancelled"]) \
        .order("event_date", desc=True) \
        .execute()
    booking_history = history_data.data if history_data.data else []

    # Also parse for booking history
    for booking in booking_history:
        booking["parsed_items"] = parse_other_items(booking.get("other_items", ""))

    return render_template(
        "booking.html", 
        user=user, 
        bookings=bookings, 
        booking_history=booking_history
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
        
        return render_template(
            "admin_portal.html", 
            stats=stats,
            pending_approvals=pending_approvals,
            all_bookings=all_bookings,
            equipment_items=equipment_items
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
        
        return jsonify({"success": True, "message": "Booking approved successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/admin/reject_booking", methods=["POST"])
def admin_reject_booking():
    if "user" not in session or session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"})
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({"success": False, "message": "No booking ID provided"})
        
        # I-update ang status ng booking
        supabase.table("bookings") \
            .update({"status": "Rejected"}) \
            .eq("id", booking_id) \
            .execute()
        
        return jsonify({"success": True, "message": "Booking rejected successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

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

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)