# check_schema.py
from db_4 import engine, Base, Product
from sqlalchemy import inspect

def check_database_schema():
    # Create an inspector to examine the database
    inspector = inspect(engine)
    
    # Check if 'products' table exists
    if 'products' not in inspector.get_table_names():
        print("❌ Table 'products' doesn't exist!")
        return False
    
    # Get columns from actual database
    db_columns = {col['name'] for col in inspector.get_columns('products')}
    
    # Get columns from SQLAlchemy model
    model_columns = {col.name for col in Product.__table__.columns}
    
    print("\nCurrent Database Schema:")
    for col in inspector.get_columns('products'):
        print(f"- {col['name']} ({col['type']})")
    
    print("\nSQLAlchemy Model Expects:")
    for col in Product.__table__.columns:
        print(f"- {col.name} ({col.type})")
    
    # Compare schemas
    if db_columns == model_columns:
        print("\n✅ Schema matches perfectly!")
        return True
    else:
        print("\n❌ Schema mismatch detected!")
        print("Missing in database:", model_columns - db_columns)
        print("Extra in database:", db_columns - model_columns)
        return False

def fix_schema():
    print("\nResetting database to match models...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("✅ Database reset complete")
    check_database_schema()

if __name__ == "__main__":
    if not check_database_schema():
        fix_schema()