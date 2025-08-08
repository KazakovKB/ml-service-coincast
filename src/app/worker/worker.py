import asyncio, json, logging, types, aiormq, aio_pika
from sqlalchemy.orm import Session

from src.app.infra.db import SessionLocal
from src.app.infra.mq import QUEUE_NAME, _connect
from src.app.infra.repositories import AccountRepo, PredictionRepo
from src.app.services.prediction_service import PredictionService


logging.basicConfig(level=logging.INFO)

async def handle(msg: aio_pika.IncomingMessage) -> None:
    """ Основной обработчик сообщений """

    async with msg.process(requeue=False):
        payload = json.loads(msg.body)
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
            resp = job.__dict__

        except PredictionService.NotEnoughCredits:
            db.rollback()
            resp = {"status": "error", "error": "not_enough_credits"}

        except Exception as exc:
            db.rollback()
            logging.exception("worker error")
            resp = {"status": "error", "error": str(exc)}

        finally:
            db.close()

        # отправить ответ
        if msg.reply_to:
            body = json.dumps(resp, default=str).encode()
            props = aiormq.spec.Basic.Properties(
                correlation_id=msg.correlation_id,
            )
            await msg.channel.basic_publish(
                body,
                routing_key=msg.reply_to,
                properties=props,
            )
            logging.info("reply cid=%s sent", msg.correlation_id)
        else:
            logging.warning("no reply_to given; cid=%s", msg.correlation_id)

async def main() -> None:
    conn = await _connect()
    ch   = await conn.channel()
    await ch.set_qos(prefetch_count=1)
    queue = await ch.declare_queue(QUEUE_NAME, durable=True)
    await queue.consume(handle, no_ack=False)
    logging.info("worker started; waiting for tasks")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())