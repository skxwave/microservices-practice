import json
from aiokafka import AIOKafkaProducer


async def send_user_created_event(user_info: dict):
    # If local run — localhost:9094.
    # If inside docker — kafka:9092.
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9094",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        message = {
            "user": user_info,
            "action": "created",
        }
        await producer.send_and_wait("user.events", value=message)
        print("Message send to kafka:", message)
    finally:
        await producer.stop()
