import asyncio
import time
import websockets

connected_clients = {}
pending_alarms = []

# Temporary storage per sender
active_recordings = {}

def log(msg):
    print(msg, flush=True)

async def alarm_scheduler():
    while True:
        now = time.time()
        for alarm in pending_alarms:
            if alarm["acked"]:
                continue

            if now >= alarm["trigger_time"]:
                receivers = [ws for role, ws in connected_clients.items()
                             if role.startswith("RECEIVER")]

                if receivers:
                    log("🔔 Sending alarm")
                    for ws in receivers:
                        await ws.send(b"ALRM" + alarm["audio"])
                    alarm["trigger_time"] = now + 30
                else:
                    alarm["trigger_time"] = now + 10

        await asyncio.sleep(1)

async def handler(websocket):
    role = None
    delay = 0

    try:
        ident = await websocket.recv()
        role = ident.strip()
        connected_clients[role] = websocket
        log(f"🟢 {role} connected")

        async for message in websocket:

            # TEXT messages
            if isinstance(message, str):

                if message.startswith("START"):
                    delay = int(message.split(":")[1])
                    active_recordings[websocket] = b""
                    log(f"🎤 Recording started (delay {delay}s)")

                elif message == "STOP":
                    audio = active_recordings.get(websocket, b"")

                    pending_alarms.append({
                        "audio": audio,
                        "trigger_time": time.time() + delay,
                        "acked": False
                    })

                    log(f"📦 Stored alarm ({len(audio)} bytes)")
                    active_recordings[websocket] = b""

                elif message == "ACK":
                    for alarm in pending_alarms:
                        if not alarm["acked"]:
                            alarm["acked"] = True
                            break

            # BINARY (audio streaming)
            elif isinstance(message, bytes):
                if websocket in active_recordings:
                    active_recordings[websocket] += message

    except Exception as e:
        log(f"❌ Error: {e}")

    finally:
        if role in connected_clients:
            del connected_clients[role]
        if websocket in active_recordings:
            del active_recordings[websocket]
        log(f"🔴 {role} disconnected")

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        log("🚀 Server running")
        asyncio.create_task(alarm_scheduler())
        await asyncio.Future()

asyncio.run(main())
