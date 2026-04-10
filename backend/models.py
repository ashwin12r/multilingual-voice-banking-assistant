from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from database import Base, engine

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    balance = Column(Float, default=50000.0)
    
    transactions = relationship("Transaction", back_populates="user")
    emis = relationship("EMI", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String) # Storing as string YYYY-MM-DD for simplicity
    description = Column(String)
    amount = Column(Float)
    type = Column(String) # 'credit' or 'debit'
    category = Column(String, default="Uncategorized")
    
    user = relationship("User", back_populates="transactions")

class EMI(Base):
    __tablename__ = "emis"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    amount = Column(Float)
    due_date = Column(String)
    status = Column(String, default="Pending")
    
    user = relationship("User", back_populates="emis")

Base.metadata.create_all(bind=engine)