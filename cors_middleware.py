"""
CORS middleware to ensure all responses have appropriate CORS headers.
This is especially important for model files and other static resources.
"""

from flask import request, make_response

class CORSMiddleware:
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        # Check if this is a CORS preflight request
        if environ['REQUEST_METHOD'] == 'OPTIONS':
            # Handle preflight request
            headers = [
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Authorization, Content-Type, Accept, Origin, X-Requested-With, Range'),
                ('Access-Control-Max-Age', '3600'),
                ('Access-Control-Expose-Headers', 'Content-Length, Content-Type, Content-Disposition, Last-Modified, Accept-Ranges, ETag')
            ]
            start_response('200 OK', headers)
            return [b'']
        
        # For regular requests, let the application handle it
        # but we'll intercept the response to add CORS headers
        def cors_start_response(status, headers, exc_info=None):
            # Convert headers to a list if it's not already
            headers_list = list(headers)
            
            # Add CORS headers if not present
            has_cors_origin = False
            for name, value in headers_list:
                if name.lower() == 'access-control-allow-origin':
                    has_cors_origin = True
                    break
            
            if not has_cors_origin:
                headers_list.append(('Access-Control-Allow-Origin', '*'))
                headers_list.append(('Access-Control-Expose-Headers', 'Content-Length, Content-Type, Content-Disposition, Last-Modified, Accept-Ranges, ETag'))
            
            return start_response(status, headers_list, exc_info)
        
        return self.app(environ, cors_start_response)

def apply_cors(app):
    """Apply CORS middleware to a Flask app."""
    return CORSMiddleware(app) 