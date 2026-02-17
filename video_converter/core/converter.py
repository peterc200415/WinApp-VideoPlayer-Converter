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
from .encoder_detector import EncoderDetector, find_ffmpeg
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
        sequence_manager: Optional[SequenceManager] = None,
        preset: str = "medium",
        use_crf: bool = False,
        crf: int = 23
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
            preset: 編碼預設 (ultrafast, fast, medium, slow, veryslow)
            use_crf: 使用 CRF 模式而非 bitrate
            crf: CRF 值 (0-51, 較低 = 較高品質)
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
        self.preset = preset
        self.use_crf = use_crf
        self.crf = crf
        self._last_error: Optional[str] = None
    
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
        command = [find_ffmpeg(), "-threads", str(self.threads), "-y"]
        
        # 根據編碼器添加硬體加速參數 (必須在 -i 之前)
        if encoder in ["h264_nvenc", "hevc_nvenc"]:
            command.extend(["-hwaccel", "cuda"])
            command.extend(["-hwaccel_output_format", "cuda"])
        elif encoder in ["h264_qsv", "hevc_qsv"]:
            command.extend(["-init_hw_device", "qsv=hw"])
            command.extend(["-filter_hw_device", "hw"])
            command.extend(["-hwaccel", "qsv"])
            command.extend(["-hwaccel_output_format", "qsv"])
        
        command.extend(["-i", input_path])
        
        # 根據編碼器添加特定參數
        if encoder == "h264_nvenc":
            command.extend(["-c:v", "h264_nvenc"])
            command.extend(["-preset", self.preset])
            if self.use_crf:
                command.extend(["-crf", str(self.crf)])
            else:
                command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale_cuda={self.width}:{self.height}"])
        elif encoder == "hevc_nvenc":
            command.extend(["-c:v", "hevc_nvenc"])
            command.extend(["-preset", self.preset])
            if self.use_crf:
                command.extend(["-crf", str(self.crf)])
            else:
                command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale_cuda={self.width}:{self.height}"])
        elif encoder == "h264_qsv":
            command.extend(["-c:v", "h264_qsv"])
            command.extend(["-preset", self.preset])
            if self.use_crf:
                command.extend(["-crf", str(self.crf)])
            else:
                command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale_qsv=w={self.width}:h={self.height}"])
        elif encoder == "hevc_qsv":
            command.extend(["-c:v", "hevc_qsv"])
            command.extend(["-preset", self.preset])
            if self.use_crf:
                command.extend(["-crf", str(self.crf)])
            else:
                command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale_qsv=w={self.width}:h={self.height}"])
        elif encoder == "h264_amf":
            command.extend(["-c:v", "h264_amf"])
            command.extend(["-preset", self.preset])
            if self.use_crf:
                command.extend(["-crf", str(self.crf)])
            else:
                command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale={self.width}:{self.height}"])
        elif encoder == "hevc_amf":
            command.extend(["-c:v", "hevc_amf"])
            command.extend(["-preset", self.preset])
            if self.use_crf:
                command.extend(["-crf", str(self.crf)])
            else:
                command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale={self.width}:{self.height}"])
        else:  # libx264, libx265 或其他軟體編碼器
            command.extend(["-c:v", encoder])
            command.extend(["-preset", self.preset])
            if self.use_crf:
                command.extend(["-crf", str(self.crf)])
            else:
                command.extend(["-b:v", self.bitrate])
            command.extend(["-vf", f"scale={self.width}:{self.height}"])
        
        # 複製音效
        command.extend(["-c:a", "aac"])
        
        # 輸出檔案
        command.append(output_path)
        
        return command
    
    def _parse_progress(self, line: str, duration: float = 0) -> Optional[Dict[str, Any]]:
        """
        解析 FFmpeg 進度輸出
        
        Args:
            line: FFmpeg 輸出行
            duration: 影片總時長（秒）
        
        Returns:
            進度資訊字典或 None
        """
        result = {}
        
        # 解析 frame=xxx 格式
        frame_match = re.search(r'frame=\s*(\d+)', line)
        if frame_match:
            result["frame"] = int(frame_match.group(1))
        
        # 解析 time=hh:mm:ss.ms 格式
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            current_time = hours * 3600 + minutes * 60 + seconds
            result["time"] = current_time
            
            # 計算百分比
            if duration > 0:
                result["percent"] = min(100, (current_time / duration) * 100)
        
        if result:
            result["raw_line"] = line
            return result
        return None
    
    def get_video_duration(self, input_path: str) -> float:
        """取得影片時長（秒）"""
        import json
        ffprobe_path = find_ffmpeg().replace("ffmpeg", "ffprobe")
        
        try:
            result = subprocess.run(
                [
                    ffprobe_path or "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    input_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                encoding="utf-8"
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get("format", {}).get("duration", 0))
        except Exception:
            pass
        return 0
    
    def get_video_info(self, input_path: str) -> Dict[str, Any]:
        """取得影片資訊"""
        import json
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path.endswith("ffmpeg.exe"):
            ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
        elif ffmpeg_path == "ffmpeg":
            ffprobe_path = "ffprobe"
        else:
            ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")
        
        try:
            result = subprocess.run(
                [
                    ffprobe_path or "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    input_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                encoding="utf-8"
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                info = {"duration": 0, "width": 0, "height": 0, "format": "", "codec": ""}
                
                if "format" in data:
                    info["duration"] = float(data["format"].get("duration", 0))
                    info["format"] = data["format"].get("format_name", "")
                
                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        info["width"] = stream.get("width", 0)
                        info["height"] = stream.get("height", 0)
                        info["codec"] = stream.get("codec_name", "")
                        break
                
                return info
        except Exception:
            pass
        return {"duration": 0, "width": 0, "height": 0, "format": "", "codec": ""}
    
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
        
        # 取得影片資訊
        video_info = self.get_video_info(str(input_path))
        src_width = video_info.get("width", 0)
        src_height = video_info.get("height", 0)
        duration = video_info.get("duration", 0)
        
        # 如果解析度相同，直接複製檔案（不解碼）
        if src_width == self.width and src_height == self.height and self.width > 0 and self.height > 0:
            self._last_error = None
            try:
                import shutil
                shutil.copy2(str(input_path), str(output_path))
                self._last_error = "SKIPPED_SAME_RESOLUTION"

                progress = {
                    "percent": 100.0,
                    "time": float(duration) if duration else 0.0,
                    "video_info": video_info,
                    "raw_line": ""
                }
                if hasattr(self, "_file_progress_callback") and self._file_progress_callback:
                    self._file_progress_callback(progress)
                if progress_callback:
                    progress_callback(progress)
                return True
            except Exception as e:
                self._last_error = f"Copy failed: {e}"
                return False
        
        # 取得編碼器
        encoder = self._get_encoder()
        
        # 建立命令
        command = self._build_ffmpeg_command(
            str(input_path),
            str(output_path),
            encoder
        )
        
        self._last_error = None
        stderr_output = []
        
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
                    self._last_error = "轉換被使用者停止"
                    return False
                
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                stderr_output.append(line)

                should_report = bool(progress_callback) or (
                    hasattr(self, "_file_progress_callback") and bool(self._file_progress_callback)
                )
                if line and should_report:
                    progress = self._parse_progress(line, duration)
                    if progress:
                        progress["video_info"] = video_info
                        if hasattr(self, "_file_progress_callback") and self._file_progress_callback:
                            self._file_progress_callback(progress)
                        if progress_callback:
                            progress_callback(progress)
            
            # 等待程序完成
            stdout, stderr = process.communicate(timeout=self.timeout)
            
            if process.returncode == 0:
                return True
            else:
                # 收集錯誤訊息
                full_error = "".join(stderr_output) + stderr
                self._last_error = full_error
                
                # 轉換失敗，刪除不完整的輸出檔案
                if output_path.exists():
                    output_path.unlink()
                return False
                
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            if output_path.exists():
                output_path.unlink()
            self._last_error = f"轉換超時 ({self.timeout}秒)"
            raise TimeoutError(f"轉換超時: {input_path}")
        except Exception as e:
            self._last_error = str(e)
            if output_path.exists():
                output_path.unlink()
            raise
    
    def stop(self) -> None:
        """停止轉換"""
        self._stop_event.set()
    
    def reset_stop(self) -> None:
        """重置停止標誌"""
        self._stop_event.clear()
    
    def get_last_error(self) -> Optional[str]:
        """取得最後的錯誤訊息"""
        return self._last_error
    
    def convert_batch(
        self,
        input_files: list,
        output_folder: str,
        delete_original: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        file_progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        批次轉換影片
        
        Args:
            input_files: 輸入檔案列表
            output_folder: 輸出資料夾
            delete_original: 是否刪除原始檔案
            progress_callback: 進度回調函數 (current, total, filename)
            file_progress_callback: 檔案轉換進度回調 (包含 percent, time, video_info)
        
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
        
        # 儲存 file_progress_callback 以便在 convert 中使用
        self._file_progress_callback = file_progress_callback
        
        for idx, input_file in enumerate(input_files):
            if self._stop_event.is_set():
                break
            
            if progress_callback:
                progress_callback(idx, total, str(input_file))
            
            try:
                # 取得影片資訊（用於檔名）
                video_info = self.get_video_info(str(input_file))
                src_height = video_info.get("height", 0)
                
                # 使用輸出設定的高度作為檔名
                out_height = self.height
                
                # 生成輸出檔名
                seq = self.sequence_manager.get_next()
                if out_height > 0:
                    output_filename = f"av-{out_height}p-{seq:04d}.mp4"
                else:
                    output_filename = f"av-{seq:04d}.mp4"
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
