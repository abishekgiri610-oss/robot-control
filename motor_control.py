import sys

# Mock RPi.GPIO if not on Raspberry Pi
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("RPi.GPIO not found. Using Mock GPIO.")

class MockGPIO:
    BCM = "BCM"
    OUT = "OUT"
    HIGH = "HIGH"
    LOW = "LOW"
    
    @staticmethod
    def setmode(mode):
        pass
    
    @staticmethod
    def setup(pin, mode):
        pass
    
    @staticmethod
    def output(pin, state):
        pass
    
    @staticmethod
    def cleanup():
        pass
    
    class PWM:
        def __init__(self, pin, freq):
            self.pin = pin
            self.freq = freq
        def start(self, duty_cycle):
            pass
        def ChangeDutyCycle(self, duty_cycle):
            pass
        def stop(self):
            pass

if not GPIO_AVAILABLE:
    GPIO = MockGPIO()

class MotorController:
    def __init__(self):
        # 4-Motor Configuration (BCM)
        self.MOTORS = {
            'back_left':   {'in1': 16, 'in2': 20, 'pwm': 21},
            'back_right':  {'in1': 13, 'in2': 19, 'pwm': 26},
            'front_left':  {'in1': 5,  'in2': 6,  'pwm': 12},
            'front_right': {'in1': 11, 'in2': 8,  'pwm': 9},
        }
        
        GPIO.setmode(GPIO.BCM)
        self.pwm_objs = {}
        
        for name, pins in self.MOTORS.items():
            GPIO.setup(pins['in1'], GPIO.OUT)
            GPIO.setup(pins['in2'], GPIO.OUT)
            GPIO.setup(pins['pwm'], GPIO.OUT)
            
            pwm = GPIO.PWM(pins['pwm'], 100) # 100Hz
            pwm.start(0)
            self.pwm_objs[name] = pwm
            
    def _set_motor(self, motor_name, direction, speed):
        if motor_name not in self.MOTORS:
            return
            
        pins = self.MOTORS[motor_name]
        
        if direction == 'forward':
            GPIO.output(pins['in1'], GPIO.HIGH)
            GPIO.output(pins['in2'], GPIO.LOW)
        elif direction == 'backward':
            GPIO.output(pins['in1'], GPIO.LOW)
            GPIO.output(pins['in2'], GPIO.HIGH)
        else: # stop
            GPIO.output(pins['in1'], GPIO.LOW)
            GPIO.output(pins['in2'], GPIO.LOW)
            speed = 0
            
        self.pwm_objs[motor_name].ChangeDutyCycle(speed)

    def move(self, direction, speed=50):
        """
        Moves the robot in a cardinal direction.
        """
        print(f"Motor Moving: {direction} at Speed: {speed}")
        speed = max(0, min(100, int(speed)))
        
        if direction == 'forward':
            for m in self.MOTORS: self._set_motor(m, 'forward', speed)
            
        elif direction == 'backward':
            for m in self.MOTORS: self._set_motor(m, 'backward', speed)
            
        elif direction == 'left':
            # Rotate Left: Left motors back, Right motors forward
            self._set_motor('front_left', 'backward', speed)
            self._set_motor('back_left', 'backward', speed)
            self._set_motor('front_right', 'forward', speed)
            self._set_motor('back_right', 'forward', speed)
            
        elif direction == 'right':
            # Rotate Right: Left motors forward, Right motors back
            self._set_motor('front_left', 'forward', speed)
            self._set_motor('back_left', 'forward', speed)
            self._set_motor('front_right', 'backward', speed)
            self._set_motor('back_right', 'backward', speed)
            
        elif direction == 'stop':
            for m in self.MOTORS: self._set_motor(m, 'stop', 0)

    def cleanup(self):
        for pwm in self.pwm_objs.values():
            pwm.stop()
        GPIO.cleanup()
