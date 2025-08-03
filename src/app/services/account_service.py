from src.app.domain.account import Account
from src.app.domain.enums import TxType
from src.app.infra.repositories import AccountRepo


class AccountService:
    """Пополнение, списание, история."""

    def __init__(self, acc_repo: AccountRepo):
        self._acc_repo = acc_repo

    # фасады
    def deposit(self, account_id: int, amount: int, reason: str) -> int:
        acc: Account = self._acc_repo.load(account_id)
        acc.apply(delta=amount, reason=reason, tx_type=TxType.DEPOSIT)
        self._acc_repo.save(acc)
        return acc.balance

    def charge_for_prediction(self, account_id: int, cost: int, reason: str) -> int:
        acc = self._acc_repo.load(account_id)
        acc.apply(delta=-cost, reason=reason, tx_type=TxType.PREDICTION_CHARGE)
        self._acc_repo.save(acc)
        return acc.balance

    def history(self, account_id: int):
        return self._acc_repo.load(account_id).history