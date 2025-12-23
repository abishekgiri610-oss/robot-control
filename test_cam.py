import cv2

print("Testing OpenCV Camera Access...")
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print("SUCCESS: Camera opened!")
    ret, frame = cap.read()
    if ret:
        print(f"Frame captured: {frame.shape}")
        cv2.imwrite("test_frame.jpg", frame)
    else:
        print("ERROR: Could not read frame.")
    cap.release()
else:
    print("FAILURE: Could not open camera index 0.")
