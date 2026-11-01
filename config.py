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

APP_VERSION = "20261101_001"
LOGIN_USERNAME = "QA"
LOGIN_PASSWORD = "123123"

# ---------- 日期识别配置 ----------
# 原始数据日期来源：优先取 Excel 内的“检测日期”列，而不是文件名
DETECT_DATE_COLUMN = "检测日期"

# 班次分界时刻（小时）：检测时间早于该时刻的记录归属上一个生产日。
# 口径与原始文件命名一致（文件名 = 检测日期按 08:00 切分后的生产日）。
SHIFT_BOUNDARY_HOUR = 8

# 去重标识：同一条码 + 同一检测时刻 + 同一分类 + 同一原因 视为同一条检测记录
DEDUPE_KEY = ["条码", "检测日期", "检测分类", "检测原因"]