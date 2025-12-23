import time
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("OpenCV not found. Using Mock Camera.")

class VideoCamera(object):
    def __init__(self):
        self.video = None
        self.picam2 = None
        
        # Try Picamera2 first (User's preference)
        try:
            from picamera2 import Picamera2
            self.picam2 = Picamera2()
            sensor_cfg = self.picam2.sensor_modes[0]
            preview_cfg = self.picam2.create_preview_configuration(
                main={"format": "YUV420", "size": sensor_cfg["size"]}
            )
            self.picam2.configure(preview_cfg)
            self.picam2.start()
            print("Using Picamera2")
            return # Exit init if successful
        except ImportError:
            pass
        except Exception as e:
            print(f"Picamera2 Init Failed: {e}")

        # Fallback to OpenCV
        if CV2_AVAILABLE:
            try:
                # If on Windows and suspecting no camera, this might hang or fail.
                # Only try if not explicitly disabled.
                self.video = cv2.VideoCapture(0)
                if not self.video.isOpened():
                    self.video = None
            except Exception as e:
                print(f"OpenCV Init Failed: {e}")
                self.video = None

    def __del__(self):
        if self.video:
            self.video.release()
        # Picamera2 usually stays open or needs explicit stop, handled by OS mostly in this script scope

    def get_frame(self):
        # 1. Picamera2
        if self.picam2:
            try:
                yuv = self.picam2.capture_array("main")
                if CV2_AVAILABLE:
                    bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
                    ret, jpeg = cv2.imencode('.jpg', bgr)
                    return jpeg.tobytes()
            except Exception as e:
                print(f"Picamera2 Error: {e}")
        
        # 2. OpenCV
        if self.video:
            success, image = self.video.read()
            if success:
                ret, jpeg = cv2.imencode('.jpg', image)
                return jpeg.tobytes()
        
        # 3. Mock
        return self.get_mock_frame()

    def get_mock_frame(self):
        # Create a black image
        if CV2_AVAILABLE:
            img = np.zeros((480, 640, 3), np.uint8)
            # Add text
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(img, f'Mock Camera {time.time():.1f}', (50, 240), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            ret, jpeg = cv2.imencode('.jpg', img)
            return jpeg.tobytes()
        else:
            # Return empty bytes if no opencv/numpy
            return b''
