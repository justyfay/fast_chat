from fastapi import APIRouter

from src.fast_chat.routers.v1.auth import auth_router
from src.fast_chat.routers.v1.messages import msg_router
from src.fast_chat.routers.v1.users import user_router
from src.fast_chat.routers.v1.ws import ws_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(auth_router)
v1_router.include_router(msg_router)
v1_router.include_router(user_router)
v1_router.include_router(ws_router)
