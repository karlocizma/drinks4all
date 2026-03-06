from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Drinks4All"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/drinks4all"
    timezone: str = "Europe/Berlin"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_sender: str = "noreply@drinks4all.local"
    admin_report_email: str = "admin@drinks4all.local"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
