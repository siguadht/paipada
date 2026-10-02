"""应用配置：从项目根目录 .env 读取，代码不硬编码密钥与模型名。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> 拍拍搭/（项目根）
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 火山方舟（LLM + 即梦生图共用一个 Ark Key）
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_llm_model: str = ""
    ark_image_model: str = ""

    # 数据库
    database_url: str = f"sqlite:///{DATA_DIR / 'app.db'}"

    # JWT 会话
    jwt_secret: str = "dev-only-secret-change-me-in-env-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 天

    # 上传与输入限制
    max_upload_mb: int = 10
    max_input_chars: int = 200
    allowed_image_types: tuple = ("jpg", "jpeg", "png", "webp")

    # 超时与重试
    llm_timeout_seconds: int = 30
    image_timeout_seconds: int = 60
    max_regenerate_times: int = 3
    max_design_edits: int = 8  # 新编辑流程的单方案调用护栏
    demo_product_catalog: bool = False  # 仅本机演示用商品图片；正式环境保持关闭

    # 火山 TOS 对象存储（图生图照片中转）
    tos_access_key: str = ""
    tos_secret_key: str = ""
    tos_region: str = "cn-beijing"
    tos_endpoint: str = "https://tos-cn-beijing.volces.com"
    tos_bucket: str = "paipaida-app"

    # 目录
    upload_dir: str = str(DATA_DIR / "uploads")
    generated_dir: str = str(DATA_DIR / "generated")

    @property
    def has_ark_key(self) -> bool:
        return bool(self.ark_api_key and self.ark_api_key.strip())


settings = Settings()
