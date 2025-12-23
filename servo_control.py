import time

# Mock RPi.GPIO if not on Raspberry Pi
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

if not GPIO_AVAILABLE:
    # Re-define MockGPIO here if imported in isolation, 
    # but practically we trust it handles itself or we duplicate the mock class if needed.
    # For simplicity, we'll assume the same check or just use a dummy class if user runs this file directly.
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state): pass
        @staticmethod
        def cleanup(): pass
        class PWM:
            def __init__(self, pin, freq): pass
            def start(self, dc): pass
            def ChangeDutyCycle(self, dc): pass
            def stop(self): pass
    GPIO = MockGPIO()

class ServoController:
    def __init__(self):
        # Pin Configuration
        self.SERVO_PIN = 18
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        
        # 50Hz PWM frequency is standard for servos
        self.pwm = GPIO.PWM(self.SERVO_PIN, 50)
        self.pwm.start(0)
        self.current_angle = 90
        # Initialize at center
        self.set_angle(90)

    def set_angle(self, angle):
        """
        Sets servo angle. Input 0-180.
        Internally maps to -90 to +90 for hardware.
        """
        print(f"Servo Moving to Angle: {angle}")
        self.current_angle = angle
        
        # Map 0-180 to -90 to 90
        hw_angle = angle - 90
        hw_angle = max(-90, min(90, hw_angle))
        
        # User's Formula: duty = 7.5 + (angle / 18.0)
        duty = 7.5 + (hw_angle / 18.0)
        
        GPIO.output(self.SERVO_PIN, True)
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.3) # Wait for it to move
        self.pwm.ChangeDutyCycle(0) # Stop sending signal to prevent jitter
        GPIO.output(self.SERVO_PIN, False)

    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup()
