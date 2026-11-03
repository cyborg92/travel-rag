from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Travel Assistant API",
    description="A learning project for a travel knowledge assistant powered by RAG.",
    version="0.1.0",
)

app.include_router(router)
