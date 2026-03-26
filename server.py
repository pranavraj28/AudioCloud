import asyncio
import os
import websockets

# Keep track of everyone connected (Sender and Receivers)
connected_clients = set()

async def audio_broker(websocket, path):
    # When a new device connects, add them to the list
    connected_clients.add(websocket)
    print(f"🟢 Device connected! Total devices: {len(connected_clients)}")

    try:
        # Listen continuously for incoming audio packets
        async for message in websocket:
            # Broadcast this exact audio packet to all OTHER connected devices
            for client in connected_clients:
                if client != websocket:
                    await client.send(message)

    except websockets.exceptions.ConnectionClosed:
        print("🔴 Device disconnected.")
    finally:
        # Clean up when a device leaves
        connected_clients.remove(websocket)

async def main():
    # Render will automatically provide a PORT number
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(audio_broker, "0.0.0.0", port):
        print(f"🚀 Cloud Audio Server running on port {port}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
