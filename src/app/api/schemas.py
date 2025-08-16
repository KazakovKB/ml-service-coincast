from pydantic import BaseModel, conint, ConfigDict
from datetime import datetime
from typing import List, Any, Tuple
from src.app.domain.enums import TxType, JobStatus

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Balance(BaseModel):
    balance: int

class TopUp(BaseModel):
    amount: conint(gt=0)
    reason: str | None = "Manual top-up"

class PredictionIn(BaseModel):
    model_name: str
    data: List[dict]

class PredictionOut(BaseModel):
    id: int
    model_name: str
    predictions: List[Any]
    valid_input: List[Any]
    invalid_rows: List[Tuple[int, Any]]
    cost: int
    created_at: datetime
    status: JobStatus
    error: str | None = None

    class Config:
        orm_mode = True

class PredictionShort(BaseModel):
    id: int
    model_name: str
    cost: int
    created_at: datetime
    status: JobStatus

    model_config = ConfigDict(from_attributes=True)

class TransactionOut(BaseModel):
    amount: int
    tx_type: TxType
    reason: str
    balance_after: int
    created_at: datetime

    class Config:
        orm_mode = True

