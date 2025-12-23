from flask import Flask, render_template, request, jsonify, Response
import RPi.GPIO as GPIO
import math
from mpu6050 import mpu6050
import serial
import pynmea2
from picamera2 import Picamera2
import cv2
import time

app = Flask(__name__)

# ------------------- GPIO Setup -------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

current_mode = "manual"  # for camera feed
current_servo_angle = 0  # Default: camera facing forward


# ------------------- Motor Configuration -------------------
MOTORS = {
    'back_left':   {'in1': 16, 'in2': 20, 'pwm': 21},
    'back_right':  {'in1': 13, 'in2': 19, 'pwm': 26},
    'front_left':  {'in1': 5,  'in2': 6,  'pwm': 12},
    'front_right': {'in1': 11, 'in2': 8,  'pwm': 9},
}

pwm_objs     = {}
motor_speeds = {m: 80 for m in MOTORS}

for m, pins in MOTORS.items():
    GPIO.setup(pins['in1'], GPIO.OUT)
    GPIO.setup(pins['in2'], GPIO.OUT)
    GPIO.setup(pins['pwm'], GPIO.OUT)
    pwm = GPIO.PWM(pins['pwm'], 100)
    pwm.start(0)
    pwm_objs[m] = pwm

def set_motor(motor, direction):
    pins = MOTORS[motor]
    speed = motor_speeds[motor]
    if   direction == 'forward':
        GPIO.output(pins['in1'], GPIO.HIGH)
        GPIO.output(pins['in2'], GPIO.LOW)
    elif direction == 'backward':
        GPIO.output(pins['in1'], GPIO.LOW)
        GPIO.output(pins['in2'], GPIO.HIGH)
    else:  # stop
        GPIO.output(pins['in1'], GPIO.LOW)
        GPIO.output(pins['in2'], GPIO.LOW)
        speed = 0
    pwm_objs[motor].ChangeDutyCycle(speed)

# ------------------- Encoder Setup -------------------
encoders = {
    'back_left':   {'A': 4,  'B': 10},
    'back_right':  {'A': 17, 'B': 27},
    'front_left':  {'A': 22, 'B': 23},
    'front_right': {'A': 24, 'B': 25},
}

encoder_counts = {k: 0 for k in encoders}

def make_callback(motor):
    def callback(channel):
        encoder_counts[motor] += 1
    return callback

for m, pins in encoders.items():
    GPIO.setup(pins['A'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(pins['B'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(pins['A'], GPIO.RISING, callback=make_callback(m), bouncetime=20)

#-------------------servo motor----------------------------
SERVO_PIN = 18
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)
servo_pwm.start(0)

def set_servo_angle(angle):
    global current_servo_angle
    current_servo_angle = angle

    # Map angle from -90 to +90 to a duty cycle of 2.5 to 12.5
    angle = max(-90, min(90, angle))  # clamp to valid logical range
    duty = 7.5 + (angle / 18.0)  # 0° = 7.5%, ±90° = ±5% → ~2.5% to 12.5%
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(0)


# ------------------ Initialize Sensors -------------------
mpu_sensor = mpu6050(0x68)
gps_serial = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)

def read_mpu6050_data():
    accel = mpu_sensor.get_accel_data()
    gyro  = mpu_sensor.get_gyro_data()
    return {
        'accelX': round(accel['x'], 2),
        'accelY': round(accel['y'], 2),
        'accelZ': round(accel['z'], 2),
        'gyroX':  round(gyro['x'], 2),
        'gyroY':  round(gyro['y'], 2),
        'gyroZ':  round(gyro['z'], 2),
    }

def read_gps_data():
    try:
        while gps_serial.in_waiting:
            line = gps_serial.readline().decode('ascii', errors='replace')
            if line.startswith('$GPGGA'):
                msg = pynmea2.parse(line)
                return {
                    'latitude':  round(msg.latitude, 6),
                    'longitude': round(msg.longitude, 6)
                }
    except Exception:
        pass
    return {'latitude': 0.0, 'longitude': 0.0}

# ------------------- Picamera2 Setup -------------------
picam2        = Picamera2()
sensor_cfg    = picam2.sensor_modes[0]  # full-res
preview_cfg   = picam2.create_preview_configuration(
    main={"format": "YUV420", "size": sensor_cfg["size"]}
)
picam2.configure(preview_cfg)
picam2.start()
time.sleep(1)  # warm-up

def gen_normal_frames():
    while True:
        yuv = picam2.capture_array("main")
        bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
        ret, jpg = cv2.imencode('.jpg', bgr)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg.tobytes() + b'\r\n')
        
def gen_autonomous_frames():
    frame_num = 0
    while True:
        yuv = picam2.capture_array("main")
        frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
        frame_num += 1
        frame_copy = frame.copy()

        if current_servo_angle == 0:
            # === ROW DETECTION ONLY ===
            row_result = model_row(frame_copy)[0]
            for box in row_result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = row_result.names[int(box.cls[0])]
                cx = (x1 + x2) // 2
                cv2.line(frame_copy, (cx, y1), (cx, y2), (0, 255, 0), 2)
                cv2.putText(frame_copy, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        elif abs(current_servo_angle) == 90:
            # === DISEASE & RIPENESS DETECTION ===
            disease_result = model_disease(frame_copy)[0]
            disease = "none"
            for box in disease_result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                disease = disease_result.names[cls]
                cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame_copy, disease, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            ripeness_result = model_ripeness(frame_copy)[0]
            ripeness_counts = {}
            for box in ripeness_result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                label = ripeness_result.names[cls]
                ripeness_counts[label] = ripeness_counts.get(label, 0) + 1
                cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame_copy, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            # Show summary
            y = 30
            for label, count in ripeness_counts.items():
                cv2.putText(frame_copy, f"{label}: {count}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                y += 25

            if frame_num % 30 == 0:
                gps = read_gps_data()
                log_detection(gps, disease, ripeness_counts)

        # === Stream frame ===
        ret, buffer = cv2.imencode('.jpg', frame_copy)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    if current_mode == "autonomous":
        return Response(gen_autonomous_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return Response(gen_normal_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# -----------------------Autonomous mode---------------------

def autonomous_mode():
    print("🟢 Autonomous mode starting...")

    while True:
        frame = picam2.capture_array("main")
        row_result = model_row(frame)[0]

        if len(row_result.boxes) == 0:
            print("🔍 No plant rows detected. Searching...")
            stop_all_motors()
            continue

        # Compute alignment
        centers = []
        for box in row_result.boxes:
            x1, _, x2, _ = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            centers.append(cx)

        avg_center = int(sum(centers) / len(centers))
        frame_center = frame.shape[1] // 2
        offset = avg_center - frame_center

        # Align to row center
        if abs(offset) > 30:
            if offset < 0:
                set_motor('left', 'forward')
                set_motor('right', 'stop')
                print("↪ Adjusting Left")
            else:
                set_motor('right', 'forward')
                set_motor('left', 'stop')
                print("↩ Adjusting Right")
            time.sleep(0.5)
            stop_all_motors()
            continue

        # Move forward
        print("⬆ Moving Forward...")
        set_motor('left', 'forward')
        set_motor('right', 'forward')
        time.sleep(0.5)
        stop_all_motors()

        # Check if close to plant
        if any((box.xyxy[0][3] - box.xyxy[0][1]) > frame.shape[0] * 0.5 for box in row_result.boxes):
            print("🛑 Close to plant. Stopping...")
            stop_all_motors()

            # Servo scan
            for angle in [90, -90]:
                set_servo_angle(angle)
                time.sleep(1.5)  # give time for camera to rotate and detect
            set_servo_angle(0)
            print("✅ Detection complete. Moving to next plant...")


# ------------------- Flask Routes -------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def move():
    direction = request.form['direction']
    if direction != 'stop':
        for k in encoder_counts:
            encoder_counts[k] = 0
    if direction == 'forward':
        for m in MOTORS: set_motor(m, 'forward')
    elif direction == 'backward':
        for m in MOTORS: set_motor(m, 'backward')
    elif direction == 'left':
        set_motor('front_left',  'backward')
        set_motor('back_left',   'backward')
        set_motor('front_right', 'forward')
        set_motor('back_right',  'forward')
    elif direction == 'right':
        set_motor('front_left',  'forward')
        set_motor('back_left',   'forward')
        set_motor('front_right', 'backward')
        set_motor('back_right',  'backward')
    else:
        for m in MOTORS: set_motor(m, 'stop')
    return '', 204

@app.route('/set_speed', methods=['POST'])
def set_speed():
    motor = request.form['motor']; speed = int(request.form['speed'])
    if motor in motor_speeds:
        motor_speeds[motor] = speed
    return '', 204

@app.route('/sensor_data')
def sensor_data():
    encoder_data = {
        m: {
            'counts':     encoder_counts[m],
            'distance_cm': round(encoder_counts[m] * DISTANCE_PER_PULSE_CM, 2)
        } for m in encoder_counts
    }
    return jsonify({
        'encoder': encoder_data,
        'mpu6050': read_mpu6050_data(),
        'gps':     read_gps_data()
    })

@app.route('/reset_encoder', methods=['POST'])
def reset_encoder():
    for k in encoder_counts: encoder_counts[k] = 0
    return '', 204

@app.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    for m in MOTORS: set_motor(m, 'stop')
    return '', 204

@app.route('/start_autonomous', methods=['POST'])
def start_autonomous():
    import threading
    threading.Thread(target=autonomous_mode).start()
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
