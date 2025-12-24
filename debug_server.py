from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(b"<h1>SUCCESS! Connectivity is working.</h1>")

print("Starting Simple Server on 0.0.0.0:5000...")
httpd = HTTPServer(('0.0.0.0', 5000), SimpleHandler)
httpd.serve_forever()
