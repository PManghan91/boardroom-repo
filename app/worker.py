import redis
import os
import time

print("Worker starting up...")

try:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    exit(1)


stream_name = "br:test"
group_name = "boardroom_group"
consumer_name = f"worker-{os.getpid()}"

# Create the consumer group on the stream
try:
    r.xgroup_create(stream_name, group_name, id="0", mkstream=True)
    print(f"Consumer group '{group_name}' created for stream '{stream_name}'.")
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" in str(e):
        print(f"Consumer group '{group_name}' already exists.")
    else:
        print(f"Error creating consumer group: {e}")
        exit(1)

print(f"Worker '{consumer_name}' is ready to consume messages from stream '{stream_name}'.")

while True:
    try:
        # Block and wait for new messages in the stream for this consumer group
        messages = r.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: ">"},  # '>' means only new messages
            count=1,
            block=5000,  # Block for 5000 milliseconds (5 seconds)
        )

        if not messages:
            # Timed out, no new messages
            continue

        for stream, message_list in messages:
            for message_id, data in message_list:
                print(f"Processing message {message_id}: {data}")
                # Simulate work
                time.sleep(1)
                # Acknowledge that the message has been processed
                r.xack(stream_name, group_name, message_id)
                print(f"Acknowledged message {message_id}.")

    except Exception as e:
        print(f"An error occurred during message processing: {e}")
        # Wait before retrying to avoid flooding logs in case of persistent errors
        time.sleep(5)
