import threading
import time
import random

# Mock Libraries if not on Pi
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

try:
    from mpu6050 import mpu6050
    MPU_AVAILABLE = True
except ImportError:
    MPU_AVAILABLE = False

try:
    import serial
    import pynmea2
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False


class Sensors:
    def __init__(self):
        self._setup_encoders()
        self._setup_mpu()
        self._setup_gps()

    # ---------------- ENCODERS ----------------
    def _setup_encoders(self):
        self.ENCODERS = {
            'back_left':   {'A': 4,  'B': 10},
            'back_right':  {'A': 17, 'B': 27},
            'front_left':  {'A': 22, 'B': 23},
            'front_right': {'A': 24, 'B': 25},
        }
        self.encoder_counts = {k: 0 for k in self.ENCODERS}
        self.DISTANCE_PER_PULSE_CM = 0.5 # Example calibration value
        
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            for m, pins in self.ENCODERS.items():
                GPIO.setup(pins['A'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(pins['B'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pins['A'], GPIO.RISING, callback=self._make_callback(m), bouncetime=20)

    def _make_callback(self, motor):
        def callback(channel):
            self.encoder_counts[motor] += 1
        return callback

    def get_encoder_data(self):
        if not GPIO_AVAILABLE:
            # Mock Data: increment slightly to show movement if we were moving
            for k in self.encoder_counts:
                self.encoder_counts[k] += random.randint(0, 5)

        return {
            m: {
                'counts':     self.encoder_counts[m],
                'distance_cm': round(self.encoder_counts[m] * self.DISTANCE_PER_PULSE_CM, 2)
            } for m in self.encoder_counts
        }

    def reset_encoders(self):
        for k in self.encoder_counts:
            self.encoder_counts[k] = 0

    # ---------------- MPU6050 ----------------
    def _setup_mpu(self):
        self.mpu = None
        if MPU_AVAILABLE and GPIO_AVAILABLE: # I2C usually needs GPIO lib context or specific setup on Pi
            try:
                self.mpu = mpu6050(0x68)
            except Exception as e:
                print(f"MPU6050 Init Failed: {e}")

    def get_mpu_data(self):
        if self.mpu:
            try:
                accel = self.mpu.get_accel_data()
                gyro  = self.mpu.get_gyro_data()
                return {
                    'accelX': round(accel['x'], 2), 'accelY': round(accel['y'], 2), 'accelZ': round(accel['z'], 2),
                    'gyroX':  round(gyro['x'], 2),  'gyroY':  round(gyro['y'], 2),  'gyroZ':  round(gyro['z'], 2),
                }
            except:
                pass
        
        # Mock Data
        return {
            'accelX': round(random.uniform(-1, 1), 2),
            'accelY': round(random.uniform(-1, 1), 2),
            'accelZ': round(random.uniform(9, 10), 2), # Gravity
            'gyroX':  round(random.uniform(-5, 5), 2),
            'gyroY':  round(random.uniform(-5, 5), 2),
            'gyroZ':  round(random.uniform(-5, 5), 2),
        }

    # ---------------- GPS ----------------
    def _setup_gps(self):
        self.gps_serial = None
        if GPS_AVAILABLE:
            try:
                self.gps_serial = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)
            except Exception as e:
                print(f"GPS Init Failed: {e}")

    def get_gps_data(self):
        if self.gps_serial:
            try:
                # Read all waiting bytes to get latest
                while self.gps_serial.in_waiting:
                    line = self.gps_serial.readline().decode('ascii', errors='replace')
                    if line.startswith('$GPGGA'):
                        msg = pynmea2.parse(line)
                        return {
                            'latitude':  round(msg.latitude, 6),
                            'longitude': round(msg.longitude, 6)
                        }
            except Exception:
                pass
                
        # Mock Data (Somewhere in New York for fun, or user location)
        return {
            'latitude':  40.7128 + random.uniform(-0.0001, 0.0001),
            'longitude': -74.0060 + random.uniform(-0.0001, 0.0001)
        }
