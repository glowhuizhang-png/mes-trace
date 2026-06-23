import os

# 项目根目录 = config.py 所在的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RULE_FILE = os.path.join(BASE_DIR, "data", "0.rule.xlsx")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw_data")
PHOTO_BASE_DIR = os.path.join(BASE_DIR, "data", "photos")
PRODUCTION_FILE = os.path.join(BASE_DIR, "data", "production", "production.xls")
UF_DATA_DIR = os.path.join(BASE_DIR, "data", "uf_check")

APP_VERSION = "20260609_003"