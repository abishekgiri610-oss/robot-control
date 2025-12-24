import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const RobotApp());
}

class RobotApp extends StatelessWidget {
  const RobotApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Antigravity Robot',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF121212),
        primaryColor: const Color(0xFF00D8FF),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00D8FF),
          secondary: Color(0xFF00D8FF),
          surface: Color(0xFF1E1E1E),
          background: Color(0xFF121212),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: TextStyle(
            fontFamily: 'Courier',
            fontWeight: FontWeight.bold,
            fontSize: 20,
            letterSpacing: 1.5,
            color: Color(0xFF00D8FF),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF1E1E1E).withOpacity(0.8),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: BorderSide.none,
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: const BorderSide(color: Color(0xFF00D8FF), width: 1.5),
          ),
        ),
      ),
      home: const RobotControlScreen(),
    );
  }
}

class RobotControlScreen extends StatefulWidget {
  const RobotControlScreen({super.key});

  @override
  State<RobotControlScreen> createState() => _RobotControlScreenState();
}

class _RobotControlScreenState extends State<RobotControlScreen> {
  late final WebViewController _controller;
  final TextEditingController _ipController = TextEditingController();
  
  String _currentUrl = 'http://192.168.0.100:5000'; 
  bool _isConnected = false;

  // Track last command to avoid duplicate spam
  String _lastCommand = 'stop';
  DateTime _lastRequestTime = DateTime.now();

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.transparent);
  }

  Future<void> _sendCommand(String direction, {int speed = 100}) async {
    // Throttle slightly to prevent network flooding, but allow 'stop' immediately
    if (direction == _lastCommand && direction != 'stop' && DateTime.now().difference(_lastRequestTime).inMilliseconds < 200) {
      return;
    }

    _lastCommand = direction;
    _lastRequestTime = DateTime.now();
    
    // Construct the API URL
    final Uri url = Uri.parse('$_currentUrl/control_motor');
    
    try {
      print("Sending: $direction");
      // Fire and forget (don't await response to keep UI smooth) or await if you want debug
      http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'direction': direction, 'speed': speed}),
      ).catchError((e) => print("Info: Request failed (normal during dev): $e"));
    } catch (e) {
      print("Error sending command: $e");
    }
  }

  void _connect() async {
    String ip = _ipController.text.trim();
    if (ip.isEmpty) return;
    if (!ip.startsWith('http')) ip = 'http://$ip';
    if (!ip.endsWith(':5000') && !ip.contains('ngrok')) ip = '$ip:5000';

    await _controller.clearCache();
    setState(() {
      _currentUrl = ip;
      _isConnected = true;
    });
    _controller.loadRequest(Uri.parse(_currentUrl)); // Only loads if URL is valid
  }

  @override
  Widget build(BuildContext context) {
    if (!_isConnected) {
      return Scaffold(
        body: Container(
          decoration: const BoxDecoration(
            gradient: RadialGradient(
              center: Alignment.center,
              radius: 1.5,
              colors: [Color(0xFF2A2A2A), Color(0xFF121212)],
            ),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 30.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
               Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [BoxShadow(color: const Color(0xFF00D8FF).withOpacity(0.3), blurRadius: 40)],
                ),
                child: const Icon(Icons.router_outlined, size: 80, color: Color(0xFF00D8FF)),
              ),
              const SizedBox(height: 40),
              TextField(
                controller: _ipController,
                decoration: const InputDecoration(labelText: 'TARGET IP ADDRESS', hintText: '192.168.0.100', prefixIcon: Icon(Icons.wifi)),
                style: const TextStyle(color: Colors.white, fontFamily: 'Courier'),
              ),
              const SizedBox(height: 30),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _connect,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00D8FF),
                    foregroundColor: Colors.black,
                  ),
                  child: const Text('CONNECT TERMINAL', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 2)),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 1. Camera Feed
          WebViewWidget(controller: _controller),

          // 2. HUD Overlay
          SafeArea(
            child: Column(
              children: [
                // Top Bar
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  color: Colors.black.withOpacity(0.4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _statusWidget(Icons.battery_5_bar, "85%"),
                      const Text("LIVE FEED", style: TextStyle(color: Color(0xFF00D8FF), fontWeight: FontWeight.bold, letterSpacing: 2)),
                      _statusWidget(Icons.wifi, "SIGNAL"),
                    ],
                  ),
                ),
                
                const Spacer(),

                // Bottom Controls
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      // FUNCTIONAL JOYSTICK
                      CustomJoystick(
                        onDirectionChanged: (dir) => _sendCommand(dir),
                        onReleased: () => _sendCommand('stop'),
                      ),
                      
                      // Action Grid
                      _buildActionButtons(),
                    ],
                  ),
                ),
              ],
            ),
          ),
          
          // Disconnect
          Positioned(top: 40, right: 10, child: IconButton(icon: const Icon(Icons.power_settings_new, color: Colors.red), onPressed: () => setState(() => _isConnected = false))),
        ],
      ),
    );
  }

  Widget _statusWidget(IconData icon, String label) {
    return Row(children: [Icon(icon, color: Colors.green, size: 20), const SizedBox(width: 5), Text(label, style: const TextStyle(color: Colors.green, fontFamily: 'Courier'))]);
  }

  Widget _buildActionButtons() {
    return SizedBox(
      width: 140,
      height: 140,
      child: Stack(
        children: [
          Positioned(top: 0, left: 45, child: _btn(Icons.keyboard_arrow_up, 'forward')),
          Positioned(bottom: 0, left: 45, child: _btn(Icons.keyboard_arrow_down, 'backward')),
          Positioned(left: 0, top: 45, child: _btn(Icons.keyboard_arrow_left, 'left')),
          Positioned(right: 0, top: 45, child: _btn(Icons.keyboard_arrow_right, 'right')),
        ],
      ),
    );
  }

  Widget _btn(IconData icon, String cmd) {
    return GestureDetector(
      onTapDown: (_) => _sendCommand(cmd),
      onTapUp: (_) => _sendCommand('stop'),
      onTapCancel: () => _sendCommand('stop'),
      child: Container(
        width: 50, height: 50,
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.5), shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFF00D8FF).withOpacity(0.5)),
        ),
        child: Icon(icon, color: const Color(0xFF00D8FF), size: 30),
      ),
    );
  }
}

// --- Custom Functional Joystick Widget ---
class CustomJoystick extends StatefulWidget {
  final Function(String) onDirectionChanged;
  final VoidCallback onReleased;

  const CustomJoystick({super.key, required this.onDirectionChanged, required this.onReleased});

  @override
  State<CustomJoystick> createState() => _CustomJoystickState();
}

class _CustomJoystickState extends State<CustomJoystick> {
  Offset _delta = Offset.zero;
  final double _radius = 60.0; // Max drag distance

  void _updateDelta(Offset localPosition) {
    // Local position is relative to the box (120x120), center is (60,60)
    final Offset center = const Offset(60, 60);
    final Offset newDelta = localPosition - center;
    final double dist = newDelta.distance;
    
    // Clamp to radius
    Offset clamped = dist <= _radius ? newDelta : Offset.fromDirection(newDelta.direction, _radius);
    
    setState(() {
      _delta = clamped;
    });

    // Calculate Direction
    if (dist > 10) { // Deadzone
      String dir = '';
      if (clamped.dx.abs() > clamped.dy.abs()) {
        dir = clamped.dx > 0 ? 'right' : 'left';
      } else {
        dir = clamped.dy > 0 ? 'backward' : 'forward'; // Y is down in Flutter (Drag down = positive Y)
      }
      widget.onDirectionChanged(dir);
    }
  }

  void _onDragEnd() {
    setState(() {
      _delta = Offset.zero;
    });
    widget.onReleased();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 150,
      height: 150,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withOpacity(0.2)),
      ),
      child: Center(
        child: GestureDetector(
          // Important: We need a container that captures gestures.
          // Using a transparent container of the hit size.
          onPanStart: (details) => _updateDelta(details.localPosition),
          onPanUpdate: (details) => _updateDelta(details.localPosition),
          onPanEnd: (_) => _onDragEnd(),
          child: Container(
            width: 120,
            height: 120,
            color: Colors.transparent, 
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                // The dragging knob
                Positioned(
                   left: 60 + _delta.dx - 25, // CenterX + dx - radius
                   top: 60 + _delta.dy - 25, // CenterY + dy - radius
                   child: Container(
                      width: 50,
                      height: 50,
                      decoration: BoxDecoration(
                        color: const Color(0xFF00D8FF).withOpacity(0.8),
                        shape: BoxShape.circle,
                        boxShadow: [BoxShadow(color: const Color(0xFF00D8FF), blurRadius: 15)],
                      ),
                      child: const Icon(Icons.gamepad, color: Colors.black87),
                   ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
