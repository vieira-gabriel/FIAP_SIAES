from fastapi import FastAPI

app = FastAPI()

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {
        "status": "online",
        "message": "Serviço operando normalmente."
    }