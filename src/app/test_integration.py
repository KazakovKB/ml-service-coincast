import pytest
from src.app.infra.db import SessionLocal, DATABASE_URL
from sqlalchemy import create_engine
from src.app.infra.models import ORMUser, ORMAccount, ORMTransaction, ORMPredictionJob, Base, TxType
from src.app.domain.user import Client, Admin
from src.app.domain.account import Account

# Фикстура для сессии
@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

# инициализация таблиц
@pytest.fixture(scope="function", autouse=True)
def prepare_schema():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def transaction_record(user: Client, account_id: int):
    last_tx = user.account.history[-1]
    return ORMTransaction(
        amount=last_tx.amount,
        tx_type=last_tx.tx_type,
        reason=last_tx.reason,
        balance_after=last_tx.balance_after,
        account_id=account_id
    )

def create_user(user: Client):
    orm_user = ORMUser(
        email=user.email,
        password=user.password,
        role=user.role
    )

    return orm_user

def test_user_creation_and_account(db):

    user = Client(email="testuser@example.com", password=Client.hash_password("pass"))
    orm_user = create_user(user)
    db.add(orm_user)
    db.commit()
    db.refresh(orm_user)
    user.id = orm_user.id
    user.account = Account(owner_id=user.id)

    orm_account = ORMAccount(
        balance=user.account.balance,
        owner_id=orm_user.id
    )
    db.add(orm_account)
    db.commit()
    db.refresh(orm_account)
    user.account.id = orm_account.id

    assert orm_user.email == "testuser@example.com"
    assert orm_account.balance == 0

def test_deposit_by_user(db):
    user = Client(email="user@example.com", password=Client.hash_password("pass"))
    orm_user = create_user(user)
    db.add(orm_user)
    db.commit()
    db.refresh(orm_user)
    user.id = orm_user.id
    user.account = Account(owner_id=user.id)

    orm_account = ORMAccount(balance=user.account.balance, owner_id=orm_user.id)
    db.add(orm_account)
    db.commit()
    db.refresh(orm_account)
    user.account.id = orm_account.id

    # Пополнение баланса пользователем
    user.account.apply(delta=200, reason="User top-up", tx_type=TxType.DEPOSIT)
    orm_account.balance = user.account.balance
    orm_tx = transaction_record(user, orm_account.id)
    db.add(orm_tx)
    db.commit()
    db.refresh(orm_account)

    assert orm_account.balance == 200
    txs = db.query(ORMTransaction).filter_by(account_id=orm_account.id).all()
    assert len(txs) == 1
    assert txs[0].amount == 200
    assert txs[0].tx_type == TxType.DEPOSIT

def test_deposit_by_admin(db):
    admin = Admin(email="admin@example.com", password=Admin.hash_password("admin123"))
    user = Client(email="user@example.com", password=Client.hash_password("user123"))

    orm_user = create_user(user)
    db.add(orm_user)
    db.commit()
    db.refresh(orm_user)
    user.id = orm_user.id
    user.account = Account(owner_id=user.id)

    orm_account = ORMAccount(balance=user.account.balance, owner_id=orm_user.id)
    db.add(orm_account)
    db.commit()
    db.refresh(orm_account)
    user.account.id = orm_account.id

    # Пополнение баланса админом
    admin.credit_user(user, amount=300, reason="Admin top-up")
    orm_account.balance = user.account.balance
    orm_tx = transaction_record(user, orm_account.id)
    db.add(orm_tx)
    db.commit()
    db.refresh(orm_account)

    assert orm_account.balance == 300
    txs = db.query(ORMTransaction).filter_by(account_id=orm_account.id).all()
    assert len(txs) == 1
    assert txs[0].reason == "Admin top-up"
    assert txs[0].tx_type == TxType.DEPOSIT

def test_charge_for_prediction(db):
    user = Client(email="user@example.com", password=Client.hash_password("pass"))
    orm_user = create_user(user)
    db.add(orm_user)
    db.commit()
    db.refresh(orm_user)
    user.id = orm_user.id
    user.account = Account(owner_id=user.id)

    user.account.apply(delta=150, reason='User top-up', tx_type=TxType.DEPOSIT)
    orm_account = ORMAccount(balance=user.account.balance, owner_id=orm_user.id)
    db.add(orm_account)
    db.commit()
    db.refresh(orm_account)
    user.account.id = orm_account.id

    # Списание за предсказание
    user.pay_for_prediction(cost=50, reason="prediction")
    orm_account.balance = user.account.balance
    orm_tx = transaction_record(user, orm_account.id)
    db.add(orm_tx)
    db.commit()
    db.refresh(orm_account)

    assert orm_account.balance == 100
    txs = db.query(ORMTransaction).filter_by(account_id=orm_account.id).all()
    assert len(txs) == 1
    assert txs[0].amount == -50
    assert txs[0].tx_type == TxType.PREDICTION_CHARGE

def test_transaction_history(db):
    user = Client(email="user@example.com", password=Client.hash_password("pass"))
    orm_user = create_user(user)
    db.add(orm_user)
    db.commit()
    db.refresh(orm_user)
    user.id = orm_user.id
    user.account = Account(owner_id=user.id)

    orm_account = ORMAccount(balance=user.account.balance, owner_id=orm_user.id)
    db.add(orm_account)
    db.commit()
    db.refresh(orm_account)
    user.account.id = orm_account.id

    # Пополнение
    user.account.apply(delta=100, reason="User top-up", tx_type=TxType.DEPOSIT)
    orm_account.balance = user.account.balance
    db.add(transaction_record(user, orm_account.id))
    db.commit()
    db.refresh(orm_account)
    # Списание
    user.pay_for_prediction(cost=40, reason="prediction")
    orm_account.balance = user.account.balance
    db.add(transaction_record(user, orm_account.id))
    db.commit()
    db.refresh(orm_account)

    txs = db.query(ORMTransaction).filter_by(account_id=orm_account.id).all()
    assert len(txs) == 2
    assert txs[0].tx_type == TxType.DEPOSIT
    assert txs[1].tx_type == TxType.PREDICTION_CHARGE
    assert txs[0].balance_after == 100
    assert txs[1].balance_after == 60

def test_prediction_job(db):
    user = Client(email="user@example.com", password=Client.hash_password("pass"))
    orm_user = create_user(user)
    db.add(orm_user)
    db.commit()
    db.refresh(orm_user)
    user.id = orm_user.id
    user.account = Account(owner_id=user.id)

    job = ORMPredictionJob(
        owner_id=orm_user.id,
        model_name="DemoModel",
        valid_input=[{"feature1": 1, "feature2": 2}],
        predictions=[0.75],
        invalid_rows=[(2, {"feature1": None, "feature2": 3})],
        cost=25
    )
    db.add(job)
    db.commit()

    jobs = db.query(ORMPredictionJob).filter_by(owner_id=orm_user.id).all()
    assert len(jobs) == 1
    assert jobs[0].model_name == "DemoModel"
    assert jobs[0].cost == 25