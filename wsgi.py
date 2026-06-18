import sys
import os

# Dynamic lookup for main entrypoint instance
app = None

try:
    from app import app
except ImportError:
    try:
        from main import app
    except ImportError:
        try:
            from run import app
        except ImportError:
            # Look for any object named app inside logical modules
            pass

if app is None:
    raise RuntimeError("Vercel Serverless Error: Could not find the core Flask 'app' instance in app.py, main.py, or run.py")
