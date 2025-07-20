from dataclasses import dataclass, field
from enums import TxType
from datetime import datetime, UTC
from typing import Sequence


@dataclass
class Transaction:
    owner_id: int
    amount: int
    tx_type: TxType
    reason: str
    balance_after: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InsufficientFunds(Exception):
    ...


class Account:
    """Кошелёк в условных кредитах."""
    def __init__(self, owner_id: int) -> None:
        self.owner_id = owner_id
        self.__balance: int = 0
        self.__history: list[Transaction] = []

    @property
    def balance(self) -> int:
        return self.__balance

    @property
    def history(self) -> Sequence[Transaction]:
        return tuple(self.__history)  # неизменяемая вью

    def apply(self, delta: int, reason: str, tx_type: TxType) -> None:
        new_balance = self.__balance + delta
        if new_balance < 0:
            raise InsufficientFunds("Not enough credits")
        self.__balance = new_balance
        self.__history.append(
            Transaction(
                owner_id=self.owner_id,
                amount=delta,
                tx_type=tx_type,
                reason=reason,
                balance_after=self.__balance,
            )
        )