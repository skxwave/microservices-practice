import json

from aiokafka import AIOKafkaProducer

from src.config import settings

TOPIC = "product.product-events.v1"

producer: AIOKafkaProducer | None = None


async def start_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()


async def stop_producer():
    await producer.stop()


async def send_product_created_event(product_info: dict):
    message = {
        "event_type": "ProductCreated",
        "product": product_info,
    }
    await producer.send_and_wait(TOPIC, value=message)
    print("ProductCreated send to kafka:", message)


async def send_product_updated_event(
    old_product_info: dict,
    new_product_info: dict,
):
    if old_product_info == new_product_info:
        print("Nothing changed")
        return
    message = {
        "event_type": "ProductUpdated",
        "old_product_info": old_product_info,
        "new_product_info": new_product_info,
    }
    await producer.send_and_wait(TOPIC, value=message)
    print("ProductUpdated send to kafka:", message)
