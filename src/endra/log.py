import logging
import os
from logging.handlers import RotatingFileHandler

# Formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Console handler (INFO+)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File handler (DEBUG+ with rotation)
file_handler = RotatingFileHandler("endra.log", maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# # Root logger
# logger_root = logging.getLogger()
# # logger_root.setLevel(logging.DEBUG)  # Global default
# logger_root.addHandler(console_handler)
# logger_root.addHandler(file_handler)

logger_endra = logging.getLogger("EndraProtocol")
logger_endra.setLevel(logging.DEBUG)


COMMS_LOG_PATH = "endra_comms.log"

COMMS_LOG_LOGGERS = ["WalId.Datatr", "IPFS-TK-Conversations", "WalId.GDM_Join"]
COMMS_LOG_FORMATTER = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

cl_file_handler = RotatingFileHandler(
    COMMS_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5
)
cl_file_handler.setLevel(logging.DEBUG)
cl_file_handler.setFormatter(formatter)
print(f"Set up comms log at {os.path.abspath(COMMS_LOG_PATH)}")

for logger_name in COMMS_LOG_LOGGERS:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(cl_file_handler)
    logger.debug(f"Initiated comms log for {logger_name}")
