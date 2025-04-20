# check_db.py
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("POSTGRES_URL")
engine = create_engine(DATABASE_URL)

def check_columns():
    inspector = inspect(engine)
    
    if 'products' not in inspector.get_table_names():
        print("❌ 'products' table doesn't exist!")
        return
    
    print("Current columns in 'products' table:")
    for column in inspector.get_columns('products'):
        print(f"- {column['name']} ({column['type']})")

def add_missing_columns():
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='products'
            AND column_name IN ('latest_prices', 'price_history')
        """))
        existing_columns = {row[0] for row in result}
        
        if 'latest_prices' not in existing_columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN latest_prices JSONB"))
            print("✅ Added latest_prices column")
        
        if 'price_history' not in existing_columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN price_history JSONB"))
            print("✅ Added price_history column")
        
        conn.commit()

if __name__ == "__main__":
    print("Current database schema:")
    check_columns()
    
    print("\nAttempting to add missing columns...")
    add_missing_columns()
    
    print("\nUpdated schema:")
    check_columns()