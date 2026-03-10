"""Migration script to add missing columns to existing database"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        conn = db.engine.connect()
        
        # Add vendor_type column if not exists
        try:
            conn.execute(text("ALTER TABLE vendors ADD COLUMN vendor_type VARCHAR(20) DEFAULT 'restaurant'"))
            conn.commit()
            print("✅ Added vendor_type column")
        except Exception as e:
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  vendor_type column already exists")
            else:
                print(f"⚠️  vendor_type: {e}")
        
        # Set default vendor_type for existing vendors
        try:
            conn.execute(text("UPDATE vendors SET vendor_type = 'restaurant' WHERE vendor_type IS NULL"))
            conn.commit()
            print("✅ Updated existing vendors")
        except Exception as e:
            print(f"⚠️  Update vendors: {e}")
        
        # Check and add missing columns to nightlife_bookings
        try:
            # Check if 'date' column exists in nightlife_bookings
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='nightlife_bookings' AND column_name='date'"))
            if not result.fetchone():
                conn.execute(text("ALTER TABLE nightlife_bookings ADD COLUMN date VARCHAR(10)"))
                # Copy from booking_date if exists
                try:
                    conn.execute(text("UPDATE nightlife_bookings SET date = booking_date WHERE date IS NULL"))
                except:
                    pass
                conn.commit()
                print("✅ Added date column to nightlife_bookings")
        except Exception as e:
            print(f"⚠️  nightlife_bookings date: {e}")
        
        conn.close()
        print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
