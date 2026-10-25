"""Print dips in the speech band (300-3400 Hz) that last >= MIN_GAP seconds."""
import subprocess, sys
import numpy as np

src, MIN_GAP, HOP = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.25, 0.02
sr = 16000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(sr),
                      "-af", "highpass=f=300,lowpass=f=3400", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
n = int(sr * HOP)
rms = np.sqrt(np.mean(x[: len(x) // n * n].reshape(-1, n) ** 2, axis=1))
db = 20 * np.log10(rms + 1e-9)
# Threshold relative to speech level: well below the 70th percentile.
thr = np.percentile(db, 70) - 14
low = db < thr
print(f"speech p70={np.percentile(db,70):.1f} dB, gap threshold={thr:.1f} dB")
i = 0
while i < len(low):
    if low[i]:
        j = i
        while j < len(low) and low[j]:
            j += 1
        if (j - i) * HOP >= MIN_GAP:
            print(f"{i*HOP:6.2f} - {j*HOP:6.2f}  ({(j-i)*HOP:.2f}s)  min {db[i:j].min():.1f} dB")
        i = j
    else:
        i += 1
