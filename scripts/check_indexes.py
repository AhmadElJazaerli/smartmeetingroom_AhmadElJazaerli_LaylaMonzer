#!/usr/bin/env python3
"""Script to check database indexes."""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://smartuser:smartpass@localhost:5433/smartmeeting"

def check_indexes():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # List tables
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';"))
        print("Tables:")
        for row in result:
            print(f"  {row[0]}")
        
        # Indexes
        result = conn.execute(text("""
            SELECT schemaname, tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """))
        print("\nDatabase Indexes:")
        for row in result:
            print(f"Table: {row[1]}, Index: {row[2]}, Definition: {row[3]}")

if __name__ == "__main__":
    check_indexes()