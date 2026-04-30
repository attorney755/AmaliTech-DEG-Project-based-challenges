from fastapi import FastAPI

app = FastAPI(title="Idempotency Gateway", description="Pay Once Protocol")

@app.get("/")
def root():
    return {"message": "Idempotency Gateway Running"}

@app.post("/process-payment")
def process_payment():
    return {"message": "Payment endpoint ready"}