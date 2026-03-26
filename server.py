import asyncio
import os
import websockets

# Store connected clients
connected_clients = set()

async def audio_server(websocket, path):
    print("🟢 New Client Connected!")
    connected_clients.add(websocket)
    try:
        # Continuously listen for messages
        async for message in websocket:
            # 'message' comes in as raw bytes. 
            # We blindly broadcast it to everyone else.
            for client in connected_clients:
                if client != websocket:
                    await client.send(message)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        connected_clients.remove(websocket)
        print("🔴 Client Disconnected")

async def main():
    # Railway provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Server listening on port {port}")
    async with websockets.serve(audio_server, "0.0.0.0", port):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
