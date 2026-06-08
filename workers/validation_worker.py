import time
import json
from redis import Redis
from sqlalchemy.orm import Session
from config.db_setup import SessionLocal, TransactionLedger

# Connect to Redis and initialize our stream settings
redis_client = Redis(host="localhost", port=6379, decode_responses=True)
STREAM_NAME = "transactions:stream"
CONSUMER_GROUP = "validation_group"
CONSUMER_NAME = "worker_1"

def init_consumer_group():
    """Initializes a Redis Consumer Group so multiple workers can split the load safely."""
    try:
        # Create a consumer group that reads from the very beginning ('0') of the stream
        redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        print(f"Consumer Group '{CONSUMER_GROUP}' initialized successfully.")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            # It just means the group was already created during a previous run
            print(f"Consumer Group '{CONSUMER_GROUP}' already exists. Resuming...")
        else:
            print(f"Error creating consumer group: {e}")

def process_stream():
    init_consumer_group()
    print(f"{CONSUMER_NAME} is active and listening for transactions...")
    
    db: Session = SessionLocal()
    
    try:
        while True:
            # SDE Rule: Read new, unacknowledged messages ('>') from the consumer group
            # count=1 means this worker grabs exactly one transaction at a time to process
            # block=1000 means wait up to 1000ms for a new message if the stream is empty
            response = redis_client.xreadgroup(CONSUMER_GROUP, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=1000)
            
            if not response:
                continue # No new messages, loop back and check again
                
            for stream, messages in response:
                for message_id, message_data in messages:
                    # Extract and parse our flattened JSON payload string
                    tx_payload = json.loads(message_data["payload"])
                    
                    print(f"Processing TX: {tx_payload['transaction_id']} | User: {tx_payload['user_id']}")
                    
                    # --- SDE Masterstroke: High-Performance Rule Validation ---
                    # Rule 1: Flag suspiciously large single amounts for the upcoming AI auditor
                    is_suspicious = tx_payload["amount"] > 5000.0
                    status = "FLAGGED" if is_suspicious else "SETTLED"
                    
                    # Create our persistent record instance matching our PostgreSQL Schema
                    new_tx = TransactionLedger(
                        transaction_id=tx_payload["transaction_id"],
                        user_id=tx_payload["user_id"],
                        amount=tx_payload["amount"],
                        currency=tx_payload["currency"],
                        merchant_type=tx_payload["merchant_type"],
                        location=tx_payload["location"],
                        status=status
                    )
                    
                    # Write to PostgreSQL ledger
                    db.add(new_tx)
                    db.commit()
                    
                    # SDE Rule: Acknowledge (XACK) the message in Redis so no other worker retries it
                    redis_client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
                    print(f"Successfully written to Ledger with status: {status}")
                    
    except KeyboardInterrupt:
        print("\nWorker stopped safely.")
    finally:
        db.close()

if __name__ == "__main__":
    process_stream()