"""
配置管理模組
處理應用程式的設定儲存與載入
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "width": 1280,
        "height": 720,
        "bitrate": "1000k",
        "encoder": "auto",
        "threads": 1,
        "timeout": 300,
        "delete_original": True,
        "output_prefix": "av",
        "sequence_file": "sequence_number.txt"
    }
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置檔案路徑
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """從檔案載入配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # 合併預設配置與載入的配置
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告: 無法載入配置檔案: {e}，使用預設配置")
        
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self) -> None:
        """儲存配置到檔案"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"警告: 無法儲存配置檔案: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        取得配置值
        
        Args:
            key: 配置鍵
            default: 預設值
        
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        設定配置值
        
        Args:
            key: 配置鍵
            value: 配置值
        """
        self.config[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """
        批量更新配置
        
        Args:
            updates: 要更新的配置字典
        """
        self.config.update(updates)
    
    def reset_to_default(self) -> None:
        """重置為預設配置"""
        self.config = self.DEFAULT_CONFIG.copy()
    
    def get_all(self) -> Dict[str, Any]:
        """
        取得所有配置
        
        Returns:
            配置字典的副本
        """
        return self.config.copy()
