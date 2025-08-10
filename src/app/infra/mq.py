import os, json
from typing import Any
from faststream.rabbit import RabbitBroker

RABBIT_URL  = os.getenv("RABBIT_URL")
QUEUE_NAME  = os.getenv("QUEUE_NAME")

broker = RabbitBroker(RABBIT_URL)

async def start_broker() -> None:
    await broker.start()

async def stop_broker() -> None:
    await broker.stop()

async def rpc_predict(payload: dict[str, Any]) -> Any:
    msg = await broker.request(
        json.dumps(payload),
        queue=QUEUE_NAME,
    )
    return json.loads(msg.body)