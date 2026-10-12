import asyncio

from async_asgi_testclient.websocket import WebSocketSession


async def receive_json(ws: WebSocketSession, timeout: float = 5.0) -> dict:
    """Получение JSON из сокета с таймаутом, чтобы упавший тест не завис навсегда."""
    return await asyncio.wait_for(ws.receive_json(), timeout=timeout)
