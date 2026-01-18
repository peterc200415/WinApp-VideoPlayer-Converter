"""
檔案工具模組
提供檔案相關的實用功能
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple


def get_video_files(
    directory: str,
    extensions: Optional[List[str]] = None
) -> List[Path]:
    """
    取得目錄中的所有影片檔案
    
    Args:
        directory: 目錄路徑
        extensions: 檔案副檔名列表（預設: ['.mp4', '.avi', '.mov', '.mkv']）
    
    Returns:
        影片檔案路徑列表
    """
    if extensions is None:
        extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    
    directory = Path(directory)
    if not directory.is_dir():
        return []
    
    video_files = []
    for ext in extensions:
        video_files.extend(directory.glob(f"*{ext}"))
        video_files.extend(directory.glob(f"*{ext.upper()}"))
    
    return sorted(video_files)


def get_file_size(file_path: str) -> int:
    """
    取得檔案大小（位元組）
    
    Args:
        file_path: 檔案路徑
    
    Returns:
        檔案大小
    """
    return Path(file_path).stat().st_size


def format_file_size(size: int) -> str:
    """
    格式化檔案大小
    
    Args:
        size: 檔案大小（位元組）
    
    Returns:
        格式化後的大小字串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def is_video_file(file_path: str) -> bool:
    """
    檢查是否為影片檔案
    
    Args:
        file_path: 檔案路徑
    
    Returns:
        True 如果是影片檔案
    """
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    return Path(file_path).suffix.lower() in video_extensions


def get_video_info(file_path: str) -> Optional[dict]:
    """
    取得影片資訊（需要 ffprobe）
    
    Args:
        file_path: 影片檔案路徑
    
    Returns:
        影片資訊字典或 None
    """
    import subprocess
    import json
    
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    
    return None


def ensure_directory(path: str) -> Path:
    """
    確保目錄存在
    
    Args:
        path: 目錄路徑
    
    Returns:
        Path 物件
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_delete(file_path: str) -> bool:
    """
    安全刪除檔案
    
    Args:
        file_path: 檔案路徑
    
    Returns:
        True 如果刪除成功
    """
    try:
        Path(file_path).unlink()
        return True
    except Exception:
        return False
