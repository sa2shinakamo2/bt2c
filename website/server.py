from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()

    def do_GET(self):
        # Serve index.html for /explorer path
        if self.path == '/explorer':
            self.path = '/explorer/index.html'
        return super().do_GET()

if __name__ == '__main__':
    # Change to the website directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    server = HTTPServer(('localhost', 8000), CORSRequestHandler)
    print('Starting server at http://localhost:8000')
    server.serve_forever()
