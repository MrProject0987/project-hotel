# GrandStay Hotel & Residences - Hotel Management System
**Bachelor of Computer Applications (BCA) - Semester 5 Academic Project**

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1-black.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite3-green.svg)
![Frontend](https://img.shields.io/badge/Frontend-HTML5%20%7C%20CSS3%20%7C%20Vanilla%20JS-gold.svg)
![Status](https://img.shields.io/badge/Tests-11%20Passed-brightgreen.svg)

---

## 1. Project Overview

**GrandStay** is a luxury hotel management and online reservation web application developed for the BCA Semester 5 final academic project. It offers an opulent, intuitive guest-facing booking portal paired with an administrative operations center.

The application adheres to clean architecture, MVC principles, parameterized database operations, server-side data validation, and an enterprise double-booking prevention engine.

---

## 2. Key Features

### 🛎️ Guest & Public Experience
- **Luxury Aesthetic & Responsive Design**: Elegant Midnight Navy (`#0a1128`) and Royal Gold (`#c59b27`) palette with modern typography (`Cinzel`, `Playfair Display`, `Plus Jakarta Sans`). Fully responsive across mobile (320px–430px), tablet (768px), and desktop (1024px+).
- **Interactive Quick Search**: Date pickers, guest counters, and suite category selectors embedded in the homepage hero.
- **Dynamic Suite Catalog**: Live multi-attribute filtering (suite tier, price range, guest capacity, date availability) with sorting (Price: Low to High / High to Low, Guest Capacity, Suite Name).
- **Detailed Suite Showcase**: High-resolution photo galleries with interactive thumbnail switching, architectural dimensions, bed setups, full amenities checklist, and property policies.
- **Real-Time Booking Engine**:
  - Live client-side calculation of stay duration, room subtotal, 12% luxury hotel occupancy tax, and grand total.
  - Asynchronous background check against `/api/check-availability` to confirm dates before submission.
- **Printable Booking Receipt**: Unique reference codes (e.g., `GS-2026-XXXXX`), breakdown of taxes and charges, and printer-ready CSS stylesheet.
- **Guest Dashboard**: Centralized dashboard to track upcoming stays, review past reservation history, and cancel reservations with instant refund tracking.
- **Inquiry & Concierge Desk**: Interactive inquiry form saving messages to the database, paired with an accessible FAQ accordion.

### 🛡️ Administrator Operations Center
- **Executive Dashboard**: Real-time business intelligence metrics:
  - Total Revenue generated.
  - Active & Confirmed bookings count.
  - Current Property Occupancy Rate (`%`).
  - Total Suite Inventory and registered customer count.
  - Recent reservations quick-review table.
- **Room Inventory Management (Full CRUD)**:
  - **Create**: Add new suites with room numbers, pricing, capacities, square footage, bed types, image URLs, and amenities.
  - **Read**: Browse all rooms with real-time keyword filtering.
  - **Update**: Edit room pricing, descriptions, images, and inventory status (`available`, `maintenance`, `inactive`).
  - **Delete**: Remove rooms with database integrity validation (prevents deleting suites with active or upcoming reservations).
- **Reservation Management**:
  - Filter master booking registry by status (`Confirmed`, `Checked-in`, `Checked-out`, `Cancelled`).
  - Search by guest name, reference code, email, or room number.
  - Real-time inline status transition dropdowns.
- **Customer Directory**:
  - Directory of registered guest profiles, total stay counts, and lifetime revenue generated.
  - One-click account suspension and reactivation toggling.

---

## 3. Technology Stack & Rationale

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3.12, Flask 3.1 | Clean, lightweight micro-framework optimal for academic project inspection and rapid REST API construction. |
| **Templating** | Jinja2 | Clean server-side HTML rendering, template inheritance (`base.html`), and contextual filters. |
| **Database** | SQLite 3 | Zero-configuration, file-based relational database engine with ACID compliance and foreign key enforcement. |
| **Frontend Structure** | HTML5 | Semantic tags (`<header>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<footer>`, `<dialog>`) for accessibility. |
| **Styling** | CSS3 (Custom Properties, Flexbox, Grid) | Zero heavy third-party UI dependencies; custom responsive design tailored to luxury hospitality. |
| **Interactivity** | Vanilla JavaScript (ES6+) | Native asynchronous `fetch` calls, real-time date/price math, modal handlers, and toast notifications. |
| **Security** | Werkzeug Security | Secure cryptographic password hashing (PBKDF2/scrypt), parameterized SQL queries preventing SQL Injection. |

---

## 4. Database Schema & Architecture

The system utilizes an SQLite database (`grandstay.db`) with relational integrity (`PRAGMA foreign_keys = ON;`) and indexed lookups.

```
       +-----------------------+              +-----------------------+
       |         USERS         |              |         ROOMS         |
       +-----------------------+              +-----------------------+
       | id (PK, AutoInc)      |              | id (PK, AutoInc)      |
       | username (UNIQUE)     |              | room_number (UNIQUE)  |
       | email (UNIQUE)        |              | name                  |
       | password_hash         |              | room_type             |
       | full_name             |              | description           |
       | phone                 |              | price_per_night       |
       | role [customer/admin] |              | capacity              |
       | status                |              | bed_type              |
       | created_at            |              | size_sqft             |
       +-----------------------+              | image_url             |
                   |                          | gallery_urls          |
                   | 1                        | amenities             |
                   |                          | status                |
                   |                          +-----------------------+
                   |                                      |
                   | M                                  1 |
       +--------------------------------------------------+
       |                   | M
       |       +-----------------------+
       |       |       BOOKINGS        |
       |       +-----------------------+
       +-----> | id (PK, AutoInc)      |
               | booking_reference     |
               | user_id (FK -> users) |
               | room_id (FK -> rooms) |
               | check_in (DATE)       |
               | check_out (DATE)      |
               | guests                |
               | total_price           |
               | special_requests      |
               | status                |
               | payment_status        |
               | payment_method        |
               | created_at            |
               +-----------------------+
```

### 🔒 Double-Booking Prevention Algorithm
To prevent duplicate reservations for the same room over conflicting date ranges, the server executes a strict collision check before every database insert:

```sql
SELECT COUNT(*) FROM bookings 
WHERE room_id = ? 
  AND status IN ('confirmed', 'checked-in')
  AND date(check_in) < date(:requested_check_out)
  AND date(check_out) > date(:requested_check_in);
```

Two intervals \([A, B)\) and \([C, D)\) overlap if and only if:
$$\text{Overlap} \iff A < D \quad \text{AND} \quad B > C$$
If the collision count is $> 0$, the server blocks the booking and notifies the user with a descriptive error.

---

## 5. Project Directory Structure

```
grandstay-hotel/
├── app.py                     # Main Flask application & REST API endpoints
├── config.py                  # Application settings & environment variables
├── database.py                # Database connection helpers, availability logic, seed loader
├── schema.sql                 # SQL schema definitions, constraints & indexes
├── requirements.txt           # Python dependencies
├── .env                       # Local environment variables
├── .env.example               # Template environment configuration
├── .gitignore                 # VCS ignore patterns
├── README.md                  # Comprehensive project documentation
├── static/
│   ├── css/
│   │   ├── style.css          # Core luxury theme, responsive layout & typography
│   │   ├── components.css     # Buttons, modals, badges, cards, data tables, toasts
│   │   └── admin.css          # Admin portal sidebar, metrics grid & data toolbars
│   ├── js/
│   │   ├── main.js            # Mobile navbar, modal controls, toast dismissals, demo filler
│   │   ├── booking.js         # Real-time nights math, tax breakdown & availability API
│   │   └── admin.js           # Admin table interactions & navigation highlights
│   └── images/
├── templates/
│   ├── base.html              # Master layout with header, nav, flash alerts & footer
│   ├── index.html             # Homepage: Hero, quick search, featured rooms, amenities
│   ├── rooms.html             # Rooms catalog with filter sidebar, live sorting & cards
│   ├── room_detail.html       # Room details with gallery, specs, amenities & booking card
│   ├── booking_confirm.html    # Printable booking receipt with reference code
│   ├── about.html             # Hotel heritage story, pillars & awards
│   ├── contact.html           # Inquiries form, location info & FAQ accordion
│   ├── auth/
│   │   ├── login.html         # Sign-in page with quick demo credentials autofill
│   │   └── register.html      # Guest onboarding with validation
│   ├── dashboard/
│   │   └── user_dashboard.html# Guest portal for tracking and cancelling reservations
│   └── admin/
│       ├── admin_base.html    # Dedicated admin layout with management sidebar
│       ├── dashboard.html     # Real-time metrics (Revenue, Occupancy, Bookings)
│       ├── rooms_manage.html  # Room inventory table, Add Room modal, Edit modal, Delete
│       ├── bookings_manage.html# Master booking registry with status transitions
│       └── users_manage.html  # Guest directory with booking stats & suspension toggle
└── tests/
    └── test_app.py            # Automated test suite (11 test cases)
```

---

## 6. Getting Started & Installation

### Step 1: Clone or Navigate to the Project
```bash
cd "C:\Users\jay gurudev\.gemini\antigravity\scratch\grandstay-hotel"
```

### Step 2: Install Dependencies
Ensure Python 3.10+ is installed.
```bash
pip install -r requirements.txt
```

### Step 3: Initialize & Seed the Database
Initialize the SQLite database with 8 luxury rooms and demo accounts:
```bash
python database.py
```

### Step 4: Run the Application
Start the Flask development server:
```bash
python app.py
```
Open your web browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 7. Demo Accounts & Credentials

For academic project testing and viva evaluation, pre-configured accounts are provided:

| Role | Email / Username | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@grandstay.com` or `admin` | `Admin@1234` | Full access to `/admin`, metrics, room CRUD, reservation management, customer directory. |
| **Customer 1** | `john@example.com` or `john_doe` | `Customer@1234` | Standard booking, dashboard access, receipt viewing, reservation cancellation. |
| **Customer 2** | `emma@example.com` or `emma_stone` | `Customer@1234` | Standard booking, dashboard access. |

> **Examiner Convenience Feature**: On the `/login` page, click either **"Demo Admin"** or **"Demo Guest"** buttons to automatically fill credentials into the form.

---

## 8. Automated Testing

The project includes an automated test suite (`tests/test_app.py`) verifying:
1. Database schema initialization & seeding integrity.
2. Homepage and public route accessibility.
3. Suite catalog filtering (by category, price, guest count) and sorting.
4. Room detail specifications and amenities checklist.
5. Inquiries form submission to SQLite.
6. Asynchronous availability API (`/api/check-availability`).
7. Real-time pricing & tax calculation API (`/api/calculate-price`).
8. **Double-booking prevention algorithm** (verifying overlapping vs. non-overlapping ranges).
9. User registration, password hashing, and session management.
10. End-to-end booking creation, reference generation, and cancellation refund tracking.
11. Administrative permissions protection and complete room CRUD operations.

To run the test suite:
```bash
python -m unittest tests/test_app.py
```

---

## 9. BCA Project Viva / Academic Defense Guide

### Q1: Why did you choose Flask over Django for this project?
> **Answer**: Flask is a lightweight micro-framework that provides explicit control over URL routing, database connectivity, and session management without hidden layers of magic. For an academic project, Flask allows us to write transparent SQL queries, understand the exact request lifecycle, and keep the application fast and easy to audit.

### Q2: How does the application prevent double booking?
> **Answer**: Double booking is prevented on the server side using the mathematical interval overlap formula:
> A booking overlaps if `requested_check_in < existing_check_out` AND `requested_check_out > existing_check_in` for active bookings (`confirmed` or `checked-in`).
> Furthermore, database indexes on `(room_id, check_in, check_out, status)` ensure quick availability checks even as the dataset grows.

### Q3: How are passwords stored securely?
> **Answer**: Plaintext passwords are never stored. The application uses `werkzeug.security.generate_password_hash` to compute salted cryptographic hashes (PBKDF2 with SHA-256 / scrypt). During login, `check_password_hash` compares the provided credentials in constant time to prevent timing attacks.

### Q4: How is SQL Injection prevented?
> **Answer**: All database queries throughout `app.py` and `database.py` use parameterized placeholders (`?`). Values are passed as distinct parameter tuples to the SQLite driver rather than concatenated into SQL strings, completely eliminating the risk of SQL injection.

### Q5: What is the purpose of the REST API endpoints in a server-rendered application?
> **Answer**: While Jinja2 renders complete pages, the REST API endpoints (`/api/check-availability` and `/api/calculate-price`) allow the browser to asynchronously query the server using `fetch()` without reloading the page. This delivers immediate UI feedback (e.g. informing the guest whether a room is free and computing taxes dynamically as dates change).
#   p r o j e c t - h o t e l  
 #   p r o j e c t - h o t e l  
 