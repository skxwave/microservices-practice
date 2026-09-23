import asyncio
import json
from aiokafka import AIOKafkaConsumer

TOPICS = ["user.user-events.v1"]


async def process_message(payload: dict):
    event_type = payload.get("event_type")

    if event_type == "UserCreated":
        user_data = payload.get("user")
        username = user_data.get("username")
        email = user_data.get("email")
        print(f"User '{username}':'{email}' created!")
    else:
        print("Unknown event type")


async def run_consumer():
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers="localhost:9094",  # TODO: 9092 inside docker
        group_id="notifications-service-group",
        enable_auto_commit=False,
        auto_offset_reset="earliest",  # read from beginning, if group is new
    )
    await consumer.start()

    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))

                # processing message
                await process_message(payload)

                # manually commit!
                await consumer.commit()
            except json.JSONDecodeError:
                print("JSON is not valid")
            except Exception as e:
                print(f"Unknown error (offset={msg.offset}): {e}")
                await asyncio.sleep(2)
    finally:
        # Graceful shutdown
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_consumer())
