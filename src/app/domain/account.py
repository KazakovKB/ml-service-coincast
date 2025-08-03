from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import List, Sequence, Dict, Any

from src.app.domain.enums import TxType


@dataclass
class Transaction:
    account_id: int | None
    amount: int
    tx_type: TxType
    reason: str
    balance_after: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _persisted: bool = False                 # признак «уже в БД»

    # небольшие хелперы
    def is_deposit(self) -> bool:
        return self.tx_type == TxType.DEPOSIT

    def is_prediction_charge(self) -> bool:
        return self.tx_type == TxType.PREDICTION_CHARGE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "amount": self.amount,
            "tx_type": self.tx_type.value,
            "reason": self.reason,
            "balance_after": self.balance_after,
            "created_at": self.created_at.isoformat(),
            "_persisted": self._persisted,
        }


class InsufficientFunds(Exception):
    ...

class Account:
    """Кошелёк в условных кредитах."""

    def __init__(
        self,
        owner_id: int,
        id_: int | None = None,
        balance: int = 0,
    ) -> None:
        self.id: int | None = id_
        self.owner_id = owner_id
        self.__balance: int = balance
        self.__history: List[Transaction] = []

    # фабрики
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        """Собрать агрегат из plain-dict (DTO от репозитория)."""
        acc = cls(
            id_=data.get("id"),
            owner_id=data["owner_id"],
            balance=data.get("balance", 0),
        )

        for tx_dto in data.get("history", []):
            # гарантируем наличие _persisted
            tx_dto.setdefault("_persisted", True)
            acc.__history.append(Transaction(**tx_dto))
        return acc

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "balance": self.__balance,
            "history": [tx.as_dict() for tx in self.__history],
        }

    @property
    def balance(self) -> int:
        return self.__balance

    @property
    def history(self) -> Sequence[Transaction]:
        return tuple(self.__history)

    # бизнес-методы
    def apply(self, delta: int, reason: str, tx_type: TxType) -> None:
        new_balance = self.__balance + delta
        if new_balance < 0:
            raise InsufficientFunds("Insufficient funds")

        self.__balance = new_balance
        self.__history.append(
            Transaction(
                account_id=self.id,
                amount=delta,
                tx_type=tx_type,
                reason=reason,
                balance_after=self.__balance,
                _persisted=False,
            )
        )

    def pending_transactions(self) -> List[Transaction]:
        """Вернуть транзакции, которые ещё не сохранены в БД."""
        return [tx for tx in self.__history if not tx._persisted]