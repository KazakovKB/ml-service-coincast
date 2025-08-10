import os, json, logging, types, asyncio
from sqlalchemy.orm import Session
from faststream.rabbit import RabbitBroker
from faststream import FastStream

from src.app.infra.db import SessionLocal
from src.app.infra.repositories import AccountRepo, PredictionRepo
from src.app.services.prediction_service import PredictionService

logging.basicConfig(level=logging.INFO)

RABBIT_URL = os.getenv("RABBIT_URL")
QUEUE_NAME = os.getenv("QUEUE_NAME")

broker = RabbitBroker(RABBIT_URL)
app = FastStream(broker)

@broker.subscriber(QUEUE_NAME)
async def handle(body: str) -> str:
    payload = json.loads(body)
    db: Session = SessionLocal()
    svc = PredictionService(AccountRepo(db), PredictionRepo(db))

    try:
        job = svc.make_prediction(
            user=types.SimpleNamespace(
                id=payload["user_id"],
                account=types.SimpleNamespace(id=payload["account_id"]),
            ),
            model_name=payload["model"],
            raw_rows=payload["data"],
        )
        db.commit()
        return json.dumps(job.__dict__, default=str)

    except PredictionService.NotEnoughCredits:
        db.rollback()
        return json.dumps({"status": "error", "error": "not_enough_credits"})
    except Exception as exc:
        db.rollback()
        logging.exception("worker error")
        return json.dumps({"status": "error", "error": str(exc)})
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(app.run())