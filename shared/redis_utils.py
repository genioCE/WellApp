import redis
import json
import time
from datetime import datetime

# Retry connection logic
def get_redis_connection():
    while True:
        try:
            r = redis.Redis(host='genio_redis', port=6379, decode_responses=True)
            r.ping()  # Test connection
            return r
        except redis.exceptions.ConnectionError:
            print("Redis not available yet, retrying...")
            time.sleep(1)

r = get_redis_connection()

# JSON serializer for datetime objects
def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Single correct publish function
def publish(channel: str, message: dict):
    r.publish(channel, json.dumps(message, default=default_serializer))

def subscribe(channel: str):
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    return pubsub
