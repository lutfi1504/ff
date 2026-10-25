"""Find when the burned-in caption changes, from a 10 fps crop of the caption band."""
import subprocess, sys, json
import numpy as np

src, out = sys.argv[1], sys.argv[2]
W, H, Y0, FPS = 1080, 140, 1290, 10
raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS},crop={W}:{H}:0:{Y0},format=gray",
     "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
# Caption text is pure white; mask it so footage behind it doesn't count as a change.
masks = frames > 235
ink = masks.reshape(len(masks), -1).sum(1)
segs, start = [], 0
for i in range(1, len(masks) + 1):
    if i == len(masks) or (masks[i] ^ masks[i - 1]).sum() > 600:
        if ink[start:i].mean() > 300:
            segs.append({"start": round(start / FPS, 2), "end": round(i / FPS, 2), "mid": (start + i) // 2})
        start = i
json.dump(segs, open(out, "w"), indent=1)
print(len(segs), "segments")
