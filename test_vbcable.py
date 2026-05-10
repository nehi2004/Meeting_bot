import sounddevice as sd
import numpy as np

devices = sd.query_devices()

# Stereo Mix dhundho
device_id = None
for i, d in enumerate(devices):
    if 'stereo mix' in d['name'].lower() and d['max_input_channels'] > 0:
        device_id = i
        print(f"Stereo Mix mila: [{i}] {d['name']}")
        break

if device_id is None:
    print("Stereo Mix nahi mila! Enable karo pehle.")
else:
    print(f"\n5 seconds sun raha hai device [{device_id}]...")
    print("Koi YouTube video chalao abhi Chrome mein!\n")
    
    recording = sd.rec(
        int(5 * 16000),
        samplerate=16000,
        channels=1,
        dtype='int16',
        device=device_id
    )
    sd.wait()
    
    volume = np.abs(recording).mean()
    print(f"Volume: {volume:.1f}")
    if volume > 10:
        print("PERFECT! Stereo Mix kaam kar raha hai!")
        print("Ab meeting ka audio capture hoga!")
    else:
        print("Abhi bhi blank hai — Stereo Mix ka volume check karo")