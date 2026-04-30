from fastapi import FastAPI, Header, HTTPException
from typing import Optional
import uuid
import asyncio
from .models import PaymentRequest, PaymentResponse
from .storage.memory_storage import MemoryStorage

app = FastAPI(title="Idempotency Gateway", description="Pay Once Protocol")

# Initialize storage
storage = MemoryStorage()

def simulate_payment_processing(amount: float, currency: str) -> dict:
    """Simulate payment processing with 2-second delay"""
    import time
    time.sleep(2)  # Simulate processing time
    
    return {
        "status": "success",
        "message": f"Charged {amount} {currency}",
        "transaction_id": str(uuid.uuid4()),
        "amount": amount,
        "currency": currency
    }

@app.get("/")
def root():
    return {"message": "Idempotency Gateway Running"}

@app.post("/process-payment", response_model=PaymentResponse)
async def process_payment(
    payment: PaymentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    # Step 1: Validate idempotency key is present
    if not idempotency_key:
        raise HTTPException(
            status_code=400, 
            detail="Idempotency-Key header is required"
        )
    
    # Step 2: Check if we've seen this key before
    cached_response = await storage.get(idempotency_key)
    
    if cached_response:
        # Step 3: Return cached response with cache hit header
        return PaymentResponse(
            **cached_response
        )
    
    # Step 4: Get lock for this key (handles concurrent requests)
    lock = await storage.get_lock(idempotency_key)
    
    # Step 5: Acquire lock (wait if another request is processing)
    async with lock:
        # Double-check cache (in case another request just completed)
        cached_response = await storage.get(idempotency_key)
        if cached_response:
            return PaymentResponse(**cached_response)
        
        # Step 6: Process the payment (with 2-second delay)
        result = simulate_payment_processing(payment.amount, payment.currency)
        
        # Step 7: Store the result
        await storage.set(idempotency_key, result)
        
        # Step 8: Return the result
        return PaymentResponse(**result)