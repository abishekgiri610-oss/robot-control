import os
from flask import Flask, render_template, Response, request, jsonify

# Import Hardware Controllers (or Mocks)
from camera import VideoCamera
from motor_control import MotorController
from servo_control import ServoController
from sensors import Sensors

app = Flask(__name__)

# Initialize Hardware
camera = VideoCamera()
motors = MotorController()
servo = ServoController()
sensors = Sensors()

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            break

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control_motor', methods=['POST'])
def control_motor():
    """
    Control motor movement.
    Expected JSON: {'direction': 'forward'|'backward'|'left'|'right'|'stop', 'speed': 0-100}
    """
    data = request.json
    direction = data.get('direction', 'stop')
    speed = data.get('speed', 50) # Default speed
    
    motors.move(direction, speed)
    return jsonify({'status': 'success', 'direction': direction, 'speed': speed})

@app.route('/control_servo', methods=['POST'])
def control_servo():
    """
    Control servo angle (Pan).
    Expected JSON: {'angle': 0-180}
    """
    data = request.json
    angle = data.get('angle', 90) # Default center
    
    servo.set_angle(float(angle))
    return jsonify({'status': 'success', 'angle': angle})

@app.route('/telemetry')
def telemetry():
    """
    Fetch all sensor data.
    """
    return jsonify({
        'gps': sensors.get_gps_data(),
        'mpu': sensors.get_mpu_data(),
        'encoders': sensors.get_encoder_data()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
