from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Drinks4All"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    remember_me_days: int = 30

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/drinks4all"
    timezone: str = "Europe/Berlin"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_sender: str = "noreply@drinks4all.local"
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False

    buyer_report_email: str = "buyer@drinks4all.local"
    admin_report_email: str | None = None  # backward-compat with old .env
    paypal_me_url: str = ""

    upload_dir: str = "app/static/uploads"
    max_upload_mb: int = 5

    enable_scheduler: bool = True
    testing: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
if settings.admin_report_email and settings.buyer_report_email == "buyer@drinks4all.local":
    settings.buyer_report_email = settings.admin_report_email
