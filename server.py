import asyncio
import os
import websockets
from websockets.server import serve
from websockets.http11 import Request, Response
from websockets.datastructures import Headers

connected_clients = set()

# ── WebSocket Handler ─────────────────────────────────────────────
async def audio_broker(websocket):
    connected_clients.add(websocket)
    print(f"🟢 Connected! Total: {len(connected_clients)}", flush=True)
    try:
        async for message in websocket:
            others = [c for c in connected_clients if c != websocket]
            if others:
                await asyncio.gather(
                    *[c.send(message) for c in others],
                    return_exceptions=True
                )
    except websockets.exceptions.ConnectionClosedOK:
        print("🔴 Disconnected cleanly", flush=True)
    except Exception as e:
        print(f"💥 Error: {e}", flush=True)
    finally:
        connected_clients.discard(websocket)
        print(f"👥 Remaining: {len(connected_clients)}", flush=True)

# ── HTTP health check interceptor ────────────────────────────────
# Called for every incoming request BEFORE the WebSocket handshake.
# If it's a plain HTTP GET (no Upgrade header), return 200 OK immediately.
async def health_check(connection, request):
    upgrade = request.headers.get("Upgrade", "").lower()
    if upgrade != "websocket":
        # Plain HTTP request — return 200 so Railway health check passes
        response = connection.respond(
            http.HTTPStatus.OK,
            "AudioCloud OK\n"
        )
        return response
    # Otherwise let the WebSocket handshake proceed normally
    return None

import http

async def main():
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting AudioCloud on port {port}", flush=True)

    async with websockets.serve(
        audio_broker,
        "0.0.0.0",
        port,
        process_request=health_check,
        ping_interval=20,
        ping_timeout=10,
        max_size=2 * 1024 * 1024,
        close_timeout=10,
    ):
        print(f"✅ Listening on port {port}", flush=True)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
