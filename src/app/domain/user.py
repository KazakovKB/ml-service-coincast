from abc import ABC
from datetime import datetime, UTC
from enums import Role, TxType
from account import Account


class User(ABC):
    """Базовый пользователь."""
    __id_counter: int = 1

    def __init__(self, email: str, password_hash: str) -> None:
        self.id: int = User.__id_counter
        User.__id_counter += 1
        self.email: str = email
        self.__password_hash: str = password_hash
        self.created_at: datetime = datetime.now(UTC)
        self.account: Account = Account(owner_id=self.id)

    # проверка пароля
    def check_password(self, plain: str) -> bool:
        ...

    @property
    def role(self) -> Role:
        return Role.CLIENT

    # запрет прямого доступа
    def _change_balance(self, delta: int, reason: str, tx_type: TxType) -> None:
        self.account.apply(delta, reason, tx_type)


class Client(User):
    """Конечный пользователь ML-сервиса."""

    def pay_for_prediction(self, cost: int, reason: str) -> None:
        self._change_balance(-cost, reason, TxType.PREDICTION_CHARGE)


class Admin(User):
    """Администратор с правом пополнения чужих счетов."""

    @property
    def role(self) -> Role:
        return Role.ADMIN

    @staticmethod
    def credit_user(self, user: User, amount: int, reason: str = "Admin top-up") -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        user._change_balance(amount, reason, TxType.DEPOSIT)