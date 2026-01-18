"""
日誌工具模組
提供統一的日誌記錄功能
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """日誌管理器"""
    
    def __init__(
        self,
        name: str = "VideoConverter",
        log_file: Optional[str] = None,
        level: int = logging.INFO
    ):
        """
        初始化日誌器
        
        Args:
            name: 日誌器名稱
            log_file: 日誌檔案路徑（可選）
            level: 日誌級別
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重複添加處理器
        if self.logger.handlers:
            return
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台處理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 檔案處理器（如果指定）
        if log_file:
            file_handler = logging.FileHandler(
                log_file,
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str) -> None:
        """記錄資訊訊息"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """記錄警告訊息"""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """記錄錯誤訊息"""
        self.logger.error(message)
    
    def debug(self, message: str) -> None:
        """記錄除錯訊息"""
        self.logger.debug(message)
    
    def exception(self, message: str) -> None:
        """記錄例外訊息（含堆疊追蹤）"""
        self.logger.exception(message)
