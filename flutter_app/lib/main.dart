import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

void main() {
  runApp(const RobotApp());
}

class RobotApp extends StatelessWidget {
  const RobotApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Antigravity Robot',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF121212),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF1E1E1E),
          elevation: 0,
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
  
  // Default to a common local IP, but allow user to change it
  String _currentUrl = 'http://192.168.0.100:5000'; 
  bool _isConnected = false;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (String url) {},
          onPageFinished: (String url) {},
          onWebResourceError: (WebResourceError error) {},
        ),
      );
  }

  void _connect() {
    String ip = _ipController.text.trim();
    if (ip.isEmpty) return;
    
    if (!ip.startsWith('http')) {
      ip = 'http://$ip';
    }
    if (!ip.endsWith(':5000')) {
      ip = '$ip:5000';
    }

    setState(() {
      _currentUrl = ip;
      _isConnected = true;
    });
    _controller.loadRequest(Uri.parse(_currentUrl));
  }

  @override
  Widget build(BuildContext context) {
    if (!_isConnected) {
      return Scaffold(
        appBar: AppBar(title: const Text('Connect to Robot')),
        body: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.router, size: 80, color: Colors.cyan),
              const SizedBox(height: 20),
              TextField(
                controller: _ipController,
                decoration: const InputDecoration(
                  labelText: 'Robot IP Address',
                  hintText: 'e.g. 192.168.1.13',
                  border: OutlineInputBorder(),
                  filled: true,
                  fillColor: Color(0xFF1E1E1E),
                ),
                keyboardType: TextInputType.number,
                style: const TextStyle(color: Colors.white),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _connect,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.cyan,
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 15),
                ),
                child: const Text('CONNECT', style: TextStyle(fontSize: 18)),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      // No AppBar in connected mode for full screen feel, or keep it for a "Disconnect" button
      appBar: AppBar(
        title: const Text('Robot Control'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _controller.reload(),
          ),
          IconButton(
            icon: const Icon(Icons.link_off),
            onPressed: () => setState(() => _isConnected = false),
          ),
        ],
      ),
      body: WebViewWidget(controller: _controller),
    );
  }
}
