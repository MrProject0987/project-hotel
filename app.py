import os
import json
import random
import string
from datetime import datetime, date, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from database import get_db, is_room_available, init_db

app = Flask(__name__)
app.config.from_object(Config)

# Ensure database exists
if not os.path.exists(Config.DATABASE_PATH):
    from database import seed_db
    seed_db()

# -----------------------------------------------------------------------------
# Decorators & Authentication Helpers
# -----------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access your reservations and account.", "info")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Administrator authentication required.", "danger")
            return redirect(url_for("admin_login", next=request.url))
        if session.get("role") != "admin":
            flash("Access denied: Administrator privileges required.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

def generate_booking_reference():
    """Generates a unique booking reference code: GS-YYYY-XXXXX."""
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    year = datetime.now().year
    return f"GS-{year}-{random_str}"

@app.context_processor
def inject_globals():
    """Injects hotel configuration variables into all templates."""
    return {
        "hotel_name": Config.HOTEL_NAME,
        "hotel_phone": Config.HOTEL_PHONE,
        "hotel_email": Config.HOTEL_EMAIL,
        "hotel_address": Config.HOTEL_ADDRESS,
        "currency_symbol": Config.CURRENCY_SYMBOL,
        "tax_rate": Config.TAX_RATE,
        "current_year": datetime.now().year,
        "today_date": date.today().isoformat(),
        "tomorrow_date": (date.today() + timedelta(days=1)).isoformat()
    }

# -----------------------------------------------------------------------------
# Public & Guest Routes
# -----------------------------------------------------------------------------

@app.route("/")
def index():
    """Homepage: Luxury hero section, search bar, featured rooms, amenities, testimonials."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM rooms 
        WHERE status = 'available' 
        ORDER BY price_per_night DESC 
        LIMIT 4
    """)
    featured_rooms = cursor.fetchall()
    
    # Quick hotel stats for the counter
    cursor.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = cursor.fetchone()[0]
    conn.close()

    return render_template("index.html", featured_rooms=featured_rooms, total_rooms=total_rooms)

@app.route("/rooms")
def rooms_catalog():
    """Room Catalog with search, filters (type, guest count, price), and sorting."""
    room_type = request.args.get("type", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    guests = request.args.get("guests", type=int)
    check_in = request.args.get("check_in", "").strip()
    check_out = request.args.get("check_out", "").strip()
    sort_by = request.args.get("sort", "recommended")
    search_query = request.args.get("q", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM rooms WHERE status != 'inactive'"
    params = []

    if room_type:
        query += " AND room_type = ?"
        params.append(room_type)

    if min_price is not None:
        query += " AND price_per_night >= ?"
        params.append(min_price)

    if max_price is not None:
        query += " AND price_per_night <= ?"
        params.append(max_price)

    if guests:
        query += " AND capacity >= ?"
        params.append(guests)

    if search_query:
        query += " AND (name LIKE ? OR description LIKE ? OR room_number LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])

    # Sorting
    if sort_by == "price_asc":
        query += " ORDER BY price_per_night ASC"
    elif sort_by == "price_desc":
        query += " ORDER BY price_per_night DESC"
    elif sort_by == "capacity":
        query += " ORDER BY capacity DESC"
    elif sort_by == "name":
        query += " ORDER BY name ASC"
    else:
        query += " ORDER BY price_per_night DESC"

    cursor.execute(query, params)
    all_matching_rooms = cursor.fetchall()

    # Filter out booked rooms if dates were specified
    available_rooms = []
    if check_in and check_out:
        for r in all_matching_rooms:
            if is_room_available(r["id"], check_in, check_out):
                available_rooms.append(r)
    else:
        available_rooms = all_matching_rooms

    # Distinct room types for the filter sidebar
    cursor.execute("SELECT DISTINCT room_type FROM rooms WHERE status != 'inactive'")
    distinct_types = [row["room_type"] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "rooms.html",
        rooms=available_rooms,
        types=distinct_types,
        selected_type=room_type,
        min_price=min_price,
        max_price=max_price,
        guests=guests,
        check_in=check_in,
        check_out=check_out,
        sort_by=sort_by,
        search_query=search_query,
        total_results=len(available_rooms)
    )

@app.route("/rooms/<int:room_id>")
def room_detail(room_id):
    """Room Details Page: Photo gallery, amenities, specifications, policies, booking card."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
    room = cursor.fetchone()

    if not room:
        conn.close()
        flash("Room not found.", "danger")
        return redirect(url_for("rooms_catalog"))

    # Parse gallery URLs
    gallery = []
    if room["gallery_urls"]:
        try:
            gallery = json.loads(room["gallery_urls"])
        except Exception:
            gallery = [u.strip() for u in room["gallery_urls"].split(",") if u.strip()]
    if not gallery:
        gallery = [room["image_url"]]

    # Parse amenities
    amenities_list = [a.strip() for a in room["amenities"].split(",") if a.strip()]

    # Similar rooms for recommendations
    cursor.execute("""
        SELECT * FROM rooms 
        WHERE id != ? AND room_type = ? AND status = 'available' 
        LIMIT 3
    """, (room_id, room["room_type"]))
    similar_rooms = cursor.fetchall()
    if not similar_rooms:
        cursor.execute("SELECT * FROM rooms WHERE id != ? AND status = 'available' LIMIT 3", (room_id,))
        similar_rooms = cursor.fetchall()

    conn.close()

    return render_template(
        "room_detail.html",
        room=room,
        gallery=gallery,
        amenities_list=amenities_list,
        similar_rooms=similar_rooms
    )

@app.route("/book", methods=["POST"])
@login_required
def book_room():
    """Processes room reservation, validates dates, double-booking checks, and records booking."""
    room_id = request.form.get("room_id", type=int)
    check_in_str = request.form.get("check_in", "").strip()
    check_out_str = request.form.get("check_out", "").strip()
    guests = request.form.get("guests", type=int, default=1)
    special_requests = request.form.get("special_requests", "").strip()

    # Validation
    if not room_id or not check_in_str or not check_out_str:
        flash("Please provide valid reservation dates and select a room.", "danger")
        return redirect(request.referrer or url_for("rooms_catalog"))

    try:
        check_in_date = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format provided.", "danger")
        return redirect(url_for("room_detail", room_id=room_id))

    today = date.today()
    if check_in_date < today:
        flash("Check-in date cannot be in the past.", "danger")
        return redirect(url_for("room_detail", room_id=room_id))

    if check_out_date <= check_in_date:
        flash("Check-out date must be after check-in date (minimum 1 night stay).", "danger")
        return redirect(url_for("room_detail", room_id=room_id))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
    room = cursor.fetchone()

    if not room or room["status"] != "available":
        conn.close()
        flash("This suite is currently not available for reservation.", "danger")
        return redirect(url_for("rooms_catalog"))

    if guests > room["capacity"]:
        conn.close()
        flash(f"Maximum capacity for this room is {room['capacity']} guests.", "warning")
        return redirect(url_for("room_detail", room_id=room_id))

    # Safe double-booking prevention check
    if not is_room_available(room_id, check_in_str, check_out_str):
        conn.close()
        flash("This suite has already been booked for the selected dates. Please choose alternative dates.", "danger")
        return redirect(url_for("room_detail", room_id=room_id))

    # Calculate pricing
    nights = (check_out_date - check_in_date).days
    subtotal = nights * room["price_per_night"]
    tax_amount = round(subtotal * Config.TAX_RATE, 2)
    total_price = round(subtotal + tax_amount, 2)

    ref_code = generate_booking_reference()

    cursor.execute("""
        INSERT INTO bookings (
            booking_reference, user_id, room_id, check_in, check_out,
            guests, total_price, special_requests, status, payment_status, payment_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', 'paid', 'Credit Card (Simulated)')
    """, (
        ref_code,
        session["user_id"],
        room_id,
        check_in_str,
        check_out_str,
        guests,
        total_price,
        special_requests
    ))
    conn.commit()
    conn.close()

    flash(f"Reservation confirmed! Your booking reference is {ref_code}.", "success")
    return redirect(url_for("booking_confirmation", reference=ref_code))

@app.route("/booking/<reference>")
@login_required
def booking_confirmation(reference):
    """Booking Confirmation receipt page with booking reference, dates, and breakdown."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, r.name as room_name, r.room_number, r.room_type, r.image_url, r.price_per_night,
               u.full_name, u.email, u.phone
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        WHERE b.booking_reference = ?
    """, (reference,))
    booking = cursor.fetchone()
    conn.close()

    if not booking:
        flash("Booking reference not found.", "danger")
        return redirect(url_for("user_dashboard"))

    # Security check: only owner or admin can view
    if booking["user_id"] != session.get("user_id") and session.get("role") != "admin":
        flash("You are not authorized to view this booking.", "danger")
        return redirect(url_for("index"))

    # Calculate nights breakdown
    check_in_d = datetime.strptime(booking["check_in"], "%Y-%m-%d").date()
    check_out_d = datetime.strptime(booking["check_out"], "%Y-%m-%d").date()
    nights = (check_out_d - check_in_d).days
    room_subtotal = nights * booking["price_per_night"]
    taxes = round(room_subtotal * Config.TAX_RATE, 2)

    return render_template(
        "booking_confirm.html",
        booking=booking,
        nights=nights,
        room_subtotal=room_subtotal,
        taxes=taxes
    )

@app.route("/dashboard")
@login_required
def user_dashboard():
    """User Portal: view upcoming reservations, past stay history, and cancel active bookings."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, r.name as room_name, r.room_number, r.room_type, r.image_url, r.price_per_night
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.user_id = ?
        ORDER BY b.check_in DESC
    """, (session["user_id"],))
    all_bookings = cursor.fetchall()
    
    # User details
    cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    user_info = cursor.fetchone()
    conn.close()

    # Split into active and past
    today_str = date.today().isoformat()
    upcoming_bookings = [b for b in all_bookings if b["check_in"] >= today_str and b["status"] != "cancelled"]
    past_bookings = [b for b in all_bookings if b["check_in"] < today_str or b["status"] == "cancelled"]

    return render_template(
        "dashboard/user_dashboard.html",
        upcoming_bookings=upcoming_bookings,
        past_bookings=past_bookings,
        total_bookings=len(all_bookings),
        user_info=user_info
    )

@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    """Cancels a customer booking if within allowable window."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        flash("Reservation record not found.", "danger")
        return redirect(url_for("user_dashboard"))

    # Permission check
    if booking["user_id"] != session.get("user_id") and session.get("role") != "admin":
        conn.close()
        flash("Unauthorized action.", "danger")
        return redirect(url_for("user_dashboard"))

    if booking["status"] == "cancelled":
        conn.close()
        flash("This reservation is already cancelled.", "info")
        return redirect(url_for("user_dashboard"))

    # Mark as cancelled and refunded
    cursor.execute("""
        UPDATE bookings 
        SET status = 'cancelled', payment_status = 'refunded', updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (booking_id,))
    conn.commit()
    conn.close()

    flash(f"Reservation {booking['booking_reference']} has been cancelled successfully. Full refund has been initiated.", "success")
    return redirect(url_for("user_dashboard"))

@app.route("/about")
def about():
    """About page: GrandStay heritage, luxury philosophy, team, and culinary awards."""
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page: Inquiries form submission, directions, and concierge details."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not subject or not message:
            flash("Please complete all required fields.", "danger")
            return redirect(url_for("contact"))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contact_messages (name, email, phone, subject, message, status)
            VALUES (?, ?, ?, ?, ?, 'new')
        """, (name, email, phone, subject, message))
        conn.commit()
        conn.close()

        flash("Thank you for contacting GrandStay Concierge. Our team will respond within 24 hours.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

# -----------------------------------------------------------------------------
# REST API Endpoints (For Asynchronous UI Operations)
# -----------------------------------------------------------------------------

@app.route("/api/check-availability", methods=["GET"])
def api_check_availability():
    """REST API: Checks if a specific room is available for dates."""
    room_id = request.args.get("room_id", type=int)
    check_in = request.args.get("check_in", "").strip()
    check_out = request.args.get("check_out", "").strip()

    if not room_id or not check_in or not check_out:
        return jsonify({"success": False, "error": "Missing parameters"}), 400

    try:
        check_in_d = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out_d = datetime.strptime(check_out, "%Y-%m-%d").date()
        if check_in_d < date.today() or check_out_d <= check_in_d:
            return jsonify({"success": False, "available": False, "message": "Invalid dates"}), 200
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format"}), 400

    available = is_room_available(room_id, check_in, check_out)
    return jsonify({
        "success": True,
        "available": available,
        "room_id": room_id,
        "check_in": check_in,
        "check_out": check_out
    })

@app.route("/api/calculate-price", methods=["POST"])
def api_calculate_price():
    """REST API: Calculates stay nights, subtotal, tax and total."""
    data = request.get_json() or {}
    price_per_night = data.get("price_per_night", 0.0)
    check_in = data.get("check_in", "")
    check_out = data.get("check_out", "")

    try:
        check_in_d = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out_d = datetime.strptime(check_out, "%Y-%m-%d").date()
        nights = (check_out_d - check_in_d).days
        if nights <= 0:
            return jsonify({"success": False, "error": "Check-out must be after check-in."}), 400

        subtotal = round(nights * price_per_night, 2)
        taxes = round(subtotal * Config.TAX_RATE, 2)
        total = round(subtotal + taxes, 2)

        return jsonify({
            "success": True,
            "nights": nights,
            "subtotal": subtotal,
            "taxes": taxes,
            "total": total
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# -----------------------------------------------------------------------------
# Authentication Routes
# -----------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    """Customer & Staff Login."""
    if session.get("user_id"):
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        identifier = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "").strip()
        next_url = request.args.get("next") or request.form.get("next")

        if not identifier or not password:
            flash("Please provide your username/email and password.", "danger")
            return render_template("auth/login.html")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM users 
            WHERE (username = ? OR email = ?) AND status = 'active'
        """, (identifier, identifier))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["email"] = user["email"]
            session["role"] = user["role"]
            session.permanent = True

            flash(f"Welcome back, {user['full_name']}!", "success")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("user_dashboard"))
        else:
            flash("Invalid credentials or account suspended. Please try again.", "danger")

    return render_template("auth/login.html")

@app.route("/admin-login")
def admin_login():
    """Dedicated Administrator portal login route."""
    if session.get("user_id") and session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    return render_template("auth/login.html", is_admin_page=True)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Customer Registration."""
    if session.get("user_id"):
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validations
        if not full_name or not username or not email or not password:
            flash("All required fields must be completed.", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        conn = get_db()
        cursor = conn.cursor()

        # Check existing username or email
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            flash("Username is already taken. Please select a different one.", "warning")
            return render_template("auth/register.html")

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            flash("An account with this email address already exists.", "warning")
            return render_template("auth/register.html")

        # Insert new customer
        hashed_pwd = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, phone, role, status)
            VALUES (?, ?, ?, ?, ?, 'customer', 'active')
        """, (username, email, hashed_pwd, full_name, phone))
        conn.commit()

        # Fetch new user id and auto-login
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        new_user = cursor.fetchone()
        conn.close()

        session.clear()
        session["user_id"] = new_user["id"]
        session["username"] = new_user["username"]
        session["full_name"] = new_user["full_name"]
        session["email"] = new_user["email"]
        session["role"] = new_user["role"]

        flash("Account successfully created! Welcome to GrandStay Hotel & Residences.", "success")
        return redirect(url_for("user_dashboard"))

    return render_template("auth/register.html")

@app.route("/logout")
def logout():
    """Logs out user and destroys session."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("index"))

# -----------------------------------------------------------------------------
# Admin Management Panel Routes
# -----------------------------------------------------------------------------

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin Dashboard: Metrics, occupancy, revenue, and recent reservations."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Total Rooms
    cursor.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = cursor.fetchone()[0]

    # 2. Total Bookings & Active Bookings
    cursor.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('confirmed', 'checked-in')")
    active_bookings = cursor.fetchone()[0]

    # 3. Total Revenue
    cursor.execute("SELECT COALESCE(SUM(total_price), 0) FROM bookings WHERE status != 'cancelled'")
    total_revenue = cursor.fetchone()[0]

    # 4. Total Customers
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
    total_customers = cursor.fetchone()[0]

    # 5. Occupancy Rate
    today_str = date.today().isoformat()
    cursor.execute("""
        SELECT COUNT(DISTINCT room_id) FROM bookings 
        WHERE status IN ('confirmed', 'checked-in') 
          AND check_in <= ? AND check_out > ?
    """, (today_str, today_str))
    occupied_rooms = cursor.fetchone()[0]
    occupancy_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0

    # 6. Recent Bookings Table
    cursor.execute("""
        SELECT b.*, r.name as room_name, r.room_number, u.full_name, u.email
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        ORDER BY b.created_at DESC
        LIMIT 6
    """)
    recent_bookings = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_rooms=total_rooms,
        total_bookings=total_bookings,
        active_bookings=active_bookings,
        total_revenue=total_revenue,
        total_customers=total_customers,
        occupancy_rate=occupancy_rate,
        recent_bookings=recent_bookings
    )

@app.route("/admin/rooms")
@admin_required
def admin_rooms():
    """Admin Room Inventory: list rooms, search, modal triggers for add/edit."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms ORDER BY room_number ASC")
    rooms = cursor.fetchall()
    conn.close()
    return render_template("admin/rooms_manage.html", rooms=rooms)

@app.route("/admin/rooms/create", methods=["POST"])
@admin_required
def admin_room_create():
    """Creates a new room in the system."""
    room_number = request.form.get("room_number", "").strip()
    name = request.form.get("name", "").strip()
    room_type = request.form.get("room_type", "").strip()
    description = request.form.get("description", "").strip()
    price_per_night = request.form.get("price_per_night", type=float)
    capacity = request.form.get("capacity", type=int, default=2)
    bed_type = request.form.get("bed_type", "King Bed").strip()
    size_sqft = request.form.get("size_sqft", type=int, default=450)
    image_url = request.form.get("image_url", "").strip()
    amenities = request.form.get("amenities", "").strip()
    status = request.form.get("status", "available").strip()

    if not room_number or not name or not price_per_night or not image_url:
        flash("Room number, name, price, and primary image are required.", "danger")
        return redirect(url_for("admin_rooms"))

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO rooms (
                room_number, name, room_type, description, price_per_night,
                capacity, bed_type, size_sqft, image_url, gallery_urls, amenities, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            room_number, name, room_type, description, price_per_night,
            capacity, bed_type, size_sqft, image_url, json.dumps([image_url]), amenities, status
        ))
        conn.commit()
        flash(f"Room {room_number} ({name}) created successfully.", "success")
    except Exception as e:
        flash(f"Failed to create room: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_rooms"))

@app.route("/admin/rooms/<int:room_id>/edit", methods=["POST"])
@admin_required
def admin_room_edit(room_id):
    """Updates existing room information."""
    name = request.form.get("name", "").strip()
    room_type = request.form.get("room_type", "").strip()
    description = request.form.get("description", "").strip()
    price_per_night = request.form.get("price_per_night", type=float)
    capacity = request.form.get("capacity", type=int)
    bed_type = request.form.get("bed_type", "").strip()
    size_sqft = request.form.get("size_sqft", type=int)
    image_url = request.form.get("image_url", "").strip()
    amenities = request.form.get("amenities", "").strip()
    status = request.form.get("status", "available").strip()

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE rooms 
            SET name = ?, room_type = ?, description = ?, price_per_night = ?,
                capacity = ?, bed_type = ?, size_sqft = ?, image_url = ?,
                amenities = ?, status = ?
            WHERE id = ?
        """, (
            name, room_type, description, price_per_night,
            capacity, bed_type, size_sqft, image_url,
            amenities, status, room_id
        ))
        conn.commit()
        flash(f"Room updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update room: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_rooms"))

@app.route("/admin/rooms/<int:room_id>/delete", methods=["POST"])
@admin_required
def admin_room_delete(room_id):
    """Deletes room if no active bookings exist."""
    conn = get_db()
    cursor = conn.cursor()
    # Check if there are active bookings
    cursor.execute("""
        SELECT COUNT(*) FROM bookings 
        WHERE room_id = ? AND status IN ('confirmed', 'checked-in')
    """, (room_id,))
    active_count = cursor.fetchone()[0]

    if active_count > 0:
        conn.close()
        flash("Cannot delete room: active or upcoming reservations exist for this suite.", "danger")
        return redirect(url_for("admin_rooms"))

    try:
        cursor.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        conn.commit()
        flash("Room deleted from inventory.", "success")
    except Exception as e:
        flash(f"Error deleting room: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_rooms"))

@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    """Admin Booking Management: view all bookings, filter by status, change reservation status."""
    status_filter = request.args.get("status", "").strip()
    search_query = request.args.get("q", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT b.*, r.name as room_name, r.room_number, r.price_per_night,
               u.full_name, u.email, u.phone
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND b.status = ?"
        params.append(status_filter)

    if search_query:
        query += " AND (b.booking_reference LIKE ? OR u.full_name LIKE ? OR u.email LIKE ? OR r.room_number LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term, term])

    query += " ORDER BY b.check_in DESC"

    cursor.execute(query, params)
    bookings = cursor.fetchall()
    conn.close()

    return render_template(
        "admin/bookings_manage.html",
        bookings=bookings,
        status_filter=status_filter,
        search_query=search_query
    )

@app.route("/admin/bookings/<int:booking_id>/update-status", methods=["POST"])
@admin_required
def admin_booking_update_status(booking_id):
    """Updates booking status (confirmed, checked-in, checked-out, cancelled)."""
    new_status = request.form.get("status", "").strip()
    if new_status not in ["confirmed", "checked-in", "checked-out", "cancelled"]:
        flash("Invalid booking status provided.", "danger")
        return redirect(url_for("admin_bookings"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bookings 
        SET status = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (new_status, booking_id))
    conn.commit()
    conn.close()

    flash(f"Booking status updated to {new_status.capitalize()}.", "success")
    return redirect(request.referrer or url_for("admin_bookings"))

@app.route("/admin/users")
@admin_required
def admin_users():
    """Admin Customer Directory: list registered users, view booking count, status."""
    search_query = request.args.get("q", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT u.*, COUNT(b.id) as booking_count,
               COALESCE(SUM(CASE WHEN b.status != 'cancelled' THEN b.total_price ELSE 0 END), 0) as total_spent
        FROM users u
        LEFT JOIN bookings b ON u.id = b.user_id
        WHERE 1=1
    """
    params = []

    if search_query:
        query += " AND (u.full_name LIKE ? OR u.email LIKE ? OR u.username LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])

    query += " GROUP BY u.id ORDER BY u.created_at DESC"

    cursor.execute(query, params)
    users = cursor.fetchall()
    conn.close()

    return render_template("admin/users_manage.html", users=users, search_query=search_query)

@app.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
@admin_required
def admin_user_toggle_status(user_id):
    """Toggles user status between active and suspended."""
    if user_id == session.get("user_id"):
        flash("You cannot suspend your own administrative account.", "danger")
        return redirect(url_for("admin_users"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        new_status = "suspended" if user["status"] == "active" else "active"
        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        flash(f"User account status changed to {new_status}.", "success")
    conn.close()

    return redirect(url_for("admin_users"))

# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template("base.html", content_override=True), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
