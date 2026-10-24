from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Agent Red-Teaming Framework"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = Field(default="dev-secret-key-minimum-32-characters-long", min_length=32)
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite+aiosqlite:///./redteam_dev.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 1800
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 4
    # true = run tasks in the API process (no Redis/worker needed). Local dev and tests only.
    CELERY_TASK_ALWAYS_EAGER: bool = False

    PRIMARY_JUDGE_PROVIDER: str = "openai"
    PRIMARY_JUDGE_MODEL: str = "gpt-4o-2024-08-06"
    PRIMARY_JUDGE_API_KEY: str = ""
    PRIMARY_JUDGE_BASE_URL: str = ""

    SECONDARY_JUDGE_PROVIDER: str = "anthropic"
    SECONDARY_JUDGE_MODEL: str = "claude-3-5-sonnet-20241022"
    SECONDARY_JUDGE_API_KEY: str = ""
    SECONDARY_JUDGE_BASE_URL: str = ""

    GENERATOR_PROVIDER: str = "openai"
    GENERATOR_MODEL: str = "gpt-4o-2024-08-06"
    GENERATOR_API_KEY: str = ""
    GENERATOR_BASE_URL: str = ""

    PLANNER_PROVIDER: str = "openai"
    PLANNER_MODEL: str = "gpt-4o-2024-08-06"
    PLANNER_API_KEY: str = ""
    PLANNER_BASE_URL: str = ""

    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""

    EVAL_MODE: str = "local"

    TARGET_AGENT_DEFAULT_TIMEOUT: int = 30
    TARGET_AGENT_MAX_RETRIES: int = 3
    TARGET_AGENT_ALLOWED_HOSTS: str = ""
    TARGET_AGENT_BLOCK_PRIVATE_IPS: bool = True

    CHROMA_HOST: str = ""
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_PREFIX: str = "redteam"

    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""  # Optional - only required if using S3 storage
    S3_SECRET_KEY: str = ""  # Optional - only required if using S3 storage
    S3_BUCKET: str = "redteam-artifacts"
    S3_REGION: str = "us-east-1"

    LOCAL_STORAGE_PATH: str = "./storage"

    STORAGE_BACKEND: str = "local"  # Options: "local", "s3"

    @field_validator("S3_ACCESS_KEY", "S3_SECRET_KEY")
    @classmethod
    def validate_s3_credentials(cls, v: str, info) -> str:
        # NOTE: `info.data` only contains the fields declared *before* this one,
        # so STORAGE_BACKEND cannot be read reliably here. The cross-field
        # check lives in `validate_production_configuration` instead.
        return v

    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str = ""
    JWT_PUBLIC_KEY_PATH: str = ""
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    OIDC_ISSUER_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_SCOPES: str = "openid,profile,email"

    CORS_ORIGINS: str | list[str] = ""
    CORS_ALLOW_CREDENTIALS: bool = True

    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    # Comma-separated list of proxy addresses whose X-Forwarded-For header may
    # be trusted. Defaults to loopback only, which is correct for a local
    # development server; configure the real load-balancer addresses in a
    # container deployment.
    TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"

    JUDGE_TEMPERATURE: float = 0.0
    JUDGE_MAX_TOKENS: int = 2048
    JUDGE_CONFIDENCE_THRESHOLD: float = 0.7
    JUDGE_DOUBLE_SCORE: bool = True
    JUDGE_RETRY_ON_SCHEMA_ERROR: bool = True

    EXACT_MATCH_CASE_SENSITIVE: bool = False
    REGEX_MATCH_TIMEOUT_MS: int = 1000

    REGRESSION_DETECTION_ENABLED: bool = True
    SEVERITY_CRITICAL_OVERRIDE: bool = True

    GATE_CRITICAL_ACTION: str = "block"
    GATE_HIGH_ACTION: str = "block"
    GATE_MEDIUM_ACTION: str = "warn"
    GATE_LOW_ACTION: str = "warn"
    GATE_INCONCLUSIVE_ACTION: str = "fail"
    GATE_INFRA_FAILURE_ACTION: str = "fail"

    ADVERSARIAL_GENERATION_ENABLED: bool = True
    ADVERSARIAL_NOVELTY_THRESHOLD: float = 0.75
    ADVERSARIAL_BATCH_SIZE: int = 10
    ADVERSARIAL_MAX_RETRIES: int = 3

    REDTEAM_MAX_TURNS: int = 8
    REDTEAM_TURN_TIMEOUT_SECONDS: int = 30

    COST_PER_RUN_LIMIT_USD: float = 5.0
    COST_DAILY_LIMIT_USD: float = 100.0
    COST_TRACKING_ENABLED: bool = True

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "redteam-framework"
    OTEL_TRACES_SAMPLER: str = "parentbased_always_on"
    OTEL_METRICS_EXPORT_INTERVAL_MS: int = 60000

    PROMETHEUS_METRICS_PORT: int = 9090

    ALERT_WEBHOOK_URL: str = ""
    ALERT_CRITICAL_WEBHOOK_URL: str = ""

    FEATURE_ADVERSARIAL_GENERATOR: bool = True
    FEATURE_REDTEAM_AGENT: bool = True
    FEATURE_SECONDARY_JUDGE: bool = True
    FEATURE_RAG_RETRIEVAL: bool = True
    FEATURE_STREAMING_RESPONSES: bool = False
    FEATURE_EXPERIMENTAL_UI: bool = False

    TRANSCRIPT_RETENTION_DAYS: int = 365
    CRITICAL_FINDINGS_RETENTION_DAYS: int = 0
    REPORT_RETENTION_DAYS: int = 365
    AUDIT_LOG_RETENTION_DAYS: int = 2555

    DEV_SEED_DATA: bool = True
    DEV_MOCK_TARGET_AGENT: bool = True
    DEV_MOCK_JUDGE: bool = True

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        """Fail fast on a configuration that is unsafe in production.

        These checks run once, at startup, instead of failing later on a
        per-request basis with an opaque error.
        """
        if not self.is_production:
            return self

        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")

        if "*" in self.cors_origins_list:
            raise ValueError(
                "CORS_ORIGINS must not contain '*' in production when credentials are allowed"
            )

        if self.CORS_ALLOW_CREDENTIALS and not self.cors_origins_list:
            raise ValueError(
                "CORS_ORIGINS must list the allowed origins when credentials are enabled"
            )

        if self.STORAGE_BACKEND == "s3" and not (self.S3_ACCESS_KEY and self.S3_SECRET_KEY):
            raise ValueError("S3 credentials are required when STORAGE_BACKEND=s3")

        if self.EVAL_MODE == "local":
            raise ValueError(
                "EVAL_MODE=local uses the deterministic mock judge and must not be used "
                "in production; set EVAL_MODE=provider"
            )

        if self.DEV_MOCK_JUDGE or self.DEV_MOCK_TARGET_AGENT:
            raise ValueError(
                "DEV_MOCK_JUDGE and DEV_MOCK_TARGET_AGENT must be disabled in production"
            )

        return self

    @field_validator("TARGET_AGENT_ALLOWED_HOSTS")
    @classmethod
    def parse_allowed_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        return [host.strip() for host in v.split(",") if host.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return self.parse_cors_origins(self.CORS_ORIGINS)

    @property
    def allowed_hosts_list(self) -> list[str]:
        if isinstance(self.TARGET_AGENT_ALLOWED_HOSTS, list):
            return self.TARGET_AGENT_ALLOWED_HOSTS
        return self.parse_allowed_hosts(self.TARGET_AGENT_ALLOWED_HOSTS)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
