import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str = "8973630874:AAEP3pLmFAEFUgRiXx35CIWdHTd1Vna42HU"
    ADMINS: str = "8887751785"
    STORAGE_CHANNEL_ID: int = -1004309883485
    DATABASE_URL: str = "postgresql://postgres.fmvqghythrtrpktjjfup:FrQo52cP5azl8r19@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMINS:
            return []
        ids = []
        for x in self.ADMINS.split(","):
            cleaned = x.strip()
            if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
                ids.append(int(cleaned))
        return ids

settings = Settings()
