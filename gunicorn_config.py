import os

workers = 1
worker_class = 'gevent'
port = os.environ.get('PORT', '8000')
bind = f"0.0.0.0:{port}"
timeout = 300 