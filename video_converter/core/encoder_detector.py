"""
硬體加速編碼器偵測模組
自動偵測系統可用的硬體加速編碼器
"""
import subprocess
from typing import List, Optional


class EncoderDetector:
    """硬體加速編碼器偵測器"""
    
    def __init__(self):
        self._available_encoders: Optional[List[str]] = None
        self._ffmpeg_available: Optional[bool] = None
    
    def check_ffmpeg(self) -> bool:
        """
        檢查 FFmpeg 是否可用
        
        Returns:
            True 如果 FFmpeg 可用
        """
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            self._ffmpeg_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._ffmpeg_available = False
        
        return self._ffmpeg_available
    
    def _check_encoder(self, encoder_name: str) -> bool:
        """
        檢查特定編碼器是否可用
        
        Args:
            encoder_name: 編碼器名稱（如 'h264_nvenc'）
        
        Returns:
            True 如果編碼器可用
        """
        if not self.check_ffmpeg():
            return False
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                encoding="utf-8"
            )
            if result.returncode == 0:
                return encoder_name in result.stdout
        except (subprocess.TimeoutExpired, UnicodeDecodeError):
            pass
        
        return False
    
    def _check_nvenc(self) -> bool:
        """檢查 NVIDIA NVENC 是否可用"""
        return self._check_encoder("h264_nvenc")
    
    def _check_qsv(self) -> bool:
        """檢查 Intel QSV 是否可用"""
        return self._check_encoder("h264_qsv")
    
    def _check_amf(self) -> bool:
        """檢查 AMD AMF 是否可用"""
        return self._check_encoder("h264_amf")
    
    def detect_available_encoders(self) -> List[str]:
        """
        偵測所有可用的編碼器（按優先順序）
        
        Returns:
            可用編碼器列表，按優先順序排列
        """
        if self._available_encoders is not None:
            return self._available_encoders.copy()
        
        encoders = []
        
        # 硬體加速編碼器（按效能優先順序）
        if self._check_nvenc():
            encoders.append("h264_nvenc")
        
        if self._check_qsv():
            encoders.append("h264_qsv")
        
        if self._check_amf():
            encoders.append("h264_amf")
        
        # 軟體編碼作為備援
        if self._check_encoder("libx264"):
            encoders.append("libx264")
        
        # 如果沒有任何編碼器可用，至少返回 libx264（FFmpeg 預設）
        if not encoders:
            encoders.append("libx264")
        
        self._available_encoders = encoders
        return encoders.copy()
    
    def get_best_encoder(self) -> str:
        """
        取得最佳可用編碼器
        
        Returns:
            最佳編碼器名稱
        """
        encoders = self.detect_available_encoders()
        return encoders[0] if encoders else "libx264"
    
    def is_hardware_accelerated(self, encoder: str) -> bool:
        """
        檢查編碼器是否為硬體加速
        
        Args:
            encoder: 編碼器名稱
        
        Returns:
            True 如果是硬體加速編碼器
        """
        hardware_encoders = ["h264_nvenc", "h264_qsv", "h264_amf"]
        return encoder in hardware_encoders
