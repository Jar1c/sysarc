# from flask import Flask, render_template, request, redirect, url_for, flash, session
# import sqlite3
# from werkzeug.security import generate_password_hash, check_password_hash

# app = Flask(__name__)
# app.secret_key = "supersecretkey"  # palitan mo ito

# # --- DB INIT ---
# def init_db():
#     conn = sqlite3.connect("database.db")
#     c = conn.cursor()

#     # Users table
#     c.execute("""CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         first_name TEXT NOT NULL,
#         last_name TEXT NOT NULL,
#         middle_name TEXT,
#         barangay_id TEXT UNIQUE,
#         email TEXT UNIQUE,
#         password TEXT NOT NULL,
#         address TEXT,
#         role TEXT DEFAULT 'user',
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     )""")

#     # Bookings table
#     c.execute("""CREATE TABLE IF NOT EXISTS bookings (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id INTEGER,
#         ticket_number TEXT UNIQUE,
#         event_type TEXT,
#         status TEXT DEFAULT 'Pending',
#         note TEXT,
#         FOREIGN KEY (user_id) REFERENCES users(id)
#     )""")

#     # Insert default admin if not exists
#     c.execute("SELECT * FROM users WHERE role='admin'")
#     if not c.fetchone():
#         c.execute("""INSERT INTO users (first_name,last_name,email,password,role)
#                      VALUES (?,?,?,?,?)""",
#                   ("Admin","User","admin@baritan.ph",
#                    generate_password_hash("admin123"), "admin"))
#     conn.commit()
#     conn.close()




# # --- ROUTES ---
# @app.route("/")
# def home():
#     return render_template("index.html")






# @app.route("/signup", methods=["GET","POST"])
# def signup():
#     if request.method == "POST":
#         fname = request.form["first_name"]
#         lname = request.form["last_name"]
#         mname = request.form.get("middle_name")
#         bid = request.form["barangay_id"]
#         email = request.form["email"]
#         password = request.form["password"]
#         confirm = request.form["confirm_password"]
#         address = request.form["address"]

#         if password != confirm:
#             flash("Passwords do not match!", "error")
#             return redirect(url_for("signup"))

#         conn = sqlite3.connect("database.db")
#         c = conn.cursor()
#         try:
#             c.execute("""INSERT INTO users 
#                 (first_name,last_name,middle_name,barangay_id,email,password,address)
#                 VALUES (?,?,?,?,?,?,?)""",
#                 (fname,lname,mname,bid,email,generate_password_hash(password),address))
#             conn.commit()
#             flash("Account created! Please sign in.", "success")
#             return redirect(url_for("signin"))
#         except sqlite3.IntegrityError:
#             flash("Email or Barangay ID already exists!", "error")
#             return redirect(url_for("signup"))
#         finally:
#             conn.close()

#     return render_template("signup.html")

# @app.route("/signin", methods=["GET","POST"])
# def signin():
#     if request.method == "POST":
#         email = request.form["email"]
#         password = request.form["password"]

#         conn = sqlite3.connect("database.db")
#         c = conn.cursor()
#         c.execute("SELECT * FROM users WHERE email=?", (email,))
#         user = c.fetchone()
#         conn.close()

#         if user and check_password_hash(user[6], password):
#             session["user_id"] = user[0]
#             session["role"] = user[8]
#             flash("Welcome back!", "success")

#             if user[8] == "admin":
#                 return redirect(url_for("admin_portal"))
#             else:
#                 return redirect(url_for("booking"))
                
#         else:
#             flash("Invalid email or password!", "error")
#             return redirect(url_for("signin"))
            

#     return render_template("signin.html")

# @app.route("/booking")
# def booking():
#     if "user_id" not in session:
#         flash("Please login first!", "error")
#         return redirect(url_for("signin"))
#     return render_template("booking.html")



# @app.route("/admin_login", methods=["GET", "POST"])
# def admin_login():
#     if request.method == "POST":
#         email = request.form["email"]
#         password = request.form["password"]

#         conn = sqlite3.connect("database.db")
#         c = conn.cursor()
#         c.execute("SELECT * FROM users WHERE email=? AND role='admin'", (email,))
#         admin = c.fetchone()
#         conn.close()

#         if admin and check_password_hash(admin[6], password):
#             session["user_id"] = admin[0]
#             session["role"] = "admin"
#             # flash("Welcome Admin!", "success")
#             return redirect(url_for("admin_portal"))
#         else:
#             flash("Invalid admin credentials!", "error")
#             return redirect(url_for("admin_login"))

#     return render_template("admin_login.html")

# # @app.route("/admin_login", methods=["GET", "POST"])
# # def admin_login():
# #     if request.method == "POST":
# #         email = request.form["email"]
# #         password = request.form["password"]

# #         try:
# #             conn = sqlite3.connect("database.db")
# #             c = conn.cursor()
# #             c.execute("SELECT * FROM users WHERE email=? AND role='admin'", (email,))
# #             admin = c.fetchone()
# #         except sqlite3.Error as e:
# #             flash("Database error occurred!", "error")
# #             return redirect(url_for("admin_login"))
# #         finally:
# #             conn.close()

# #         if admin and check_password_hash(admin[6], password):
# #             session["user_id"] = admin[0]
# #             session["role"] = "admin"
# #             return redirect(url_for("admin_portal"))
# #         else:
# #             flash("Invalid admin credentials!", "error")
# #             return redirect(url_for("admin_login"))

# #     return render_template("admin_login.html")

# @app.route("/admin_portal")
# def admin_portal():
#     if session.get("role") != "admin":
#         flash("Admins only!", "error")
#         return redirect(url_for("signin"))

#     conn = sqlite3.connect("database.db")
#     c = conn.cursor()
#     c.execute("SELECT * FROM bookings")
#     bookings = c.fetchall()
#     conn.close()

#     return render_template("admin_portal.html", bookings=bookings)


# @app.route("/logout", methods=["POST"])
# def logout():
#     session.clear()
#     flash("You have been logged out!", "success")
#     return redirect(url_for("signin"))

# @app.route("/signout", methods=["POST"])
# def signout():
#     session.pop("user", None)  # remove user session
#     return redirect(url_for("admin_login")) 

# # --- RUN ---
# if __name__ == "__main__":
#     init_db()
#     app.run(debug=True)























from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) 


SUPABASE_URL = "https://vehpeqlxmucsgasedcuh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZlaHBlcWx4bXVjc2dhc2VkY3VoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjYxNjIyMiwiZXhwIjoyMDcyMTkyMjIyfQ.Xp5JiKtJVPMfZR1ethvOwguVBwjbIYKapi-1STLLfd8"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



@app.route("/")
def home():
    return render_template("index.html")


import re  # ilagay sa taas ng file

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        fname = request.form['first_name']
        lname = request.form['last_name']
        mname = request.form.get('middle_name')
        bid = request.form['barangay_id']
        email = request.form['email']
        password = request.form["password"]
        confirm = request.form['confirm_password']
        address = request.form['address']

        form_data = {
            "first_name": fname,
            "last_name": lname,
            "middle_name": mname,
            "barangay_id": bid,
            "email": email,
            "address": address
        }

        # Password validation
        if len(password) < 8:
            flash("Password must be at least 8 characters long!", "error")
            return render_template("signup.html", form=form_data)
        if not re.search(r"[A-Z]", password):
            flash("Password must contain at least 1 uppercase letter!", "error")
            return render_template("signup.html", form=form_data)
        if not re.search(r"\d", password):
            flash("Password must contain at least 1 number!", "error")
            return render_template("signup.html", form=form_data)
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email address!", "error")
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
        
        existing_email = supabase.table("users").select("*").eq("email", email).execute()
        if existing_email.data:
            flash("Email already exists!", "error")
            return render_template("signup.html", form=form_data)

        existing_bid = supabase.table("users").select("*").eq("barangay_id", bid).execute()
        if existing_bid.data:
            flash("Barangay ID already exists!", "error")
            return render_template("signup.html", form=form_data)

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
                    "middle_name": mname,
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

    return render_template("signup.html", form={})


@app.route("/verify_success")
def verify_success():
    user_id = request.args.get("id")
    if user_id:
        supabase.table("users").update({"is_verified": True}).eq("id", user_id).execute()
    return render_template("verify_success.html")


# def update_custom_verification(user_id):
#     supabase.table("users").update({"is_verified": True}).eq("id", user_id).execute()
    
@app.route('/signin', methods=['GET','POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email format!", "error")
            return redirect(url_for("signin"))

        try:
            # Fetch user from custom table
            user_query = supabase.table("users").select("*").eq("email", email).execute()
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
                # Update custom table if user is verified in Supabase Auth
                supabase.table("users").update({"is_verified": True}).eq("email", email).execute()
                user_data["is_verified"] = True

            # Check verification in custom table
            if not user_data.get("is_verified", False):
                flash("Account not verified yet! Please check your email.", "error")
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
            else:
                return redirect(url_for('booking'))

        except Exception as e:
            flash(f"Login failed: {str(e)}", "error")
            return redirect(url_for("signin"))

    return render_template("signin.html")






@app.route("/booking")
def booking():
    if "user" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("signin"))
    
    # Get user data from database using the session user ID
    user_id = session["user"]["id"]
    user_data = supabase.table("users").select("*").eq("id", user_id).execute()
    
    if user_data.data:
        user = user_data.data[0]
        return render_template("booking.html", user=user)
    else:
        flash("User not found!", "error")
        return redirect(url_for("signin"))


# Route to show booking2 form
@app.route("/booking2", methods=["GET"])
def booking2_page():
    if "user" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("signin"))
    return render_template("booking2.html")



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

    if existing_booking.data and len(existing_booking.data) > 0:
        flash("You already booked! You can't book multiple.", "error")
        return redirect(url_for("booking2_page"))

    try:
        # Get form data
        event_type = request.form.get("event_type", "").strip()
        event_date = request.form.get("event_date", "").strip()
        contact_number = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        tent_qty = int(request.form.get("tent_qty", 0) or 0)
        chairs_qty = int(request.form.get("chairs_qty", 0) or 0)
        other_items = request.form.get("other_items", "").strip()

        # Generate IDs
        booking_id = str(uuid.uuid4())
        ticket_number = "TKT-" + str(uuid.uuid4())[:8].upper()

        booking_data = {
            "id": booking_id,
            "user_id": user_id,
            "ticket_number": ticket_number,
            "event_type": event_type,
            "event_date": event_date,
            "contact_number": contact_number,
            "email": email,
            "tent_qty": tent_qty,
            "chairs_qty": chairs_qty,
            "other_items": other_items,
            "status": "Pending",
            "created_at": datetime.now().isoformat()
        }

        # Insert into Supabase
        supabase.table("bookings").insert(booking_data).execute()

        # If no exception, consider success
        flash(f"Booking submitted successfully! Ticket: {ticket_number}", "success")
        return redirect(url_for("booking2_page"))

    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "error")
        return redirect(url_for("booking2_page"))









@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        try:
            # Kunin admin mula sa custom users table
            response = supabase.table("users").select("*").eq("email", email).eq("role", "admin").execute()

            if response.data:
                user = response.data[0]

                # Check if verified
                if not user["is_verified"]:
                    flash("Admin not verified yet!", "error")
                    return redirect(url_for("admin_login"))

                # Check password
                if check_password_hash(user["password"], password):
                    session["user"] = {
                        "id": user["id"],
                        "email": user["email"],
                        "first_name": user["first_name"],
                        "role": user["role"]
                    }
                    return redirect(url_for("admin_portal"))
                else:
                    flash("Invalid password!", "error")
                    return redirect(url_for("admin_login"))
            else:
                flash("Admin not found!", "error")
                return redirect(url_for("admin_login"))

        except Exception as e:
            flash(f"Login failed: {str(e)}", "error")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")


@app.route("/admin_portal")
def admin_portal():
    if "user" not in session or session["user"]["role"] != "admin":
        flash("Admins only!", "error")
        return redirect(url_for("signin"))

    try:
        bookings = supabase.table("bookings").select("*").execute().data
    except Exception as e:
        flash("Error loading bookings.", "error")
        bookings = []

    return render_template("admin_portal.html", bookings=bookings)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out!", "success")
    return redirect(url_for("home"))

@app.route("/signout", methods=["POST"])
def signout():
    session.pop("user", None)  # remove user session
    return redirect(url_for("admin_login")) 


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)

