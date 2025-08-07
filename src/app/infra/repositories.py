from typing import Optional, List
from sqlalchemy.orm import Session
from src.app.infra.models import ORMUser, ORMAccount, ORMTransaction, ORMPredictionJob
from src.app.domain.user import Client, Admin
from src.app.domain.account import Account
from src.app.domain.prediction import PredictionJob
from src.app.domain.enums import Role, TxType

# ORM < - > Domain сопоставление

class UserRepo:

    def __init__(self, session: Session):
        self._s = session

    def get(self, user_id: int) -> Client:
        orm = self._s.get(ORMUser, user_id)
        if not orm:
            raise ValueError(f"User {user_id} not found")

        return self._to_domain(orm)

    def get_by_email(self, email: str) -> Optional[Client]:
        orm = self._s.query(ORMUser).filter_by(email=email).first()
        return self._to_domain(orm) if orm else None

    def add(self, dom_user: Client) -> Client:
        orm_user = ORMUser(
            email=dom_user.email,
            password=dom_user.password,
            role=dom_user.role,
        )
        self._s.add(orm_user)
        self._s.flush()

        # создать счёт с нулевым балансом
        orm_acc = ORMAccount(balance=0, owner_id=orm_user.id)
        self._s.add(orm_acc)
        self._s.commit()

        # вернуть доменный объект с заполненными id
        dom_user.id = orm_user.id
        dom_user.account = Account.from_dict(
            {"id": orm_acc.id,
             "owner_id": orm_user.id,
             "balance": orm_acc.balance}
        )
        return dom_user

    @staticmethod
    def _to_domain(orm: type[ORMUser]) -> Client:
        cls = Admin if orm.role is Role.ADMIN else Client
        dom = cls(orm.email, orm.password)
        dom.id = orm.id
        dom.account = Account.from_dict(
            {"id": orm.account.id,
             "owner_id": orm.id,
             "balance": orm.account.balance}
        )
        return dom


class AccountRepo:

    def __init__(self, s: Session) -> None:
        self._s = s

    @property
    def session(self) -> Session:
        return self._s

    def load(self, account_id: int) -> Account:
        orm_acc = self._s.get(ORMAccount, account_id)
        if orm_acc is None:
            raise ValueError("Account not found")

        acc = Account.from_dict(
            {"id": orm_acc.id, "owner_id": orm_acc.owner_id, "balance": 0}
        )

        for trx in sorted(orm_acc.transactions, key=lambda t: t.created_at):
            acc.apply(
                delta  = trx.amount,
                reason = trx.reason,
                tx_type= TxType(trx.tx_type),
            )
            acc.history[-1]._persisted = True

        return acc

    def save(self, dom_acc: Account) -> None:
        orm_acc = self._s.get(ORMAccount, dom_acc.id)
        orm_acc.balance = dom_acc.balance

        for tx in dom_acc.pending_transactions():       # only new
            self._s.add(
                ORMTransaction(
                    account_id   = orm_acc.id,
                    amount       = tx.amount,
                    tx_type      = tx.tx_type,
                    reason       = tx.reason,
                    balance_after= tx.balance_after,
                    created_at   = tx.created_at,
                )
            )
            tx._persisted = True


class PredictionRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def add(self, job: PredictionJob) -> PredictionJob:
        orm = ORMPredictionJob(
            owner_id     = job.owner_id,
            model_name   = job.model_name,
            valid_input  = job.valid_input,
            predictions  = job.predictions,
            invalid_rows = job.invalid_rows,
            cost         = job.cost,
            status       = job.status,
            error        = job.error,
            created_at   = job.created_at,
        )
        self._s.add(orm)
        self._s.flush()

        return PredictionJob(
            id            = orm.id,
            owner_id      = orm.owner_id,
            model_name    = orm.model_name,
            valid_input   = orm.valid_input,
            predictions   = orm.predictions,
            invalid_rows  = orm.invalid_rows,
            cost          = orm.cost,
            status        = orm.status,
            error         = orm.error,
            created_at    = orm.created_at,
        )

    def list_by_user(self, user_id: int) -> List[PredictionJob]:
        rows = (
            self._s.query(ORMPredictionJob)
            .filter_by(owner_id=user_id)
            .order_by(ORMPredictionJob.created_at.desc())
            .all()
        )
        return [
            PredictionJob(
                id           = r.id,
                owner_id     = r.owner_id,
                model_name   = r.model_name,
                valid_input  = r.valid_input,
                predictions  = r.predictions,
                invalid_rows = r.invalid_rows,
                cost         = r.cost,
                status       = r.status,
                error        = r.error,
                created_at   = r.created_at,
            )
            for r in rows
        ]