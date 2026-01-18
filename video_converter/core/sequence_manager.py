"""
執行緒安全的序列號管理器
用於管理輸出檔案的序列號
"""
import os
import threading
from pathlib import Path
from typing import Optional


class SequenceManager:
    """執行緒安全的序列號管理器"""
    
    def __init__(self, sequence_file: str = "sequence_number.txt"):
        """
        初始化序列號管理器
        
        Args:
            sequence_file: 序列號檔案路徑
        """
        self.sequence_file = Path(sequence_file)
        self.lock = threading.Lock()
        self.current_sequence = self._load_sequence()
    
    def _load_sequence(self) -> int:
        """從檔案載入序列號"""
        try:
            if self.sequence_file.exists():
                with open(self.sequence_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return int(content)
        except (ValueError, IOError) as e:
            print(f"警告: 無法載入序列號檔案: {e}")
        return 1
    
    def _save_sequence(self) -> None:
        """儲存序列號到檔案"""
        try:
            with open(self.sequence_file, "w", encoding="utf-8") as f:
                f.write(str(self.current_sequence))
        except IOError as e:
            print(f"警告: 無法儲存序列號檔案: {e}")
    
    def get_next(self) -> int:
        """
        取得下一個序列號（執行緒安全）
        
        Returns:
            下一個序列號
        """
        with self.lock:
            seq = self.current_sequence
            self.current_sequence += 1
            self._save_sequence()
            return seq
    
    def reset(self, start_number: int = 1) -> None:
        """
        重置序列號
        
        Args:
            start_number: 起始序列號
        """
        with self.lock:
            self.current_sequence = start_number
            self._save_sequence()
    
    def get_current(self) -> int:
        """
        取得當前序列號（不遞增）
        
        Returns:
            當前序列號
        """
        with self.lock:
            return self.current_sequence
