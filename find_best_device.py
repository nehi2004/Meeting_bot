import sounddevice as sd
import numpy as np
import time

print("YouTube video chalao Chrome mein ABHI!")
print("Sab input devices test kar raha hai...\n")
time.sleep(3)

devices = sd.query_devices()
results = []

for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        try:
            recording = sd.rec(
                int(2 * 16000),
                samplerate=16000,
                channels=1,
                dtype='int16',
                device=i
            )
            sd.wait()
            volume = np.abs(recording).mean()
            results.append((volume, i, device['name']))
            print(f"[{i:2d}] Vol={volume:6.1f} | {device['name'][:45]}")
        except Exception as e:
            print(f"[{i:2d}] SKIP | {device['name'][:40]} ({str(e)[:30]})")

print("\n" + "="*55)
print("BEST DEVICES (volume ke hisaab se):")
results.sort(reverse=True)
for vol, idx, name in results[:5]:
    print(f"  [{idx:2d}] Volume={vol:.1f} | {name}")

if results and results[0][0] > 10:
    best_id = results[0][1]
    print(f"\nBEST DEVICE: [{best_id}] use karo!")
    print(f"phase2_bot.py mein device_id = {best_id} set karo")
else:
    print("\nKoi bhi device audio capture nahi kar pa raha!")
    print("YouTube video zaroor chala ke rakho test ke dauran")