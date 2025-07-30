from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, UTC
from src.app.domain.enums import Role, TxType

Base = declarative_base()

class ORMUser(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, nullable=False)
    password      = Column(String, nullable=False)
    created_at    = Column(DateTime, default=datetime.now(UTC))
    role          = Column(Enum(Role), default=Role.CLIENT)

    account       = relationship("ORMAccount", uselist=False, back_populates="owner")
    prediction_jobs = relationship("ORMPredictionJob", back_populates="user")


class ORMAccount(Base):
    __tablename__ = "accounts"
    id            = Column(Integer, primary_key=True)
    balance       = Column(Integer, default=0)
    owner_id      = Column(Integer, ForeignKey("users.id"))

    owner         = relationship("ORMUser", back_populates="account")
    transactions  = relationship("ORMTransaction", back_populates="account")


class ORMTransaction(Base):
    __tablename__ = "transactions"
    id            = Column(Integer, primary_key=True)
    amount        = Column(Integer)
    tx_type       = Column(Enum(TxType))
    reason        = Column(String)
    balance_after = Column(Integer)
    created_at    = Column(DateTime, default=datetime.now(UTC))
    account_id    = Column(Integer, ForeignKey("accounts.id"))

    account       = relationship("ORMAccount", back_populates="transactions")


class ORMPredictionJob(Base):
    __tablename__ = "prediction_jobs"
    id            = Column(Integer, primary_key=True, index=True)
    owner_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_name    = Column(String, nullable=False)
    valid_input   = Column(JSON, nullable=False)
    predictions   = Column(JSON, nullable=False)
    invalid_rows  = Column(JSON, nullable=False)
    cost          = Column(Integer, nullable=False)
    created_at    = Column(DateTime, default=datetime.now(UTC))

    user          = relationship("ORMUser", back_populates="prediction_jobs")
