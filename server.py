import asyncio
import os
import websockets

connected_clients = set()

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
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"🔴 Connection closed with error: {e}", flush=True)
    except Exception as e:
        print(f"💥 Error: {e}", flush=True)
    finally:
        connected_clients.discard(websocket)
        print(f"👥 Remaining: {len(connected_clients)}", flush=True)

async def main():
    # Railway injects PORT as an environment variable — MUST bind to it
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting on port {port}", flush=True)

    async with websockets.serve(
        audio_broker,
        "0.0.0.0",
        port,
        ping_interval=20,
        ping_timeout=10,
        max_size=2 * 1024 * 1024,   # 2MB max message
        close_timeout=10,
    ):
        print(f"✅ Listening on port {port}", flush=True)
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
