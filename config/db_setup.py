import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, UTC

# Connect to PostgreSQL inside Docker using your exact credentials
DATABASE_URL = "postgresql://finguard_stream:finguard@localhost:5432/transaction_ledger_db"

engine = create_engine(DATABASE_URL)

# This is exactly what the worker is looking for!
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Define the Core Financial Ledger Schema
class TransactionLedger(Base):
    __tablename__ = "transaction_ledger"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    merchant_type = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    status = Column(String(20), default="SETTLED") # SETTLED, FLAGGED, BLOCKED

def init_db():
    Base.metadata.create_all(bind=engine)
    print("PostgreSQL Financial Ledger schema initialized successfully!")

if __name__ == "__main__":
    init_db()