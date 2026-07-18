from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# data目录
DATA_DIR = BASE_DIR / "data"

RULE_FILE = DATA_DIR / "0.rule.xlsx"
RAW_DIR = DATA_DIR / "raw_data"
PHOTO_BASE_DIR = DATA_DIR / "photos"
PRODUCTION_FILE = DATA_DIR / "production" / "production.xls"
UF_DATA_DIR = DATA_DIR / "uf_check"

APP_VERSION = "20260609_001"
LOGIN_USERNAME = "QA"
LOGIN_PASSWORD = "123123"