from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.operations import router as operations_router

router = APIRouter()
router.include_router(operations_router)
router.include_router(chat_router)
