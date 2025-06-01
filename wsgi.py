import asyncio
import uvicorn
from app import app

def run_server():
    """Run the FastAPI app with uvicorn"""
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)

# For WSGI compatibility, create an ASGI to WSGI adapter
try:
    from asgiref.wsgi import WsgiToAsgi
    application = WsgiToAsgi(app)
except ImportError:
    # Direct ASGI application
    application = app

if __name__ == "__main__":
    run_server()