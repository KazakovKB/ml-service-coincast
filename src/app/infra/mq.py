import os, json, uuid, asyncio, aio_pika, backoff
from typing import Any


RABBIT_URL = os.getenv("RABBIT_URL")
QUEUE_NAME = os.getenv("QUEUE_NAME")
RPC_TIMEOUT = int(os.getenv("RPC_REPLY_TIMEOUT"))

@backoff.on_exception(backoff.expo, aio_pika.exceptions.AMQPConnectionError, max_time=60)
async def _connect():
    """ Создать надёжное соединение с RabbitMQ """
    return await aio_pika.connect_robust(RABBIT_URL)


async def rpc_call(payload: dict[str, Any]) -> Any:
    """
    Опубликовать задачу и ждать ответа
    """
    conn = await _connect()
    # канал для взаимодействия
    channel = await conn.channel()

    # получать только одно сообщение за раз от брокера
    await channel.set_qos(prefetch_count=1)
    # создаёт основную очередь
    await channel.declare_queue(QUEUE_NAME, durable=True)

    # создаёт временную очередь
    callback_q = await channel.declare_queue(exclusive=True)
    # генерирует id запроса
    corr_id = uuid.uuid4().hex
    # объект для ожидания ответа
    fut: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

    async def on_reply(msg: aio_pika.IncomingMessage):
        if msg.correlation_id == corr_id:
            await msg.ack()
            fut.set_result(msg.body)

    # очередь-ответчик, чтобы получать ответы
    await callback_q.consume(on_reply)

    # публикует задачу
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload).encode(),
            correlation_id=corr_id,
            reply_to=callback_q.name,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=QUEUE_NAME,
    )

    # ожидает ответа
    body = await asyncio.wait_for(fut, timeout=RPC_TIMEOUT)
    await channel.close(); await conn.close()
    return json.loads(body)