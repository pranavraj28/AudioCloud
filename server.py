import asyncio
import os
import websockets

# Keep track of everyone connected (Sender and Receivers)
connected_clients = set()

# FIX: New websockets library (>=10.0) uses single argument — no "path" parameter
async def audio_broker(websocket):
    connected_clients.add(websocket)
    print(f"🟢 Device connected! Total devices: {len(connected_clients)}", flush=True)

    try:
        async for message in websocket:
            # Broadcast this exact audio packet to all OTHER connected devices
            if connected_clients:
                others = [c for c in connected_clients if c != websocket]
                if others:
                    await asyncio.gather(
                        *[client.send(message) for client in others],
                        return_exceptions=True  # don't crash if one client drops mid-send
                    )
    except websockets.exceptions.ConnectionClosedOK:
        print("🔴 Device disconnected cleanly.", flush=True)
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"🔴 Device disconnected with error: {e}", flush=True)
    except Exception as e:
        print(f"💥 Unexpected error: {e}", flush=True)
    finally:
        connected_clients.discard(websocket)  # discard is safe even if already removed
        print(f"👥 Remaining devices: {len(connected_clients)}", flush=True)

async def main():
    port = int(os.environ.get("PORT", 8765))

    print(f"🚀 Cloud Audio Server starting on port {port}", flush=True)

    async with websockets.serve(
        audio_broker,
        "0.0.0.0",
        port,
        ping_interval=20,       # keep Railway from closing idle connections
        ping_timeout=10,
        max_size=2 * 1024 * 1024  # 2MB max message size
    ):
        print(f"✅ Server listening on port {port}", flush=True)
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
