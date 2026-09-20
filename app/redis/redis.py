import redis
from app.core.config import setting

redis_conn = redis.from_url(setting.REDIS_URL, decode_responses=True, socket_timeout=None)
