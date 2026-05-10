# test_mic.py naam se save karo
import sounddevice as sd
import numpy as np

print("Mic test kar raha hai... 3 seconds bolte raho")
recording = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='int16')
sd.wait()
volume = np.abs(recording).mean()
print(f"Volume level: {volume}")
if volume < 10:
    print("MIC KAM KAR RAHA HAI! Volume bahut low hai")
    print("Windows Settings > Sound > Input > apna mic check karo")
else:
    print(f"Mic theek hai! Volume: {volume}")