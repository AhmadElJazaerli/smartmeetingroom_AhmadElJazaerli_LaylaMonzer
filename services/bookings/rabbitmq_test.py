import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
channel = connection.channel()
channel.queue_declare(queue="bookings", durable=True)
message = {
    "event": "test_message",
    "booking_id": 999,
    "user_id": 1,
    "room_id": 1,
    "start_time": "2025-12-01T10:00:00",
    "end_time": "2025-12-01T11:00:00"
}
channel.basic_publish(
    exchange="",
    routing_key="bookings",
    body=json.dumps(message),
    properties=pika.BasicProperties(delivery_mode=2)
)
print("Test message sent to RabbitMQ.")
connection.close()
