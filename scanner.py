"""
scanner.py — standalone QR scanner launched as a subprocess by app.py.
Runs completely independently, scans ONE QR code, prints it to stdout, exits.
Because it is a separate process the OS fully releases the camera on exit,
so app.py can open it again immediately for the next scan.
"""
import cv2
from pyzbar.pyzbar import decode
import sys

cap = None
for idx in range(10):
    c = cv2.VideoCapture(idx)
    if c.isOpened():
        ok, _ = c.read()
        if ok:
            cap = c
            break
        c.release()
    else:
        c.release()

if cap is None:
    print("ERROR: could not open webcam", file=sys.stderr)
    sys.exit(1)

scanned = None
while True:
    ret, frame = cap.read()
    if not ret:
        break
    for obj in decode(frame):
        scanned = obj.data.decode("utf-8")
        cv2.putText(frame, scanned, (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 80), 2)
    cv2.imshow("QR Scanner  —  point at box  [q = quit]", frame)
    if scanned or (cv2.waitKey(1) & 0xFF == ord('q')):
        break

cap.release()
cv2.destroyAllWindows()

if scanned:
    print(scanned.strip())
    sys.exit(0)
else:
    sys.exit(2)
