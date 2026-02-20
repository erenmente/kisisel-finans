"""
Finans Asistanı - Profesyonel Logging Sistemi
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Log dosyası konumu
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Renkli terminal çıktısı için ANSI kodları
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """Renkli log formatter - terminal için"""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.GRAY,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA,
    }
    
    def format(self, record):
        # Seviyeye göre renk seç
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        
        # Zaman formatı
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Log mesajını formatla
        level_short = record.levelname[0]  # I, W, E, D, C
        
        # Emoji ekle
        emoji = {
            logging.DEBUG: "🔍",
            logging.INFO: "ℹ️",
            logging.WARNING: "⚠️",
            logging.ERROR: "❌",
            logging.CRITICAL: "💀",
        }.get(record.levelno, "")
        
        formatted = f"{Colors.GRAY}{timestamp}{Colors.RESET} {color}[{level_short}]{Colors.RESET} {emoji} {record.getMessage()}"
        
        return formatted


class FileFormatter(logging.Formatter):
    """Dosya için log formatter - renksiz, detaylı"""
    
    def format(self, record):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{timestamp} | {record.levelname:8} | {record.name:20} | {record.getMessage()}"


def setup_logger(name: str = "FinansAsistan", level: int = logging.INFO) -> logging.Logger:
    """
    Logger'ı yapılandır ve döndür.
    
    Args:
        name: Logger adı
        level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Yapılandırılmış logger nesnesi
    """
    logger = logging.getLogger(name)
    
    # Zaten yapılandırılmışsa tekrar yapma
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 1. Konsol Handler (Renkli)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # 2. Dosya Handler (Rotating - max 5MB, 3 yedek)
    log_file = LOG_DIR / f"{name.lower()}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Dosyaya her şeyi yaz
    file_handler.setFormatter(FileFormatter())
    logger.addHandler(file_handler)
    
    # Propagation'ı kapat (üst logger'a iletme)
    logger.propagate = False
    
    logger.info(f"Logger başlatıldı: {name}")
    
    return logger


# Ana logger instance
main_logger = setup_logger("FinansAsistan")


# Kısa yollar
def info(msg): main_logger.info(msg)
def warning(msg): main_logger.warning(msg)
def error(msg): main_logger.error(msg)
def debug(msg): main_logger.debug(msg)


if __name__ == "__main__":
    # Test
    logger = setup_logger("TestLogger", logging.DEBUG)
    logger.debug("Bu bir debug mesajı")
    logger.info("Bu bir bilgi mesajı")
    logger.warning("Bu bir uyarı mesajı")
    logger.error("Bu bir hata mesajı")
    logger.critical("Bu kritik bir mesaj")
