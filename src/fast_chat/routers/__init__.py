from fastapi import APIRouter

from fast_chat.routers.pages import pages_router
from fast_chat.routers.v1 import v1_router

api_router = APIRouter(prefix="")

api_router.include_router(v1_router)
api_router.include_router(pages_router)
