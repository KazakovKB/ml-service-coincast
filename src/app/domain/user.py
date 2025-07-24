from abc import ABC
from datetime import datetime, UTC
from enums import Role, TxType
from account import Account
import bcrypt


# === User ===
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
        return bcrypt.checkpw(plain.encode(), self.__password_hash.encode())

    @property
    def role(self) -> Role:
        return Role.CLIENT

    # запрет прямого доступа
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