import os
import json

from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

load_dotenv()


async def send_user_created_event(user_info: dict):
    producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_URL"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        message = {
            "event_type": "UserCreated",
            "user": user_info,
        }
        await producer.send_and_wait("user.user-events.v1", value=message)
        print("Message send to kafka:", message)
    finally:
        await producer.stop()
