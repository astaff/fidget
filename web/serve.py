#! /usr/bin/env python3

from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable


def get_script_directory() -> str:
    """Returns the directory where the script is located"""
    return str(Path(__file__).parent)

def create_handler() -> type:
    """Creates a request handler that serves from the script's directory"""
    class CustomHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            # Set the directory to the script's location
            directory = get_script_directory()
            super().__init__(*args, directory=directory, **kwargs)
            
        def do_GET(self):
            if self.path == '/':
                self.path = '/index.html'
            return super().do_GET()
    return CustomHandler

def run_server(port: int = 8080, handler: Callable[..., Any] = None) -> None:
    """Runs the HTTP server with the specified port and handler"""
    server_address = ('', port)
    handler = handler or create_handler()
    httpd = HTTPServer(server_address, handler)
    print(f"Server running on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
