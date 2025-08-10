import os, json, logging, asyncio
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
async def handle(body: str) -> None:
    payload = json.loads(body)
    job_id     = payload["job_id"]
    account_id = payload["account_id"]
    model_name = payload["model"]
    rows       = payload["data"]
    db: Session = SessionLocal()
    svc = PredictionService(AccountRepo(db), PredictionRepo(db))

    try:
        job = svc.process_job(
            job_id=job_id,
            account_id=account_id,
            model_name=model_name,
            raw_rows=rows,
        )
        db.commit()
        logging.info("job %s done: status=%s cost=%s", job.id, job.status, job.cost)

    except PredictionService.NotEnoughCredits:
        db.commit()
        logging.warning("job %s failed: not enough credits", job_id)

    except Exception as exc:
        logging.exception("job %s failed with unexpected error", job_id)
        try:
            PredictionRepo(db).mark_error(job_id, f"worker_error: {exc}")
            db.commit()
        except Exception:
            db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(app.run())