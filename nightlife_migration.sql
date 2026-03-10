-- Nightlife Module Database Migration Script
-- Run this against your PostgreSQL database (neondb) to ensure all required tables exist

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- DELIVERY_ORDERS TABLE - Ensure all required columns exist
-- ============================================================================

-- Check if delivery_orders table exists, if not create it
CREATE TABLE IF NOT EXISTS delivery_orders (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    items_json TEXT NOT NULL,
    subtotal INTEGER NOT NULL DEFAULT 0,
    delivery_charge INTEGER DEFAULT 0,
    packing_charge INTEGER DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    payment_method VARCHAR(20) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'UNPAID',
    user_name VARCHAR(120),
    user_phone VARCHAR(20),
    address_line1 VARCHAR(200),
    address_line2 VARCHAR(200),
    landmark VARCHAR(200),
    city VARCHAR(120),
    state VARCHAR(120),
    pincode VARCHAR(20),
    status VARCHAR(30) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add columns if they don't exist (for PostgreSQL)
ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS delivery_charge INTEGER DEFAULT 0;
ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS packing_charge INTEGER DEFAULT 0;

-- ============================================================================
-- NIGHTLIFE_VENDOR_CONFIGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS nightlife_vendor_configs (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL UNIQUE,
    max_advance_days INTEGER DEFAULT 365,
    cancel_before_hrs INTEGER DEFAULT 2,
    venue_name VARCHAR(200),
    addr1 VARCHAR(200),
    addr2 VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(20),
    banner_url VARCHAR(300),
    gallery_urls TEXT
);

-- ============================================================================
-- NIGHTLIFE_SLOTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS nightlife_slots (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    name VARCHAR(150) NOT NULL,
    start_time VARCHAR(5) NOT NULL,
    end_time VARCHAR(5) NOT NULL
);

-- ============================================================================
-- NIGHTLIFE_TABLE_TYPES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS nightlife_table_types (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    name VARCHAR(150) NOT NULL,
    seats INTEGER NOT NULL,
    total_tables INTEGER DEFAULT 0,
    price INTEGER DEFAULT 0,
    cancel_hours INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- NIGHTLIFE_TABLES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS nightlife_tables (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    table_number INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'free'
);

-- ============================================================================
-- NIGHTLIFE_BOOKINGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS nightlife_bookings (
    id SERIAL PRIMARY KEY,
    booking_id VARCHAR(50) UNIQUE NOT NULL,
    vendor_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    slot_id INTEGER NOT NULL,
    booking_date VARCHAR(10) NOT NULL,
    customer_name VARCHAR(150),
    customer_email VARCHAR(150),
    customer_phone VARCHAR(50),
    table_numbers TEXT,
    total_price INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    otp_code VARCHAR(10),
    otp_expiry TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- NIGHTLIFE_CLOSED_DATES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS nightlife_closed_dates (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    closed_date VARCHAR(10) NOT NULL,
    reason VARCHAR(200)
);

-- ============================================================================
-- RESTAURANTS TABLE (for menu items)
-- ============================================================================

CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    address VARCHAR(300) NOT NULL,
    description VARCHAR(1000),
    is_nightlife BOOLEAN DEFAULT FALSE,
    banner_image TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MENU_ITEMS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    price INTEGER NOT NULL,
    category VARCHAR(100),
    food_type VARCHAR(20),
    available BOOLEAN DEFAULT TRUE,
    image_url VARCHAR(300)
);

-- ============================================================================
-- VENDORS TABLE (if not exists)
-- ============================================================================

CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    restaurant_name VARCHAR(200) NOT NULL,
    owner_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    address VARCHAR(300) NOT NULL,
    password VARCHAR(150),
    upi_id VARCHAR(120),
    vendor_type VARCHAR(20) DEFAULT 'restaurant',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- USERS TABLE (if not exists)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for better performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_nightlife_bookings_vendor ON nightlife_bookings(vendor_id);
CREATE INDEX IF NOT EXISTS idx_nightlife_bookings_date ON nightlife_bookings(booking_date);
CREATE INDEX IF NOT EXISTS idx_nightlife_bookings_status ON nightlife_bookings(status);
CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant ON menu_items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_delivery_orders_vendor ON delivery_orders(vendor_id);
CREATE INDEX IF NOT EXISTS idx_delivery_orders_status ON delivery_orders(status);

-- ============================================================================
-- Sample Data - Insert a demo vendor if none exists
-- ============================================================================

-- Only insert if vendors table is empty
INSERT INTO vendors (restaurant_name, owner_name, email, phone, address, vendor_type)
SELECT 'Club Havana', 'Demo Owner', 'vendor@night.com', '9876543210', 'Pune, Maharashtra', 'nightlife'
WHERE NOT EXISTS (SELECT 1 FROM vendors LIMIT 1);

-- Print migration status
DO $$
BEGIN
    RAISE NOTICE 'Nightlife migration completed successfully!';
END $$;
