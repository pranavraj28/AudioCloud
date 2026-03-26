import asyncio
import os
from aiohttp import web
import aiohttp

connected_clients = set()

# ── WebSocket Handler ─────────────────────────────────────────────
async def websocket_handler(request):
    ws = web.WebSocketResponse(
        heartbeat=20,
        max_msg_size=2*1024*1024
    )
    await ws.prepare(request)

    connected_clients.add(ws)
    print(f"🟢 WS Connected! Total: {len(connected_clients)}", flush=True)

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                others = [c for c in connected_clients if c is not ws]
                if others:
                    await asyncio.gather(
                        *[c.send_bytes(msg.data) for c in others],
                        return_exceptions=True
                    )
            elif msg.type == aiohttp.WSMsgType.TEXT:
                others = [c for c in connected_clients if c is not ws]
                if others:
                    await asyncio.gather(
                        *[c.send_str(msg.data) for c in others],
                        return_exceptions=True
                    )
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
    except Exception as e:
        print(f"💥 WS Error: {e}", flush=True)
    finally:
        connected_clients.discard(ws)
        print(f"👥 Remaining clients: {len(connected_clients)}", flush=True)

    return ws

# ── HTTP Health Check (stops Railway from killing the container) ──
async def health(request):
    return web.Response(
        text=f"AudioCloud OK — {len(connected_clients)} client(s) connected",
        status=200
    )

# ── App Setup ─────────────────────────────────────────────────────
def make_app():
    app = web.Application()
    app.router.add_get("/",       health)
    app.router.add_get("/health", health)
    app.router.add_get("/ws",     websocket_handler)
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting AudioCloud on port {port}", flush=True)
    web.run_app(make_app(), host="0.0.0.0", port=port)
