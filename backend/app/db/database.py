import sqlite3
import os
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
import uuid
import hashlib
import secrets
import jwt  # Add this import for JWT handling

# Create the database directory if it doesn't exist
db_dir = Path(__file__).parent.parent.parent / "data"

# Database file path
DB_PATH = str(db_dir / "foodiespot.db")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # Token expiration in hours

# Standard format for datetime strings across the application
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

def format_datetime(dt_obj):
    """Convert datetime object to standard string format without timezone information"""
    if dt_obj is None:
        return None
        
    if isinstance(dt_obj, datetime):
        # Remove timezone info if present
        if dt_obj.tzinfo is not None:
            dt_obj = dt_obj.replace(tzinfo=None)
        return dt_obj.strftime(DATETIME_FORMAT)
        
    elif isinstance(dt_obj, str):
        # Remove timezone indicators if present
        if dt_obj.endswith('Z'):
            dt_obj = dt_obj[:-1]
        elif '+' in dt_obj:
            dt_obj = dt_obj.split('+')[0]
        elif dt_obj.count('-') > 2 and '-' in dt_obj[10:]:  # Check for timezone with negative offset
            parts = dt_obj.rsplit('-', 3)
            if len(parts) > 1:
                dt_obj = parts[0]
                
        # Try to parse and reformat to ensure consistency
        try:
            parsed_dt = datetime.fromisoformat(dt_obj)
            return parsed_dt.strftime(DATETIME_FORMAT)
        except ValueError:
            # If we can't parse it, return as is
            return dt_obj
    
    # Return string representation for anything else
    return str(dt_obj)

def parse_datetime(date_str):
    """Parse a datetime string to a datetime object"""
    if not date_str:
        return None
        
    # Clean the string first
    if isinstance(date_str, str):
        if date_str.endswith('Z'):
            date_str = date_str[:-1]
        elif '+' in date_str:
            date_str = date_str.split('+')[0]
    
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        try:
            return datetime.strptime(date_str, DATETIME_FORMAT)
        except ValueError:
            return None

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database tables"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create restaurants table with contact details
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            location TEXT NOT NULL,
            cuisine TEXT NOT NULL,
            total_capacity INTEGER NOT NULL,
            opening_time TEXT NOT NULL,
            closing_time TEXT NOT NULL,
            description TEXT,
            latitude REAL,
            longitude REAL,
            email TEXT,
            phone TEXT,
            website TEXT,
            address TEXT
        )
        ''')
        
        # Create reservations table with TEXT for datetime
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id TEXT PRIMARY KEY,
            restaurant_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            party_size INTEGER NOT NULL,
            reservation_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
        )
        ''')
        
        # Create users table with TEXT for datetime
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'customer',
            created_at TEXT NOT NULL,
            last_login TEXT
        )
        ''')
        
        # Create tokens table with TEXT for datetime
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        conn.commit()

# Initialize the database on module import
init_db()

# Restaurant functions
def get_restaurants(cuisine=None, location=None):
    """Get restaurants with optional filtering"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM restaurants"
        params = []
        
        where_clauses = []
        if cuisine:
            where_clauses.append("LOWER(cuisine) = LOWER(?)")
            params.append(cuisine)
        
        if location:
            where_clauses.append("LOWER(location) LIKE LOWER(?)")
            params.append(f"%{location}%")
            
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_restaurant(restaurant_id):
    """Get a restaurant by ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_restaurant(restaurant):
    """Add a new restaurant"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO restaurants 
            (id, name, location, city, cuisine, total_capacity, opening_time, closing_time, 
            description, latitude, longitude, email, phone, website, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                restaurant["id"],
                restaurant["name"],
                restaurant["location"],
                restaurant["city"],
                restaurant["cuisine"],
                restaurant["total_capacity"],
                restaurant["opening_time"],
                restaurant["closing_time"],
                restaurant.get("description"),
                restaurant.get("latitude"),
                restaurant.get("longitude"),
                restaurant.get("email"),
                restaurant.get("phone"),
                restaurant.get("website"),
                restaurant.get("address")
            )
        )
        conn.commit()
        return get_restaurant(restaurant["id"])

def update_restaurant(restaurant):
    """Update an existing restaurant"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE restaurants SET
            name = ?,
            location = ?,
            city = ?,
            cuisine = ?,
            total_capacity = ?,
            opening_time = ?,
            closing_time = ?,
            description = ?,
            latitude = ?,
            longitude = ?,
            email = ?,
            phone = ?,
            website = ?,
            address = ?
            WHERE id = ?
            """,
            (
                restaurant["name"],
                restaurant["location"],
                restaurant["city"],
                restaurant["cuisine"],
                restaurant["total_capacity"],
                restaurant["opening_time"],
                restaurant["closing_time"],
                restaurant.get("description"),
                restaurant.get("latitude"),
                restaurant.get("longitude"),
                restaurant.get("email"),
                restaurant.get("phone"),
                restaurant.get("website"),
                restaurant.get("address"),
                restaurant["id"]
            )
        )
        conn.commit()
        return get_restaurant(restaurant["id"])

def delete_restaurant(restaurant_id):
    """Delete a restaurant"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM restaurants WHERE id = ?", (restaurant_id,))
        conn.commit()
        return cursor.rowcount > 0

# Reservation functions
def get_reservations(restaurant_id=None, date=None, status=None, customer_phone=None):
    """Get reservations with optional filtering"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM reservations"
        params = []
        
        where_clauses = []
        if restaurant_id:
            where_clauses.append("restaurant_id = ?")
            params.append(restaurant_id)
        
        if date:
            # Format the date as string if it's a datetime object
            if isinstance(date, datetime):
                date_str = date.strftime("%Y-%m-%d")
            else:
                date_str = date
                
            # Use LIKE for matching the date part at the beginning of the string
            where_clauses.append("reservation_time LIKE ?")
            params.append(f"{date_str}%")
            
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if customer_phone:
            where_clauses.append("customer_phone = ?")
            params.append(customer_phone)
            
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_reservation(reservation_id):
    """Get a reservation by ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_reservation(reservation):
    """Add a new reservation"""
    # Ensure reservation_time is in the standard string format
    if "reservation_time" in reservation:
        reservation_time = format_datetime(reservation["reservation_time"])
    else:
        reservation_time = format_datetime(datetime.now())
    
    # Generate ID if not provided
    reservation_id = reservation.get("id", str(uuid.uuid4()))
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reservations 
            (id, restaurant_id, customer_name, customer_email, customer_phone, party_size, reservation_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reservation_id,
                reservation["restaurant_id"],
                reservation["customer_name"],
                reservation["customer_email"],
                reservation["customer_phone"],
                reservation["party_size"],
                reservation_time,  # Use the formatted string
                reservation.get("status", "confirmed")
            )
        )
        conn.commit()
        return get_reservation(reservation_id)

def update_reservation(reservation):
    """Update an existing reservation"""
    # Ensure reservation_time is in the standard string format
    if "reservation_time" in reservation:
        reservation_time = format_datetime(reservation["reservation_time"])
    else:
        # Get the current time from the existing reservation
        existing = get_reservation(reservation["id"])
        reservation_time = existing["reservation_time"] if existing else format_datetime(datetime.now())
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE reservations SET
            restaurant_id = ?,
            customer_name = ?,
            customer_email = ?,
            customer_phone = ?,
            party_size = ?,
            reservation_time = ?,
            status = ?
            WHERE id = ?
            """,
            (
                reservation["restaurant_id"],
                reservation["customer_name"],
                reservation["customer_email"],
                reservation["customer_phone"],
                reservation["party_size"],
                reservation_time,  # Use the formatted string
                reservation.get("status", "confirmed"),
                reservation["id"]
            )
        )
        conn.commit()
        return get_reservation(reservation["id"])

def delete_reservation(reservation_id):
    """Delete a reservation"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
        conn.commit()
        return cursor.rowcount > 0

def check_availability(restaurant_id, date_utc, party_size):
    """Check if a restaurant has available capacity for a given date and party size"""
    # Get restaurant details
    restaurant = get_restaurant(restaurant_id)
    if not restaurant:
        return {"available": False, "reason": "Restaurant not found"}
    
    # Standardize the date format
    date_str = format_datetime(date_utc)
    
    # Parse into datetime object for time comparison
    date_obj = None
    try:
        date_obj = parse_datetime(date_str)
        if not date_obj:
            return {"available": False, "reason": f"Invalid date format: {date_str}"}
    except Exception as e:
        return {"available": False, "reason": f"Error parsing date: {str(e)}"}
    
    # Check if restaurant is open at the requested time
    time_str = date_obj.strftime("%H:%M")
    if time_str < restaurant["opening_time"] or time_str > restaurant["closing_time"]:
        return {
            "available": False,
            "reason": f"Restaurant is closed at {time_str}. Open hours: {restaurant['opening_time']}-{restaurant['closing_time']}"
        }
    
    # Get existing reservations for the date
    date_prefix = date_obj.strftime("%Y-%m-%d")
    
    # For queries, we need to find reservations on the same day
    # So we format the date part only, and get all reservations for that day
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM reservations 
            WHERE restaurant_id = ? 
            AND status = 'confirmed'
            AND reservation_time LIKE ?
            """, 
            (restaurant_id, f"{date_prefix}%")
        )
        existing_reservations = [dict(row) for row in cursor.fetchall()]
    
    # Calculate available capacity
    reserved_seats = sum(res["party_size"] for res in existing_reservations)
    available_seats = restaurant["total_capacity"] - reserved_seats
    
    if available_seats >= party_size:
        return {
            "available": True,
            "restaurant": restaurant["name"],
            "date": date_str,
            "available_seats": available_seats
        }
    else:
        return {
            "available": False,
            "reason": f"Not enough capacity. Only {available_seats} seats available."
        }

# User functions
def hash_password(password, salt=None):
    """Hash a password with a salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password and salt, then hash
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    
    return pw_hash, salt

def get_users(role=None):
    """Get users with optional filtering by role"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT id, username, email, full_name, phone, role, created_at FROM users"
        params = []
        
        if role:
            query += " WHERE role = ?"
            params.append(role)
            
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_user(user_id):
    """Get a user by ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, full_name, phone, role, created_at FROM users WHERE id = ?", 
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_email(email):
    """Get a user by email"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_username(username):
    """Get a user by username"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_phone(phone_number):
    """Get a user by phone number"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = ?", (phone_number,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_user(user):
    """Add a new user"""
    # Check if phone number already exists (instead of email)
    if "phone" in user and get_user_by_phone(user["phone"]):
        return {"error": "Phone number already registered"}
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Generate new ID if not provided
        user_id = user.get("id") or str(uuid.uuid4())
        
        # Create the SQL query dynamically based on available fields
        fields = ["id"]
        values = [user_id]
        placeholders = ["?"]
        
        # Add available fields
        if "phone" in user:
            fields.append("phone")
            values.append(user["phone"])
            placeholders.append("?")
            
        if "name" in user:
            fields.append("full_name")
            values.append(user["name"])
            placeholders.append("?")
            
        # Optional fields with defaults
        fields.append("role")
        values.append(user.get("role", "customer"))
        placeholders.append("?")
        
        fields.append("created_at")
        values.append(format_datetime(datetime.now()))
        placeholders.append("?")
        
        # For backward compatibility - empty values for required fields in old schema
        if "username" not in user:
            fields.append("username")
            values.append(f"user_{uuid.uuid4().hex[:8]}")  # Generate a random username
            placeholders.append("?")
            
        if "email" not in user:
            fields.append("email")
            values.append("")  # Empty email
            placeholders.append("?")
            
        if "password_hash" not in user and "password_salt" not in user:
            # Generate dummy hash and salt for empty password
            dummy_hash, dummy_salt = hash_password("")
            fields.extend(["password_hash", "password_salt"])
            values.extend([dummy_hash, dummy_salt])
            placeholders.extend(["?", "?"])
            
        # Build and execute the query
        query = f"""
            INSERT INTO users 
            ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
        """
        
        cursor.execute(query, values)
        conn.commit()
        return get_user(user_id)

def update_user(user_id, user_data):
    """Update an existing user"""
    current_user = get_user(user_id)
    if not current_user:
        return None
    
    # If changing email, check if it's already used
    if "email" in user_data and user_data["email"] != current_user["email"]:
        existing = get_user_by_email(user_data["email"])
        if existing:
            return {"error": "Email already registered"}
    
    # If changing username, check if it's already used
    if "username" in user_data and user_data["username"] != current_user["username"]:
        existing = get_user_by_username(user_data["username"])
        if existing:
            return {"error": "Username already taken"}
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Handle password separately if it's being updated
        if "password" in user_data:
            password_hash, password_salt = hash_password(user_data["password"])
            cursor.execute(
                "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
                (password_hash, password_salt, user_id)
            )
            del user_data["password"]
        
        # Build dynamic update query for the rest of the fields
        if user_data:
            set_parts = []
            values = []
            
            for key, value in user_data.items():
                if key in ["username", "email", "full_name", "phone", "role"]:
                    set_parts.append(f"{key} = ?")
                    values.append(value)
            
            if set_parts:
                query = f"UPDATE users SET {', '.join(set_parts)} WHERE id = ?"
                values.append(user_id)
                cursor.execute(query, values)
        
        conn.commit()
        return get_user(user_id)

def delete_user(user_id):
    """Delete a user"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def authenticate_user(email, password):
    """Authenticate a user by email and password"""
    user = get_user_by_email(email)
    if not user:
        return None
    
    # Hash the provided password with the stored salt
    password_hash, _ = hash_password(password, user["password_salt"])
    
    # Check if the hashed password matches
    if password_hash == user["password_hash"]:
        # Update last login time
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (format_datetime(datetime.now()), user["id"])
            )
            conn.commit()
        
        # Return user without sensitive data
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "phone": user["phone"],
            "role": user["role"],
            "created_at": user["created_at"]
        }
    
    return None

def authenticate_user_by_otp(phone_number):
    """Authenticate a user by phone number after OTP verification"""
    user = get_user_by_phone(phone_number)
    if not user:
        return None
        
    # Update last login time
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (format_datetime(datetime.now()), user["id"])
        )
        conn.commit()
    
    # Return user without sensitive data
    return {
        "id": user["id"],
        "phone": user["phone"],
        "full_name": user.get("full_name"),
        "role": user["role"],
        "created_at": user["created_at"]
    }

def generate_access_token(user_data):
    """Generate a JWT access token for a user"""
    payload = {
        "sub": user_data["id"],
        "name": user_data.get("full_name", ""),
        "phone": user_data["phone"],
        "role": user_data["role"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def generate_refresh_token(user_id):
    """Generate a refresh token and store it in the database"""
    refresh_token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO refresh_tokens (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (refresh_token, user_id, format_datetime(expires_at), format_datetime(datetime.utcnow()))
        )
        conn.commit()
    
    return refresh_token

def verify_token(token):
    """Verify a JWT token and return the user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return get_user(payload["sub"])
    except jwt.PyJWTError:
        return None

def refresh_access_token(refresh_token):
    """Create a new access token using a valid refresh token"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, expires_at FROM refresh_tokens 
            WHERE token = ?
            """,
            (refresh_token,)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
            
        # Parse the expiration date
        expires_at = parse_datetime(row["expires_at"])
        if not expires_at or expires_at < datetime.utcnow():
            return None
        
        user = get_user(row["user_id"])
        if not user:
            return None
        
        return generate_access_token(user)

def revoke_refresh_token(refresh_token):
    """Revoke a refresh token"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM refresh_tokens WHERE token = ?",
            (refresh_token,)
        )
        conn.commit()
        return cursor.rowcount > 0

def revoke_all_user_tokens(user_id):
    """Revoke all refresh tokens for a user"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM refresh_tokens WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount

def login_user(email, password):
    """Login a user and generate access and refresh tokens"""
    user = authenticate_user(email, password)
    if not user:
        return None
    
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user["id"])
    
    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION * 3600  # in seconds
    }

def login_user_with_phone(phone_number):
    """Login a user with phone number after OTP verification"""
    user = authenticate_user_by_otp(phone_number)
    if not user:
        return None
    
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user["id"])
    
    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION * 3600  # in seconds
    }