#!/usr/bin/env python3
"""Script to add database indexes for performance optimization."""
from sqlalchemy import create_engine, text

# Database URL
DATABASE_URL = "postgresql+psycopg2://smartuser:smartpass@localhost:5433/smartmeeting"

def add_indexes():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Indexes for bookings
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings (user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_room_id ON bookings (room_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_start_time ON bookings (start_time);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_end_time ON bookings (end_time);"))

        # Indexes for reviews
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews (user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reviews_room_id ON reviews (room_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews (created_at);"))

        # Indexes for rooms
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rooms_capacity ON rooms (capacity);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rooms_location ON rooms (location);"))

        print("Indexes added successfully.")

if __name__ == "__main__":
    add_indexes()