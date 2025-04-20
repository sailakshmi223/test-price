from sqlalchemy import create_engine, Column, String, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import uuid
import os
import logging
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    url = Column('url', String(500), unique=True)
    retailer = Column('retailer', String(50))
    latest_prices = Column('latest_prices', JSON)
    price_history = Column('price_history', JSON)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_product_to_db(db, url, retailer, latest_prices=None, price_history=None):
    try:
        # Check if product already exists
        existing_product = db.query(Product).filter(Product.url == url).first()
        
        if existing_product:
            # Update existing product
            if isinstance(latest_prices, str):
                latest_prices = json.loads(latest_prices)
            if isinstance(price_history, str):
                price_history = json.loads(price_history)
            
            # Update latest prices
            existing_product.latest_prices = latest_prices or existing_product.latest_prices
            
            # Append new price history if different from last entry
            if price_history and isinstance(price_history, list):
                if not existing_product.price_history:
                    existing_product.price_history = []
                
                # Only add if price changed or no history exists
                if (not existing_product.price_history or 
                    price_history[-1]['value'] != existing_product.price_history[-1].get('value')):
                    existing_product.price_history.extend(price_history)
            
            db.commit()
            db.refresh(existing_product)
            return existing_product
        else:
            # Add new product
            if isinstance(latest_prices, str):
                latest_prices = json.loads(latest_prices)
            if isinstance(price_history, str):
                price_history = json.loads(price_history)
                
            product = Product(
                url=url[:500],
                retailer=retailer[:50],
                latest_prices=latest_prices or {},
                price_history=price_history or []
            )
            db.add(product)
            db.commit()
            db.refresh(product)
            return product
            
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        # Try to get the existing product if unique constraint failed
        existing = db.query(Product).filter(Product.url == url).first()
        if existing:
            return existing
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        return None

def update_product_prices(db, url, new_price_data):
    try:
        product = db.query(Product).filter(Product.url == url).first()
        if product:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Update latest prices
            product.latest_prices = {
                'value': new_price_data['value'],
                'currency': 'INR',
                'timestamp': timestamp
            }
            
            # Add to price history if price changed
            if (not product.price_history or 
                product.price_history[-1]['value'] != new_price_data['value']):
                
                history_entry = {
                    'value': new_price_data['value'],
                    'currency': 'INR',
                    'timestamp': timestamp
                }
                
                if not product.price_history:
                    product.price_history = [history_entry]
                else:
                    product.price_history.append(history_entry)
            
            db.commit()
            db.refresh(product)
            return product
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating product prices: {str(e)}")
        return None

if __name__ == "__main__":
    # This will create tables if they don't exist
    Base.metadata.create_all(engine)
    logger.info("✅ Database tables verified")