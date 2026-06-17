import os
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Global instances initialized strictly isolated without application context
db = SQLAlchemy()
jwt = JWTManager()

# High performance cross-origin asynchronous architecture setup
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per day", "100 per hour"],
    storage_uri="memory://"
)
