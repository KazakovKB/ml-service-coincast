import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from infra.db import engine, SessionLocal
from infra.models import ORMUser, ORMAccount, Base
from domain.user import Client, Admin
from sqlalchemy.exc import IntegrityError
import logging

logging.basicConfig(level=logging.INFO)

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    demo_user  = Client("demo@user",  Client.hash_password("user"))
    demo_admin = Admin ("demo@admin", Admin.hash_password("admin"))

    for dom in (demo_user, demo_admin):
        orm = ORMUser(email=dom.email,
                      password_hash=dom.password_hash,
                      role=dom.role)
        db.add(orm)
        try:
            db.commit()
            db.refresh(orm)


            start = 0
            db.add(ORMAccount(balance=start, owner_id=orm.id))
            db.commit()
            logging.info(f"User '{dom.email}' added successfully.")
        except IntegrityError:
            db.rollback()
            logging.info(f"User '{dom.email}' already exists. Skipping.")

if __name__ == "__main__":
    main()