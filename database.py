import sqlite3
import json
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from config import Config, BASE_DIR

def get_db():
    """Returns a SQLite database connection with row factory configured."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database schema using schema.sql."""
    schema_file = BASE_DIR / "schema.sql"
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    with get_db() as conn:
        conn.executescript(schema_sql)
        conn.commit()
    print("Database schema successfully initialized.")

def is_room_available(room_id, check_in_str, check_out_str, exclude_booking_id=None):
    """
    Checks if a room is available for given check-in and check-out dates.
    Dates are strings in 'YYYY-MM-DD' format.
    Overlapping condition: (check_in < existing_checkout) AND (check_out > existing_checkin)
    where status is not 'cancelled'.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # First verify room exists and is not under maintenance
    cursor.execute("SELECT status FROM rooms WHERE id = ?", (room_id,))
    room = cursor.fetchone()
    if not room or room["status"] != "available":
        conn.close()
        return False

    query = """
        SELECT COUNT(*) as conflict_count 
        FROM bookings 
        WHERE room_id = ? 
          AND status IN ('confirmed', 'checked-in')
          AND date(check_in) < date(?)
          AND date(check_out) > date(?)
    """
    params = [room_id, check_out_str, check_in_str]

    if exclude_booking_id:
        query += " AND id != ?"
        params.append(exclude_booking_id)

    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()

    return row["conflict_count"] == 0

def seed_db():
    """Seeds initial users, luxury rooms, sample reservations, and sample inquiries."""
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # 1. Check if already seeded
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] > 0:
        print("Database already contains data. Skipping seeding.")
        conn.close()
        return

    print("Seeding database with initial users and luxury rooms...")

    # 2. Seed Users
    users_data = [
        (
            "admin",
            "admin@grandstay.com",
            generate_password_hash("Admin@1234"),
            "Alexander Montgomery",
            "+1 (800) 555-0199",
            "admin",
            "active"
        ),
        (
            "john_doe",
            "john@example.com",
            generate_password_hash("Customer@1234"),
            "Johnathan Doe",
            "+1 (415) 555-8271",
            "customer",
            "active"
        ),
        (
            "emma_stone",
            "emma@example.com",
            generate_password_hash("Customer@1234"),
            "Emma Stone",
            "+1 (310) 555-9134",
            "customer",
            "active"
        )
    ]
    cursor.executemany("""
        INSERT INTO users (username, email, password_hash, full_name, phone, role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, users_data)

    # 3. Seed Luxury Rooms
    # High-quality verified Unsplash hotel architecture and interior photography
    rooms_data = [
        (
            "101",
            "Deluxe King Sanctuary",
            "Standard Deluxe",
            "An elegantly curated sanctuary offering tranquil garden views, an opulent king-size plush mattress, Italian marble bathroom with rainfall shower, and dedicated workstation.",
            249.00,
            2,
            "King Bed",
            460,
            "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80"
            ]),
            "High-Speed Wi-Fi, 55-inch OLED Smart TV, Luxury Linens, Rainfall Shower, Nespresso Machine, Mini Bar, 24/7 Room Service, Climate Control",
            "available"
        ),
        (
            "202",
            "Executive Skyline Suite",
            "Executive Suite",
            "Perched on upper levels with panoramic skyline vistas, featuring a private lounge parlor, dining nook, deep soaking bathtub, and evening turndown amenity service.",
            389.00,
            3,
            "California King Bed",
            680,
            "https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80"
            ]),
            "Panoramic Skyline View, Executive Lounge Access, Deep Soaking Tub, Walk-in Closet, Nespresso Machine, High-Speed Wi-Fi, 65-inch Smart TV, Complimentary Breakfast",
            "available"
        ),
        (
            "305",
            "Oceanfront Azure Villa",
            "Ocean Villa",
            "Exclusive waterfront villa offering floor-to-ceiling horizon views, private terrace with sun loungers, outdoor heated spa pool, and direct access to pristine sands.",
            599.00,
            4,
            "King Bed + Daybed",
            920,
            "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1540541338287-41700207dee6?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=1200&q=80"
            ]),
            "Direct Oceanfront View, Private Terrace & Sun Deck, Heated Spa Jacuzzi, Dedicated Butler Service, Fully Stocked Premium Bar, B&O Sound System, Gourmet Breakfast",
            "available"
        ),
        (
            "401",
            "The Imperial Presidential Penthouse",
            "Presidential Suite",
            "The pinnacle of bespoke grand hospitality. Spanning 1,850 sq ft, this master penthouse boasts private elevator access, grand piano, dual master suites, wine cellar, and 360-degree terrace.",
            1199.00,
            6,
            "2 California King Beds",
            1850,
            "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80"
            ]),
            "Private Elevator Access, 360-Degree Wrap Terrace, Grand Piano, Dedicated 24/7 Butler & Private Chef, Jacuzzi & Sauna, Chauffeur Airport Limousine, Wine Cellar",
            "available"
        ),
        (
            "204",
            "Royal Heritage Double Suite",
            "Family Suite",
            "A masterfully appointed multi-room suite crafted for families or small entourages. Features twin queen bedrooms, adjoining playroom/living area, and dual bathrooms.",
            449.00,
            5,
            "2 Queen Beds",
            820,
            "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=1200&q=80"
            ]),
            "Dual Master Bathrooms, Connected Living Room, Kids Welcome Pack, High-Speed Wi-Fi, 2x 55-inch OLED TVs, Stocked Pantry, Crib Available Upon Request",
            "available"
        ),
        (
            "108",
            "Garden Courtyard Deluxe",
            "Standard Deluxe",
            "Bask in natural morning sunlight surrounded by lush botanical flora. Features french doors opening to an ivy-draped courtyard terrace, plush seating, and rainfall shower.",
            279.00,
            2,
            "King Bed",
            510,
            "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80"
            ]),
            "Private Garden Patio, French Doors, Rain Shower, Artisanal Bath Amenities, High-Speed Wi-Fi, Espresso Bar, 50-inch 4K TV, In-Room Safe",
            "available"
        ),
        (
            "312",
            "Sunset Horizon Junior Suite",
            "Executive Suite",
            "West-facing elevated suite offering breathtaking sunset views. Contemporary coastal decor, plush sectional sofa, workspace desk, and complimentary evening canapés.",
            349.00,
            2,
            "King Bed",
            600,
            "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1540541338287-41700207dee6?auto=format&fit=crop&w=1200&q=80"
            ]),
            "Sunset Bay View, Balcony Lounge, Evening Cocktail Hour, High-Speed Wi-Fi, Dual Vanity Bathroom, Mini Wine Chiller, 60-inch Smart TV",
            "available"
        ),
        (
            "502",
            "Ambassador Suite & Spa",
            "Presidential Suite",
            "Designed for discerning VIP travelers, featuring a private in-room cedar sauna, soaking jacuzzi, separate boardroom conference table, and panoramic mountain-ocean views.",
            890.00,
            4,
            "2 King Beds",
            1400,
            "https://images.unsplash.com/photo-1540541338287-41700207dee6?auto=format&fit=crop&w=1200&q=80",
            json.dumps([
                "https://images.unsplash.com/photo-1540541338287-41700207dee6?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1200&q=80",
                "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80"
            ]),
            "Private In-Room Cedar Sauna, Deep Whirlpool Spa, Private Conference Area, VIP Concierge, Premium Audio System, Complimentary Valet, Marble Bar",
            "available"
        )
    ]
    cursor.executemany("""
        INSERT INTO rooms (
            room_number, name, room_type, description, price_per_night, 
            capacity, bed_type, size_sqft, image_url, gallery_urls, amenities, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rooms_data)

    # 4. Seed Sample Reservations
    today = date.today()
    checkin_1 = (today + timedelta(days=2)).isoformat()
    checkout_1 = (today + timedelta(days=5)).isoformat()
    checkin_2 = (today + timedelta(days=7)).isoformat()
    checkout_2 = (today + timedelta(days=10)).isoformat()
    past_in = (today - timedelta(days=12)).isoformat()
    past_out = (today - timedelta(days=9)).isoformat()

    bookings_data = [
        (
            "GS-2026-88102",
            2, # john_doe
            1, # Deluxe King Sanctuary (room 101)
            checkin_1,
            checkout_1,
            2,
            836.64, # 3 nights * $249 * 1.12
            "High floor requested, late check-in around 8 PM.",
            "confirmed",
            "paid",
            "Credit Card (Simulated)"
        ),
        (
            "GS-2026-94211",
            3, # emma_stone
            3, # Oceanfront Azure Villa (room 305)
            checkin_2,
            checkout_2,
            2,
            2012.64, # 3 nights * $599 * 1.12
            "Anniversary celebration, champagne on arrival please.",
            "confirmed",
            "paid",
            "Credit Card (Simulated)"
        ),
        (
            "GS-2026-72019",
            2, # john_doe
            2, # Executive Skyline Suite (room 202)
            past_in,
            past_out,
            1,
            1307.04, # 3 nights * $389 * 1.12
            "Quiet room away from elevator.",
            "checked-out",
            "paid",
            "Credit Card (Simulated)"
        )
    ]
    cursor.executemany("""
        INSERT INTO bookings (
            booking_reference, user_id, room_id, check_in, check_out, 
            guests, total_price, special_requests, status, payment_status, payment_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, bookings_data)

    # 5. Seed Sample Inquiries
    messages_data = [
        (
            "Eleanor Vance",
            "eleanor@example.com",
            "+1 (555) 234-5678",
            "Wedding Reception & Suite Reservation Inquiry",
            "Greetings GrandStay Team. We are planning a boutique wedding reception in November for 40 guests and would like to reserve a block of suites including the Presidential Penthouse.",
            "new"
        ),
        (
            "David Sterling",
            "david.sterling@acme-corp.com",
            "+1 (555) 876-5432",
            "Corporate Executive Retreat",
            "We are interested in booking all executive suites for our annual board retreat over a 4-day weekend.",
            "read"
        )
    ]
    cursor.executemany("""
        INSERT INTO contact_messages (name, email, phone, subject, message, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, messages_data)

    conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_db()
