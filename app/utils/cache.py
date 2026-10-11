import time
from typing import Optional, List, Dict, Tuple, Any

class AppCache:
    """Xotirada (In-memory) tezkor ma'lumotlarni keshlovchi klass.
    Tugmalar qotmasligi va Telegram API / Supabase bazasiga qayta-qayta
    ortiqcha so'rovlar yuborilmasligi uchun xizmat qiladi.
    """
    def __init__(self):
        self._bot_username: Optional[str] = None
        
        # user_id -> expire_timestamp
        self._subscribed_users: Dict[int, float] = {}
        
        # channels_cache: (expire_timestamp, channels_list)
        self._channels_cache: Optional[Tuple[float, List[Any]]] = None
        
        # categories_cache: key -> (expire_timestamp, categories_list)
        self._categories_cache: Dict[str, Tuple[float, List[Any]]] = {}

    # --- BOT USERNAME CACHE ---
    def set_bot_username(self, username: str):
        self._bot_username = username

    def get_bot_username(self) -> Optional[str]:
        return self._bot_username

    # --- SUBSCRIPTION CACHE ---
    def is_user_subscribed(self, user_id: int) -> bool:
        exp = self._subscribed_users.get(user_id)
        if exp and exp > time.time():
            return True
        if exp:
            self._subscribed_users.pop(user_id, None)
        return False

    def mark_user_subscribed(self, user_id: int, ttl_seconds: int = 600):
        """Foydalanuvchi obunasini 10 daqiqaga keshlaydi."""
        self._subscribed_users[user_id] = time.time() + ttl_seconds

    def invalidate_user_subscription(self, user_id: int):
        self._subscribed_users.pop(user_id, None)

    # --- CHANNELS CACHE ---
    def get_cached_channels(self) -> Optional[List[Any]]:
        if self._channels_cache:
            exp, data = self._channels_cache
            if exp > time.time():
                return data
            self._channels_cache = None
        return None

    def set_cached_channels(self, channels: List[Any], ttl_seconds: int = 120):
        self._channels_cache = (time.time() + ttl_seconds, channels)

    def invalidate_channels(self):
        self._channels_cache = None
        self._subscribed_users.clear()

    # --- CATEGORIES CACHE ---
    def get_cached_categories(self, active_only: bool = True) -> Optional[List[Any]]:
        key = f"cat_{active_only}"
        entry = self._categories_cache.get(key)
        if entry:
            exp, data = entry
            if exp > time.time():
                return data
            self._categories_cache.pop(key, None)
        return None

    def set_cached_categories(self, categories: List[Any], active_only: bool = True, ttl_seconds: int = 300):
        key = f"cat_{active_only}"
        self._categories_cache[key] = (time.time() + ttl_seconds, categories)

    def invalidate_categories(self):
        self._categories_cache.clear()

# Global yagona kesh instansi
cache = AppCache()
