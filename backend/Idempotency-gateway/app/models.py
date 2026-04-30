from pydantic import BaseModel, Field
from typing import Optional

# I define the PaymentRequest model here to validate incoming payment data.
# This ensures every payment request has a valid amount and currency.
class PaymentRequest(BaseModel):
    # I require the amount to be a positive number to prevent invalid payments.
    amount: float = Field(..., gt=0, description="Payment amount must be greater than 0")

    # I enforce a 3-letter currency code (like GHS, USD) to standardize payments.
    currency: str = Field(..., min_length=3, max_length=3, description="3-letter currency code like GHS, USD")

    # I include an example in the schema to help users understand the expected format.
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 100.00,
                "currency": "GHS"
            }
        }

# I use PaymentResponse to structure the success response after processing a payment.
# This keeps the API responses consistent and predictable.
class PaymentResponse(BaseModel):
    status: str  # I include the status (e.g., "success") to confirm the payment worked.
    message: str  # I add a human-readable message for clarity.
    transaction_id: str  # I generate a unique ID for each transaction to track it later.
    amount: float  # I include the amount to confirm what was charged.
    currency: str  # I include the currency to confirm the payment details.

# I define ErrorResponse to standardize error messages, especially for idempotency conflicts.
# This helps clients handle errors gracefully.
class ErrorResponse(BaseModel):
    error: str  # I describe the error type (e.g., "Conflict").
    message: str  # I explain what went wrong in plain language.
    idempotency_key: str  # I include the key so users can debug issues.
