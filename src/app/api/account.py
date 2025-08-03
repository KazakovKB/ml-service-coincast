from fastapi import APIRouter, Depends

from src.app.api.schemas import Balance, TopUp, TransactionOut
from src.app.api.deps import get_current_user, get_account_service
from src.app.services.account_service import AccountService
from src.app.domain.user import Client


router = APIRouter(prefix="/account", tags=["Account"])

@router.get("/balance", response_model=Balance)
def balance(user: Client = Depends(get_current_user)):
    return Balance(balance=user.account.balance)


@router.post("/top-up", response_model=Balance, status_code=201)
def top_up(
    top: TopUp,
    user: Client = Depends(get_current_user),
    svc: AccountService = Depends(get_account_service),
):
    new_balance = svc.deposit(user.account.id, top.amount, top.reason)
    updated_txs = svc.history(user.account.id)
    return Balance(balance=new_balance)


@router.get("/transactions", response_model=list[TransactionOut])
def history(
    user = Depends(get_current_user),
    svc: AccountService = Depends(get_account_service),
):
    return svc.history(user.account.id)