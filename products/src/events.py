import json
from aiokafka import AIOKafkaProducer


async def send_product_created_event(product_info: dict):
    # If local run — localhost:9094.
    # If inside docker — kafka:9092.
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9094",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        message = {
            "event_type": "ProductCreated",
            "product": product_info,
        }
        await producer.send_and_wait("product.product-events.v1", value=message)
        print("ProductCreated send to kafka:", message)
    finally:
        await producer.stop()


async def send_product_updated_event(
    old_product_info: dict,
    new_product_info: dict,
):
    if old_product_info == new_product_info:
        print("Nothing changed")
        return
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9094",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        message = {
            "event_type": "ProductUpdated",
            "old_product_info": old_product_info,
            "new_product_info": new_product_info,
        }
        await producer.send_and_wait("product.product-events.v1", value=message)
        print("ProductUpdated send to kafka:", message)
    finally:
        await producer.stop()
