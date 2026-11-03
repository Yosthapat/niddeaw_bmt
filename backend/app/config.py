from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    jwt_secret: str
    jwt_expire_minutes: int = 720
    cors_origins: str = "http://localhost:5173"
    env: str = "development"
    # The weekly copy into Google Sheets (app/services/sheets_sync.py). All
    # three optional: unset, the sync is simply off and the settings page
    # says what is missing.
    google_service_account_json: str | None = None
    sheets_spreadsheet_id: str | None = None
    # What the weekly GitHub Action sends to /api/internal/sheets-sync.
    sheets_sync_secret: str | None = None
    # LINE Login (app/services/line_auth.py). The channel id is what an ID
    # token from LINE must have been issued for; the LIFF id is the app the
    # /line page opens as inside LINE. Both unset: the LINE pages say they
    # are not set up yet.
    line_login_channel_id: str | None = None
    line_liff_id: str | None = None
    # How long a member stays signed in on the /line page before LINE is
    # asked again. Opening it from LINE asks again anyway.
    line_token_minutes: int = 720

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
