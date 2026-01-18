"""
核心影片轉換器模組
提供統一的影片轉換介面
"""
import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from .encoder_detector import EncoderDetector
from .sequence_manager import SequenceManager


class VideoConverter:
    """影片轉換器"""
    
    def __init__(
        self,
        encoder: str = "auto",
        width: int = 1280,
        height: int = 720,
        bitrate: str = "1000k",
        threads: int = 1,
        timeout: int = 300,
        sequence_manager: Optional[SequenceManager] = None
    ):
        """
        初始化轉換器
        
        Args:
            encoder: 編碼器名稱（'auto' 表示自動選擇）
            width: 輸出寬度
            height: 輸出高度
            bitrate: 位元率
            threads: 執行緒數
            timeout: 超時時間（秒）
            sequence_manager: 序列號管理器（可選）
        """
        self.encoder_detector = EncoderDetector()
        self.encoder = encoder
        self.width = width
        self.height = height
        self.bitrate = bitrate
        self.threads = threads
        self.timeout = timeout
        self.sequence_manager = sequence_manager or SequenceManager()
        self._stop_event = threading.Event()
    
    def _get_encoder(self) -> str:
        """取得要使用的編碼器"""
        if self.encoder == "auto":
            return self.encoder_detector.get_best_encoder()
        return self.encoder
    
    def _build_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        encoder: str
    ) -> list:
        """
        建立 FFmpeg 命令
        
        Args:
            input_path: 輸入檔案路徑
            output_path: 輸出檔案路徑
            encoder: 編碼器名稱
        
        Returns:
            FFmpeg 命令列表
        """
        command = ["ffmpeg", "-threads", str(self.threads), "-i", input_path]
        
        # 根據編碼器添加特定參數
        if encoder == "h264_nvenc":
            command.extend(["-c:v", "h264_nvenc"])
            command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale={self.width}:{self.height}"])
        elif encoder == "h264_qsv":
            command.extend([
                "-init_hw_device", "qsv=hw",
                "-filter_hw_device", "hw",
                "-hwaccel", "qsv"
            ])
            command.extend(["-c:v", "h264_qsv"])
            command.extend(["-vf", f"scale_qsv=w={self.width}:h={self.height}"])
            command.extend(["-b:v", self.bitrate])
        elif encoder == "h264_amf":
            command.extend(["-c:v", "h264_amf"])
            command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale={self.width}:{self.height}"])
        else:  # libx264 或其他軟體編碼器
            command.extend(["-c:v", encoder])
            command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale={self.width}:{self.height}"])
        
        # 輸出檔案
        command.append(output_path)
        
        return command
    
    def _parse_progress(self, line: str) -> Optional[Dict[str, Any]]:
        """
        解析 FFmpeg 進度輸出
        
        Args:
            line: FFmpeg 輸出行
        
        Returns:
            進度資訊字典或 None
        """
        # 解析 frame=xxx 格式
        frame_match = re.search(r'frame=\s*(\d+)', line)
        if frame_match:
            return {
                "frame": int(frame_match.group(1)),
                "raw_line": line
            }
        return None
    
    def convert(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> bool:
        """
        轉換影片
        
        Args:
            input_path: 輸入檔案路徑
            output_path: 輸出檔案路徑（可選，自動生成）
            progress_callback: 進度回調函數
        
        Returns:
            True 如果轉換成功
        """
        if self._stop_event.is_set():
            return False
        
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"輸入檔案不存在: {input_path}")
        
        # 生成輸出路徑
        if output_path is None:
            seq = self.sequence_manager.get_next()
            output_path = input_path.parent / f"av{seq:04d}.mp4"
        else:
            output_path = Path(output_path)
        
        # 確保輸出目錄存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 取得編碼器
        encoder = self._get_encoder()
        
        # 建立命令
        command = self._build_ffmpeg_command(
            str(input_path),
            str(output_path),
            encoder
        )
        
        try:
            # 啟動 FFmpeg 程序
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace"
            )
            
            # 讀取輸出並解析進度
            while True:
                if self._stop_event.is_set():
                    process.kill()
                    if output_path.exists():
                        output_path.unlink()
                    return False
                
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                if line and progress_callback:
                    progress = self._parse_progress(line)
                    if progress:
                        progress_callback(progress)
            
            # 等待程序完成
            stdout, stderr = process.communicate(timeout=self.timeout)
            
            if process.returncode == 0:
                return True
            else:
                # 轉換失敗，刪除不完整的輸出檔案
                if output_path.exists():
                    output_path.unlink()
                return False
                
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            if output_path.exists():
                output_path.unlink()
            raise TimeoutError(f"轉換超時: {input_path}")
        except Exception as e:
            if output_path.exists():
                output_path.unlink()
            raise
    
    def stop(self) -> None:
        """停止轉換"""
        self._stop_event.set()
    
    def reset_stop(self) -> None:
        """重置停止標誌"""
        self._stop_event.clear()
    
    def convert_batch(
        self,
        input_files: list,
        output_folder: str,
        delete_original: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        批次轉換影片
        
        Args:
            input_files: 輸入檔案列表
            output_folder: 輸出資料夾
            delete_original: 是否刪除原始檔案
            progress_callback: 進度回調函數 (current, total, filename)
        
        Returns:
            轉換結果統計
        """
        self.reset_stop()
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        
        total = len(input_files)
        success = 0
        failed = 0
        failed_files = []
        
        for idx, input_file in enumerate(input_files):
            if self._stop_event.is_set():
                break
            
            if progress_callback:
                progress_callback(idx, total, str(input_file))
            
            try:
                # 生成輸出檔名
                seq = self.sequence_manager.get_next()
                output_filename = f"av{seq:04d}.mp4"
                output_path = output_folder / output_filename
                
                # 轉換
                if self.convert(str(input_file), str(output_path)):
                    success += 1
                    # 刪除原始檔案
                    if delete_original:
                        try:
                            Path(input_file).unlink()
                        except Exception as e:
                            print(f"警告: 無法刪除原始檔案 {input_file}: {e}")
                else:
                    failed += 1
                    failed_files.append(input_file)
                    
            except Exception as e:
                failed += 1
                failed_files.append((input_file, str(e)))
                print(f"錯誤: 轉換 {input_file} 失敗: {e}")
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "failed_files": failed_files
        }
