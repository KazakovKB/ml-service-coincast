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

    def is_deposit(self) -> bool:
        return self.tx_type == TxType.DEPOSIT

    def is_prediction_charge(self) -> bool:
        return self.tx_type == TxType.PREDICTION_CHARGE

    def as_dict(self) -> dict:
        return {
            "owner_id": self.owner_id,
            "amount": self.amount,
            "tx_type": self.tx_type.value,
            "reason": self.reason,
            "balance_after": self.balance_after,
            "created_at": self.created_at.isoformat(),
        }

    def __str__(self):
        sign = "+" if self.amount > 0 else ""
        return f"[{self.created_at.isoformat()}] {self.tx_type.value}: {sign}{self.amount} ({self.reason}), баланс: {self.balance_after}"


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

if __name__ == '__main__':
    from user import Client, Admin, User

    user = Client(email="user1@mail.com", password_hash=User.hash_password("password123"))
    admin = Admin(email="admin@mail.com", password_hash=User.hash_password("admin_password123"))

    # Пополнение через администратора
    Admin.credit_user(user=user, amount=50, reason="Welcome bonus")

    # Транзакция добавилась в историю пользователя
    last_tx = user.account.history[-1]
    print(last_tx, end='\n\n')

    # Можно проверить тип транзакции
    print(f"is_deposit: {last_tx.is_deposit()}")
    print(f"is_prediction_charge: {last_tx.is_prediction_charge()}", end='\n\n')

    # Преобразовать для API/UI
    print(last_tx.as_dict())