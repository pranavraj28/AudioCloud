import asyncio
import os
import struct
import time
import websockets

connected_clients = {}   # "SENDER" / "RECEIVER" / "RECEIVER_2" etc.
pending_alarms    = []   # list of { audio, trigger_time, acked }

def log(msg):
    print(msg, flush=True)

async def replay_alarm(alarm, ws):
    """Send a stored alarm to a specific receiver."""
    header = b"REPL"
    await ws.send(header + alarm["audio"])

async def alarm_scheduler():
    """Background task — checks every second if any alarm is due."""
    while True:
        now = time.time()
        for alarm in pending_alarms:
            if alarm["acked"]:
                continue
            if now >= alarm["trigger_time"]:
                receivers = [ws for role, ws in connected_clients.items()
                             if role.startswith("RECEIVER")]
                if receivers:
                    log(f"🔔 Triggering alarm to {len(receivers)} receiver(s)")
                    for ws in receivers:
                        try:
                            await ws.send(b"ALRM" + alarm["audio"])
                        except Exception as e:
                            log(f"⚠️ Send failed: {e}")
                    # Reschedule replay in 30s if not acked
                    alarm["trigger_time"] = now + 30
                else:
                    log("⏳ Alarm due but no receivers connected — will retry")
                    alarm["trigger_time"] = now + 10
        await asyncio.sleep(1)

async def audio_handler(websocket):
    role = None
    try:
        # First message identifies the client
        ident = await asyncio.wait_for(websocket.recv(), timeout=10)
        if isinstance(ident, str):
            # Assign unique role key for multiple receivers
            base = ident.strip()
            role = base
            count = 1
            while role in connected_clients:
                count += 1
                role = f"{base}_{count}"
            connected_clients[role] = websocket
            log(f"🟢 {role} connected | Total: {len(connected_clients)}")

            # If receiver connects while alarm is pending, replay it
            if role.startswith("RECEIVER"):
                for alarm in pending_alarms:
                    if not alarm["acked"]:
                        log(f"📤 Replaying pending alarm to new {role}")
                        try:
                            await websocket.send(b"ALRM" + alarm["audio"])
                        except Exception as e:
                            log(f"⚠️ Replay failed: {e}")

        async for message in websocket:

            # ── BINARY from SENDER: first 4 bytes = delay (uint32), rest = audio ──
            if isinstance(message, bytes) and role and role.startswith("SENDER"):
                if len(message) > 4:
                    delay_sec = struct.unpack('<I', message[:4])[0]
                    audio     = message[4:]
                    trigger   = time.time() + delay_sec
                    pending_alarms.append({
                        "audio":        audio,
                        "trigger_time": trigger,
                        "acked":        False
                    })
                    log(f"📥 Alarm stored! {len(audio)} bytes audio, "
                        f"triggers in {delay_sec}s at {time.strftime('%H:%M:%S', time.localtime(trigger))}")

            # ── TEXT from RECEIVER: ACK to dismiss alarm ──
            elif isinstance(message, str) and message.strip() == "ACK":
                log(f"✅ ACK received from {role} — dismissing alarm")
                for alarm in pending_alarms:
                    if not alarm["acked"]:
                        alarm["acked"] = True
                        break
                try:
                    await websocket.send("ALARM_ACK_OK")
                except:
                    pass

    except asyncio.TimeoutError:
        log("❌ Client didn't identify in time")
    except websockets.exceptions.ConnectionClosedOK:
        log(f"🔴 {role} disconnected cleanly")
    except websockets.exceptions.ConnectionClosedError as e:
        log(f"🔴 {role} disconnected: {e}")
    except Exception as e:
        log(f"💥 Error from {role}: {e}")
    finally:
        if role and role in connected_clients:
            del connected_clients[role]
        log(f"👥 Remaining: {len(connected_clients)}")

async def main():
    port = int(os.environ.get("PORT", 8765))
    log(f"🚀 Alarm Server starting on port {port}")
    async with websockets.serve(
        audio_handler, "0.0.0.0", port,
        ping_interval=20, ping_timeout=10,
        max_size=5 * 1024 * 1024
    ):
        log(f"✅ Listening on port {port}")
        asyncio.create_task(alarm_scheduler())
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
