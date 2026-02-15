"""
硬體加速編碼器偵測模組
自動偵測系統可用的硬體加速編碼器
"""
import os
import re
import subprocess
from typing import List, Optional, Tuple


FFMPEG_PATHS = [
    "C:/ffmpeg/bin/ffmpeg.exe",
    "C:/ffmpeg/ffmpeg.exe",
    "ffmpeg",
]


def find_ffmpeg() -> str:
    """搜尋 FFmpeg 可執行檔"""
    for path in FFMPEG_PATHS:
        if path == "ffmpeg":
            return path
        if os.path.isfile(path):
            return path
    return "ffmpeg"


def check_nvidia_driver() -> Tuple[bool, str]:
    """
    檢查 NVIDIA 驅動程式版本
    
    Returns:
        (是否支援, 訊息)
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            encoding="utf-8"
        )
        if result.returncode != 0:
            return False, "無法取得 NVIDIA 驅動版本"
        
        driver_version = result.stdout.strip()
        
        # 解析驅動版本號
        match = re.match(r'(\d+)\.(\d+)', driver_version)
        if not match:
            return True, f"驅動版本: {driver_version}"
        
        major = int(match.group(1))
        minor = int(match.group(2))
        
        # NVENC 需要驅動版本 570.0 或更新 (12.2 API)
        if major > 570:
            return True, f"驅動版本 {driver_version} - 支援 NVENC"
        elif major == 570 and minor >= 0:
            return True, f"驅動版本 {driver_version} - 支援 NVENC"
        else:
            return False, f"驅動版本 {driver_version} 太舊，需要 570.0+ (當前 API: {major}.{minor})"
            
    except FileNotFoundError:
        return False, "找不到 nvidia-smi"
    except Exception as e:
        return False, f"檢查驅動失敗: {e}"


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
        
        ffmpeg_path = find_ffmpeg()
        
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
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
        
        ffmpeg_path = find_ffmpeg()
        
        try:
            result = subprocess.run(
                [ffmpeg_path, "-hide_banner", "-encoders"],
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
        """檢查 NVIDIA NVENC 是否可用（包含驅動版本檢查）"""
        if not self._check_encoder("h264_nvenc"):
            return False
        
        # 檢查 NVIDIA 驅動版本
        supported, message = check_nvidia_driver()
        if not supported:
            print(f"NVENC: {message}")
        return supported
    
    def get_nvidia_driver_status(self) -> Tuple[bool, str]:
        """取得 NVIDIA 驅動狀態"""
        return check_nvidia_driver()
    
    def _check_qsv(self) -> bool:
        """檢查 Intel QSV 是否可用"""
        return self._check_encoder("h264_qsv")
    
    def _check_amf(self) -> bool:
        """檢查 AMD AMF 是否可用"""
        return self._check_encoder("h264_amf")
    
    def _check_hevc_amf(self) -> bool:
        """檢查 AMD HEVC (H.265) AMF 是否可用"""
        return self._check_encoder("hevc_amf")
    
    def _check_hevc_qsv(self) -> bool:
        """檢查 Intel HEVC (H.265) QSV 是否可用"""
        return self._check_encoder("hevc_qsv")
    
    def _check_hevc_nvenc(self) -> bool:
        """檢查 NVIDIA HEVC (H.265) NVENC 是否可用"""
        if not self._check_encoder("hevc_nvenc"):
            return False
        supported, message = check_nvidia_driver()
        if not supported:
            print(f"HEVC NVENC: {message}")
        return supported
    
    def detect_available_encoders(self) -> List[str]:
        """
        偵測所有可用的編碼器（按優先順序）
        
        Returns:
            可用編碼器列表，按優先順序排列
        """
        if self._available_encoders is not None:
            return self._available_encoders.copy()
        
        encoders = []
        
        # HEVC (H.265) 硬體加速編碼器 - 放在最前面（最小容量）
        if self._check_hevc_nvenc():
            encoders.append("hevc_nvenc")
        
        if self._check_hevc_amf():
            encoders.append("hevc_amf")
        
        if self._check_hevc_qsv():
            encoders.append("hevc_qsv")
        
        # H.264 硬體加速編碼器
        if self._check_nvenc():
            encoders.append("h264_nvenc")
        
        if self._check_qsv():
            encoders.append("h264_qsv")
        
        if self._check_amf():
            encoders.append("h264_amf")
        
        # 軟體編碼作為備援
        if self._check_encoder("libx265"):
            encoders.append("libx265")
        
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
