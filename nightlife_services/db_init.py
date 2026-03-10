"""
Nightlife Database Initialization
================================
Creates all tables in zoma_nightlife PostgreSQL database
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from nightlife_services.config import DATABASE_CONFIG

def create_database():
    """Create zoma_nightlife database if not exists"""
    conn = psycopg2.connect(
        host=DATABASE_CONFIG['host'],
        port=DATABASE_CONFIG['port'],
        user=DATABASE_CONFIG['user'],
        password=DATABASE_CONFIG['password'],
        dbname='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # Check if database exists
    cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DATABASE_CONFIG['database']}'")
    exists = cur.fetchone()
    
    if not exists:
        cur.execute(f"CREATE DATABASE {DATABASE_CONFIG['database']}")
        print(f"✅ Database '{DATABASE_CONFIG['database']}' created")
    else:
        print(f"ℹ️ Database '{DATABASE_CONFIG['database']}' already exists")
    
    cur.close()
    conn.close()

def create_tables():
    """Create all nightlife tables"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    
    # ==================== VENDORS ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            description TEXT,
            phone VARCHAR(20),
            password_hash VARCHAR(255),
            upi_id VARCHAR(50),
            banner VARCHAR(500),
            rating DECIMAL(3,2) DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            is_freeze BOOLEAN DEFAULT FALSE,
            commission_percent DECIMAL(5,2) DEFAULT 5.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== TABLE TYPES ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_table_types (
            id SERIAL PRIMARY KEY,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            seats INTEGER DEFAULT 2,
            total_tables INTEGER DEFAULT 1,
            price DECIMAL(10,2) DEFAULT 0,
            cancel_hours INTEGER DEFAULT 2,
            time_start VARCHAR(10) DEFAULT '18:00',
            time_end VARCHAR(10) DEFAULT '02:00',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== TABLES ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_tables (
            id SERIAL PRIMARY KEY,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
            type_id INTEGER REFERENCES nightlife_table_types(id) ON DELETE CASCADE,
            table_number INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(vendor_id, type_id, table_number)
        )
    """)
    
    # ==================== SLOTS ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_slots (
            id SERIAL PRIMARY KEY,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            start_time VARCHAR(10) NOT NULL,
            end_time VARCHAR(10) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== BOOKINGS ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_bookings (
            id SERIAL PRIMARY KEY,
            booking_id VARCHAR(50) UNIQUE NOT NULL,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
            user_name VARCHAR(255) NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            user_phone VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            slot_id INTEGER REFERENCES nightlife_slots(id),
            table_type_id INTEGER REFERENCES nightlife_table_types(id),
            tables_reserved INTEGER[] DEFAULT '{}',
            price DECIMAL(10,2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pending_otp',
            otp_code VARCHAR(6),
            otp_verified BOOLEAN DEFAULT FALSE,
            otp_created_at TIMESTAMP,
            otp_expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== BOOKING HISTORY ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_booking_history (
            id SERIAL PRIMARY KEY,
            booking_id VARCHAR(50) REFERENCES nightlife_bookings(booking_id) ON DELETE CASCADE,
            action VARCHAR(50) NOT NULL,
            old_status VARCHAR(20),
            new_status VARCHAR(20),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== CLOSED DATES ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_closed_dates (
            id SERIAL PRIMARY KEY,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
            closed_date DATE NOT NULL,
            is_recurring BOOLEAN DEFAULT FALSE,
            day_of_week INTEGER,
            reason VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(vendor_id, closed_date, is_recurring)
        )
    """)
    
    # ==================== SETTINGS ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_settings (
            id SERIAL PRIMARY KEY,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE UNIQUE,
            max_advance_days INTEGER DEFAULT 30,
            cancel_before_hours INTEGER DEFAULT 2,
            min_advance_hours INTEGER DEFAULT 2,
            allow_cancellation BOOLEAN DEFAULT TRUE,
            require_otp BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== LOCATION ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_location (
            id SERIAL PRIMARY KEY,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE UNIQUE,
            address_line1 VARCHAR(255),
            address_line2 VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            pincode VARCHAR(10),
            latitude DECIMAL(10,8),
            longitude DECIMAL(11,8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== EMAIL LOGS ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_email_logs (
            id SERIAL PRIMARY KEY,
            booking_id VARCHAR(50),
            vendor_id INTEGER,
            email_type VARCHAR(50) NOT NULL,
            recipient_email VARCHAR(255) NOT NULL,
            subject VARCHAR(500),
            body TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            error_message TEXT,
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== OTP VERIFICATIONS ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_otp_verifications (
            id SERIAL PRIMARY KEY,
            booking_id VARCHAR(50) REFERENCES nightlife_bookings(booking_id) ON DELETE CASCADE,
            otp_code VARCHAR(6) NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            user_phone VARCHAR(20),
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            verified_at TIMESTAMP
        )
    """)
    
    # ==================== GALLERY ====================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nightlife_gallery (
            id SERIAL PRIMARY KEY,
            vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
            image_url VARCHAR(500) NOT NULL,
            display_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== CREATE INDEXES ====================
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_vendor_id ON nightlife_table_types(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_table_type ON nightlife_tables(type_id)",
        "CREATE INDEX IF NOT EXISTS idx_slot_vendor ON nightlife_slots(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_booking_vendor ON nightlife_bookings(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_booking_date ON nightlife_bookings(date)",
        "CREATE INDEX IF NOT EXISTS idx_booking_status ON nightlife_bookings(status)",
        "CREATE INDEX IF NOT EXISTS idx_booking_email ON nightlife_bookings(user_email)",
        "CREATE INDEX IF NOT EXISTS idx_closed_dates_vendor ON nightlife_closed_dates(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_vendor ON nightlife_email_logs(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_booking ON nightlife_email_logs(booking_id)",
    ]
    
    for idx in indexes:
        cur.execute(idx)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ All tables created successfully!")

def seed_demo_data():
    """Seed demo vendor data"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    
    # Check if demo vendor exists
    cur.execute("SELECT id FROM vendors WHERE email = 'vendor@nightlife.com'")
    if cur.fetchone():
        print("ℹ️ Demo vendor already exists")
        cur.close()
        conn.close()
        return
    
    # Create demo vendor
    cur.execute("""
        INSERT INTO vendors (email, name, description, phone, upi_id)
        VALUES ('vendor@nightlife.com', 'Club Havana', 'Premium nightlife experience with VIP tables and great music', '+919876543210', 'clubhavana@upi')
        RETURNING id
    """)
    vendor_id = cur.fetchone()[0]
    
    # Create settings
    cur.execute("""
        INSERT INTO nightlife_settings (vendor_id, max_advance_days, cancel_before_hours, require_otp)
        VALUES (%s, 30, 2, true)
    """, (vendor_id,))
    
    # Create location
    cur.execute("""
        INSERT INTO nightlife_location (vendor_id, address_line1, city, state, pincode)
        VALUES (%s, 'MG Road, Near Metro Station', 'Mumbai', 'Maharashtra', '400001')
    """, (vendor_id,))
    
    # Create table types
    table_types = [
        ('Standard Table', 4, 8, 1500),
        ('Premium Table', 6, 5, 2500),
        ('VIP Booth', 10, 2, 5000)
    ]
    
    for name, seats, total, price in table_types:
        cur.execute("""
            INSERT INTO nightlife_table_types (vendor_id, name, seats, total_tables, price, time_start, time_end)
            VALUES (%s, %s, %s, %s, %s, '18:00', '02:00')
            RETURNING id
        """, (vendor_id, name, seats, total, price))
        type_id = cur.fetchone()[0]
        
        # Create tables
        for i in range(1, total + 1):
            status = 'free' if i <= (total // 2) else 'reserved'
            cur.execute("""
                INSERT INTO nightlife_tables (vendor_id, type_id, table_number, status)
                VALUES (%s, %s, %s, %s)
            """, (vendor_id, type_id, i, status))
    
    # Create slots
    slots = [
        ('Early Evening', '18:00', '20:00'),
        ('Prime Time', '20:00', '23:00'),
        ('Late Night', '23:00', '02:00')
    ]
    
    for name, start, end in slots:
        cur.execute("""
            INSERT INTO nightlife_slots (vendor_id, name, start_time, end_time)
            VALUES (%s, %s, %s, %s)
        """, (vendor_id, name, start, end))
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Demo data seeded!")

def init_database():
    """Initialize complete database"""
    print("🚀 Initializing Nightlife Database...")
    create_database()
    create_tables()
    seed_demo_data()
    print("✅ Database initialization complete!")

if __name__ == '__main__':
    init_database()
