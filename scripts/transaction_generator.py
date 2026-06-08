import time
import random
import json
import uuid
from datetime import datetime
from redis import Redis

# Connect to Redis running inside Docker
redis_client = Redis(host="localhost", port=6379, decode_responses=True)

# Configuration settings
STREAM_NAME = "transactions:stream"
MERCHANT_TYPES = ["e_commerce", "retail", "atm", "restaurant", "wire_transfer"]
LOCATIONS = ["Mumbai, India", "New York, USA", "London, UK", "Tokyo, Japan", "Berlin, Germany"]

def generate_mock_transaction():
    """Generates a highly realistic, randomized transaction payload."""
    # SDE Rule: Simulate a realistic mix of normal traffic and anomalous traffic
    is_anomaly = random.random() < 0.05  # 5% chance of generating a weird transaction
    
    if is_anomaly:
        # High amounts or rapid sequences signify an anomaly
        amount = round(random.uniform(5000.0, 25000.0), 2)
    else:
        amount = round(random.uniform(5.0, 800.0), 2)
        
    payload = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": f"USR_{random.randint(1000, 1050)}", # Narrow range to trigger sliding-window alerts easily
        "amount": amount,
        "currency": "USD",
        "merchant_type": random.choice(MERCHANT_TYPES),
        "location": random.choice(LOCATIONS),
        "timestamp": datetime.utcnow().isoformat()
    }
    return payload

def start_stream():
    print(f"FinGuard Stream Generator started. Pushing data to Redis Stream: '{STREAM_NAME}'...")
    print("Press Ctrl+C to terminate.")
    
    try:
        while True:
            tx_data = generate_mock_transaction()
            
            # SDE Masterstroke: Push the dictionary as a flattened JSON string into the Redis Stream
            redis_client.xadd(STREAM_NAME, {"payload": json.dumps(tx_data)})
            
            print(f"[STREAMED] ID: {tx_data['transaction_id']} | User: {tx_data['user_id']} | ${tx_data['amount']}")
            
            # Generate a new transaction every 0.5 to 1.5 seconds to simulate variable real-world load
            time.sleep(random.uniform(0.5, 1.5))
            
    except KeyboardInterrupt:
        print("\n Stream Generator stopped safely.")

if __name__ == "__main__":
    start_stream()