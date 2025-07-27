import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from abc import ABC
from datetime import datetime, UTC
from domain.enums import Role, TxType
from domain.account import Account
import bcrypt


# === User ===
class User(ABC):
    """Базовый пользователь."""

    def __init__(self, email: str, password_hash: str) -> None:
        self.id: int | None = None
        self.email: str = email
        self.__password_hash: str = password_hash
        self.created_at: datetime = datetime.now(UTC)
        self.account: Account | None = None

    # проверка пароля
    def check_password(self, plain: str) -> bool:
        return bcrypt.checkpw(plain.encode(), self.__password_hash.encode())

    @property
    def password_hash(self):
        return self.__password_hash

    @property
    def role(self) -> Role:
        return Role.CLIENT

    def _change_balance(self, delta: int, reason: str, tx_type: TxType) -> None:
        self.account.apply(delta, reason, tx_type)

    @staticmethod
    def hash_password(plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# === Client ===
class Client(User):
    """Конечный пользователь ML-сервиса."""

    def pay_for_prediction(self, cost: int, reason: str) -> None:
        self._change_balance(-cost, reason, TxType.PREDICTION_CHARGE)


# === Admin ===
class Admin(User):
    """Администратор с правом пополнения чужих счетов."""

    @property
    def role(self) -> Role:
        return Role.ADMIN

    @staticmethod
    def credit_user(user: User, amount: int, reason: str = "Admin top-up") -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        user._change_balance(amount, reason, TxType.DEPOSIT)


if __name__ == '__main__':
    # Пользователь регистрируется
    raw_password = "password123"
    hashed_password = User.hash_password(raw_password)
    user = Client(email="user1@example.ru", password_hash=hashed_password)

    # Пользователь вводит email + пароль для входа
    login_attempt = input('Enter password:')
    if user.check_password(login_attempt):
        print("Login success!")
    else:
        print("Wrong password")