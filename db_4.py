from sqlalchemy import create_engine, Column, String, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from dotenv import load_dotenv
import uuid
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("POSTGRES_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    product_id = Column('product_id', PG_UUID(as_uuid=True), 
                     primary_key=True, 
                     default=uuid.uuid4)
    url = Column('url', String(500))
    retailer = Column('retailer', String(50))
    
    # New columns we want to add
    latest_prices = Column('latest_prices', JSON, nullable=True)
    price_history = Column('price_history', JSON, nullable=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_product_to_db(db, url, retailer, latest_prices=None, price_history=None):
    try:
        product = Product(
            url=url[:500],
            retailer=retailer[:50],
            latest_prices=latest_prices,
            price_history=price_history
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        return None

def migrate_database():
    """Safely add new columns without dropping tables"""
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='products' 
            AND column_name IN ('latest_prices', 'price_history')
        """))
        existing_columns = {row[0] for row in result}
        
        # Add missing columns
        if 'latest_prices' not in existing_columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN latest_prices JSONB"))
            logger.info("Added latest_prices column")
        
        if 'price_history' not in existing_columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN price_history JSONB"))
            logger.info("Added price_history column")
        
        conn.commit()

def initialize_db():
    """Initialize database with minimal impact"""
    try:
        migrate_database()
        Base.metadata.create_all(engine)  # Creates any missing tables
        logger.info("✅ Database initialization complete")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    initialize_db()