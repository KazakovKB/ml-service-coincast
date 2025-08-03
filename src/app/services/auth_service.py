from dataclasses import dataclass
from typing import Callable

from src.app.domain.user import Client, Admin
from src.app.infra.repositories import UserRepo, AccountRepo


@dataclass(slots=True)
class TokenDTO:
    access_token: str
    token_type: str = "bearer"


class AuthService:
    """Регистрация и логин."""

    class EmailExists(Exception): ...
    class BadCredentials(Exception): ...

    def __init__(
        self,
        user_repo: UserRepo,
        account_repo: AccountRepo,
        token_factory: Callable[[int], str],
    ):
        self._users = user_repo
        self._accounts = account_repo
        self._make_token = token_factory

    def register(self, email: str, raw_password: str, is_admin=False) -> TokenDTO:
        if self._users.get_by_email(email):
            raise AuthService.EmailExists

        dom_user = (Admin if is_admin else Client)(email=email, password=Client.hash_password(raw_password))
        saved = self._users.add(dom_user)
        token = self._make_token(saved.id)
        return TokenDTO(access_token=token)

    def login(self, email: str, raw_password: str) -> TokenDTO:
        dom_user = self._users.get_by_email(email)
        if not dom_user or not dom_user.check_password(raw_password):
            raise AuthService.BadCredentials
        return TokenDTO(access_token=self._make_token(dom_user.id))