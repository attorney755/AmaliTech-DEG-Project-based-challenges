from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
import asyncio
import hashlib
import json
from .models import PaymentRequest, PaymentResponse, ErrorResponse
from .storage.memory_storage import MemoryStorage
from .utils.logger import logger

# I set up the FastAPI app here to act as an idempotency gateway for payments.
# This ensures users can't accidentally double-charge by retrying the same request.
app = FastAPI(title="Idempotency Gateway", description="Pay Once Protocol")

# I use MemoryStorage to temporarily store payment requests and their responses.
# This helps me check if a request with the same idempotency key has already been processed.
storage = MemoryStorage()

def get_request_hash(payment: PaymentRequest) -> str:
    # I create a unique hash for each payment request based on its amount and currency.
    # This way, I can detect if someone tries to reuse an idempotency key with a different request.
    request_data = {
        "amount": payment.amount,
        "currency": payment.currency
    }
    request_string = json.dumps(request_data, sort_keys=True)
    return hashlib.sha256(request_string.encode()).hexdigest()

def simulate_payment_processing(amount: float, currency: str) -> dict:
    # I simulate a real payment process here with a 2-second delay.
    # In a real app, this would call a payment provider like Stripe or PayPal.
    import time
    time.sleep(2)

    return {
        "status": "success",
        "message": f"Charged {amount} {currency}",
        "transaction_id": str(uuid.uuid4()),
        "amount": amount,
        "currency": currency
    }

@app.get("/")
def root():
    # A simple endpoint to check if the gateway is running.
    return {"message": "Idempotency Gateway Running"}

@app.get("/metrics")
def get_metrics():
    # I track how well the idempotency system is working by calculating the cache hit ratio.
    # A high ratio means most retries are safely handled without reprocessing.
    stats = logger.get_stats()

    # I calculate the percentage of requests that hit the cache (no reprocessing needed).
    total_processed = stats["cache_hits"] + stats["cache_misses"]
    cache_hit_ratio = stats["cache_hits"] / total_processed if total_processed > 0 else 0

    return {
        "statistics": stats,
        "cache_hit_ratio": f"{cache_hit_ratio * 100:.2f}%",
        "status": "healthy",
        "uptime_seconds": 0  # In production, I'd track actual uptime here.
    }

@app.post("/process-payment",
          response_model=PaymentResponse,
          responses={
              409: {"model": ErrorResponse, "description": "Idempotency key already used for different request"}
          })
async def process_payment(
    payment: PaymentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    # First, I check if the user provided an idempotency key in the headers.
    # Without it, I can't guarantee they won't be double-charged.
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required"
        )

    # I create a hash of the current request to compare it with any stored requests.
    current_request_hash = get_request_hash(payment)

    # I check if this idempotency key has been used before.
    cached_response = await storage.get(idempotency_key)
    stored_hash = await storage.get_request_hash(idempotency_key)

    if cached_response and stored_hash:
        # If the stored request doesn't match the current one, I reject it.
        # This prevents users from reusing an idempotency key for a different payment.
        if stored_hash != current_request_hash:
            logger.log_conflict(idempotency_key, {"hash": stored_hash}, {"hash": current_request_hash})

            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Conflict",
                    "message": "Idempotency key already used for a different request body",
                    "idempotency_key": idempotency_key
                }
            )

        # If the requests match, I return the cached response.
        # This means the user is safely retrying the same payment.
        logger.log_cache_hit(idempotency_key)
        logger.log_request(idempotency_key, payment.dict(), "hit")

        response = PaymentResponse(**cached_response)
        return JSONResponse(
            content=response.dict(),
            status_code=200,
            headers={"X-Cache-Hit": "true"}
        )

    # I use a lock to prevent race conditions.
    # This ensures only one thread processes a payment with the same idempotency key at a time.
    lock = await storage.get_lock(idempotency_key)

    # I double-check the cache inside the lock to handle concurrent requests safely.
    async with lock:
        cached_response = await storage.get(idempotency_key)
        stored_hash = await storage.get_request_hash(idempotency_key)

        if cached_response and stored_hash:
            if stored_hash != current_request_hash:
                logger.log_conflict(idempotency_key, {"hash": stored_hash}, {"hash": current_request_hash})
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "Conflict",
                        "message": "Idempotency key already used for a different request body",
                        "idempotency_key": idempotency_key
                    }
                )

            logger.log_cache_hit(idempotency_key)
            logger.log_request(idempotency_key, payment.dict(), "hit")

            response = PaymentResponse(**cached_response)
            return JSONResponse(
                content=response.dict(),
                status_code=200,
                headers={"X-Cache-Hit": "true"}
            )

        # If this is a new request, I process the payment and store the result.
        logger.log_cache_miss(idempotency_key)
        logger.log_request(idempotency_key, payment.dict(), "miss")

        result = simulate_payment_processing(payment.amount, payment.currency)
        await storage.set(idempotency_key, result, current_request_hash)

        response = PaymentResponse(**result)
        return JSONResponse(
            content=response.dict(),
            status_code=200,
            headers={"X-Cache-Hit": "false"}
        )
