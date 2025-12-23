// Initialize map
var map = L.map('map').setView([0, 0], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
var roverMarker = L.marker([0, 0]).addTo(map);

// Tab switching
function switchTab(tab) {
  document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active-content'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active-tab'));
  document.getElementById(tab).classList.add('active-content');
  document.getElementById(tab + '-tab').classList.add('active-tab');
}
//servo motor
function rotateServo(angle) {
  fetch('/set_servo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `angle=${angle}`
  }).then(res => {
    if (!res.ok) alert("Servo command failed.");
  });
}
//start
function startAutonomous() {
  fetch('/start_autonomous', { method: 'POST' })
    .then(res => res.ok && alert("Autonomous detection started!"))
    .catch(err => alert("Failed to start: " + err));
}

// Emergency Stop
function emergencyStop() {
  fetch('/emergency_stop', { method: 'POST' })
    .then(res => res.ok && alert("Rover has stopped successfully."))
    .catch(console.error);
}

// Update speed sliders
function updateSpeed(motor, val) {
  document.getElementById(motor + '_val').textContent = val + '%';
  fetch('/set_speed', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: `motor=${motor}&speed=${val}`
  });
}

// Reset encoder data
function resetEncoderData() {
  fetch('/reset_encoder', { method: 'POST' })
    .then(res => res.ok && alert("Encoder data has been reset."))
    .catch(console.error);
}

// Periodically fetch sensor data
setInterval(() => {
  fetch('/sensor_data')
    .then(res => res.json())
    .then(data => {
      // MPU6050
      document.getElementById('mpu6050-data').textContent =
        `Accelerometer: X=${data.mpu6050.accelX} Y=${data.mpu6050.accelY} Z=${data.mpu6050.accelZ} | ` +
        `Gyroscope: X=${data.mpu6050.gyroX} Y=${data.mpu6050.gyroY} Z=${data.mpu6050.gyroZ}`;

      // GPS
      document.getElementById('gps-data').textContent =
        `Latitude: ${data.gps.latitude} | Longitude: ${data.gps.longitude}`;

      // Encoder counts
      const e = data.encoder;
      document.getElementById('encoder-counts').textContent =
        `Front Left: ${e.front_left.counts} (${e.front_left.distance_cm} cm) | ` +
        `Front Right: ${e.front_right.counts} (${e.front_right.distance_cm} cm) | ` +
        `Back Left: ${e.back_left.counts} (${e.back_left.distance_cm} cm) | ` +
        `Back Right: ${e.back_right.counts} (${e.back_right.distance_cm} cm)`;

      // Update map marker and view
      roverMarker.setLatLng([data.gps.latitude, data.gps.longitude]);
      map.setView([data.gps.latitude, data.gps.longitude], 13);
    })
    .catch(console.error);
}, 2000);

// Joystick setup
const joystick = nipplejs.create({
  zone: document.getElementById('joystick-container'),
  mode: 'static',
  position: { left: '50%', top: '50%' },
  color: 'green'
});

let lastCommand = '';

function sendCommand(cmd) {
  if (cmd === lastCommand) return;
  lastCommand = cmd;
  fetch('/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `direction=${cmd}`
  });
}

joystick.on('dir', (evt, data) => {
  if (!data || !data.direction) return;
  let cmd = 'stop';
  switch(data.direction.angle) {
    case 'up': cmd = 'left'; break;
    case 'down': cmd = 'right'; break;
    case 'left': cmd = 'backward'; break;
    case 'right': cmd = 'forward'; break;
  }
  sendCommand(cmd);
});

joystick.on('end', () => sendCommand('stop'));
