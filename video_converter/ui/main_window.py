"""
主視窗模組
提供現代化的圖形使用者介面
"""
import os
import queue
import threading
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Text, Scrollbar,
    filedialog, ttk, StringVar, IntVar, BooleanVar, messagebox
)
from typing import List, Optional, Callable

from ..core.converter import VideoConverter
from ..core.config import Config
from ..core.encoder_detector import EncoderDetector
from ..core.sequence_manager import SequenceManager
from ..utils.file_utils import format_file_size, get_video_files


class MainWindow:
    """主視窗類別"""
    
    def __init__(self, root: Tk):
        """
        初始化主視窗
        
        Args:
            root: Tkinter 根視窗
        """
        self.root = root
        self.root.title("影片轉換器 - Video Converter")
        self.root.geometry("900x700")
        
        # 初始化組件
        self.config = Config()
        self.encoder_detector = EncoderDetector()
        self.sequence_manager = SequenceManager(
            self.config.get("sequence_file", "sequence_number.txt")
        )
        self.converter: Optional[VideoConverter] = None
        
        # 狀態變數
        self.input_files: List[str] = []
        self.output_folder: StringVar = StringVar()
        self.is_converting = False
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        
        # 建立 UI
        self.create_widgets()
        self.update_log_display()
        
        # 載入配置
        self.load_config_to_ui()
    
    def create_widgets(self):
        """建立 UI 元件"""
        # 主框架
        main_frame = Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # 標題
        title_label = Label(
            main_frame,
            text="影片轉換器",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # 檔案選擇區域
        file_frame = ttk.LabelFrame(main_frame, text="檔案選擇", padding=10)
        file_frame.pack(fill="x", pady=5)
        
        Button(
            file_frame,
            text="選擇影片檔案",
            command=self.select_files
        ).pack(side="left", padx=5)
        
        Button(
            file_frame,
            text="選擇資料夾",
            command=self.select_folder
        ).pack(side="left", padx=5)
        
        self.file_count_label = Label(
            file_frame,
            text="已選擇: 0 個檔案",
            fg="gray"
        )
        self.file_count_label.pack(side="left", padx=10)
        
        # 輸出資料夾選擇
        output_frame = ttk.LabelFrame(main_frame, text="輸出設定", padding=10)
        output_frame.pack(fill="x", pady=5)
        
        Button(
            output_frame,
            text="選擇輸出資料夾",
            command=self.select_output_folder
        ).pack(side="left", padx=5)
        
        self.output_label = Label(
            output_frame,
            textvariable=self.output_folder,
            fg="gray"
        )
        self.output_label.pack(side="left", padx=10)
        
        # 轉換設定區域
        settings_frame = ttk.LabelFrame(main_frame, text="轉換設定", padding=10)
        settings_frame.pack(fill="x", pady=5)
        
        # 解析度設定
        res_frame = Frame(settings_frame)
        res_frame.pack(fill="x", pady=2)
        
        Label(res_frame, text="寬度:").pack(side="left", padx=5)
        self.width_var = StringVar(value=str(self.config.get("width", 1280)))
        width_entry = ttk.Entry(res_frame, textvariable=self.width_var, width=10)
        width_entry.pack(side="left", padx=5)
        
        Label(res_frame, text="高度:").pack(side="left", padx=5)
        self.height_var = StringVar(value=str(self.config.get("height", 720)))
        height_entry = ttk.Entry(res_frame, textvariable=self.height_var, width=10)
        height_entry.pack(side="left", padx=5)
        
        # 位元率設定
        bitrate_frame = Frame(settings_frame)
        bitrate_frame.pack(fill="x", pady=2)
        
        Label(bitrate_frame, text="位元率:").pack(side="left", padx=5)
        self.bitrate_var = StringVar(value=self.config.get("bitrate", "1000k"))
        bitrate_entry = ttk.Entry(bitrate_frame, textvariable=self.bitrate_var, width=10)
        bitrate_entry.pack(side="left", padx=5)
        
        # 編碼器選擇
        encoder_frame = Frame(settings_frame)
        encoder_frame.pack(fill="x", pady=2)
        
        Label(encoder_frame, text="編碼器:").pack(side="left", padx=5)
        self.encoder_var = StringVar(value=self.config.get("encoder", "auto"))
        encoder_combo = ttk.Combobox(
            encoder_frame,
            textvariable=self.encoder_var,
            values=["auto"] + self.encoder_detector.detect_available_encoders(),
            state="readonly",
            width=15
        )
        encoder_combo.pack(side="left", padx=5)
        
        # 執行緒數
        threads_frame = Frame(settings_frame)
        threads_frame.pack(fill="x", pady=2)
        
        Label(threads_frame, text="執行緒數:").pack(side="left", padx=5)
        self.threads_var = IntVar(value=self.config.get("threads", 1))
        threads_combo = ttk.Combobox(
            threads_frame,
            textvariable=self.threads_var,
            values=[1, 2, 4, 8],
            state="readonly",
            width=10
        )
        threads_combo.pack(side="left", padx=5)
        
        # 選項
        options_frame = Frame(settings_frame)
        options_frame.pack(fill="x", pady=2)
        
        self.delete_original_var = BooleanVar(
            value=self.config.get("delete_original", True)
        )
        ttk.Checkbutton(
            options_frame,
            text="轉換後刪除原始檔案",
            variable=self.delete_original_var
        ).pack(side="left", padx=5)
        
        # 控制按鈕區域
        control_frame = Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        self.start_button = Button(
            control_frame,
            text="開始轉換",
            command=self.start_conversion,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5
        )
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = Button(
            control_frame,
            text="停止轉換",
            command=self.stop_conversion,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)
        
        # 進度條
        self.progress_var = StringVar(value="就緒")
        self.progress_label = Label(
            control_frame,
            textvariable=self.progress_var,
            font=("Arial", 9)
        )
        self.progress_label.pack(side="left", padx=10)
        
        # 進度條
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode="determinate",
            maximum=100
        )
        self.progress_bar.pack(fill="x", pady=5)
        
        # 日誌顯示區域
        log_frame = ttk.LabelFrame(main_frame, text="日誌", padding=5)
        log_frame.pack(fill="both", expand=True, pady=5)
        
        # 日誌文字區域
        log_text_frame = Frame(log_frame)
        log_text_frame.pack(fill="both", expand=True)
        
        self.log_text = Text(
            log_text_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 9)
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        
        log_scrollbar = Scrollbar(log_text_frame, command=self.log_text.yview)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # 狀態列
        self.status_var = StringVar(value="就緒")
        status_label = Label(
            main_frame,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padx=5
        )
        status_label.pack(fill="x", pady=(5, 0))
    
    def log(self, message: str, level: str = "INFO"):
        """
        記錄日誌訊息
        
        Args:
            message: 訊息內容
            level: 日誌級別
        """
        self.log_queue.put(f"[{level}] {message}")
    
    def update_log_display(self):
        """更新日誌顯示"""
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_log_display)
    
    def select_files(self):
        """選擇影片檔案"""
        files = filedialog.askopenfilenames(
            title="選擇影片檔案",
            filetypes=[
                ("影片檔案", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                ("所有檔案", "*.*")
            ]
        )
        if files:
            self.input_files = list(files)
            self.file_count_label.config(
                text=f"已選擇: {len(self.input_files)} 個檔案"
            )
            self.log(f"已選擇 {len(self.input_files)} 個檔案")
    
    def select_folder(self):
        """選擇資料夾（批次處理）"""
        folder = filedialog.askdirectory(title="選擇包含影片的資料夾")
        if folder:
            video_files = get_video_files(folder)
            if video_files:
                self.input_files = [str(f) for f in video_files]
                self.file_count_label.config(
                    text=f"已選擇: {len(self.input_files)} 個檔案"
                )
                self.log(f"從資料夾找到 {len(self.input_files)} 個影片檔案")
            else:
                messagebox.showwarning("警告", "該資料夾中沒有找到影片檔案")
    
    def select_output_folder(self):
        """選擇輸出資料夾"""
        folder = filedialog.askdirectory(title="選擇輸出資料夾")
        if folder:
            self.output_folder.set(folder)
            self.log(f"輸出資料夾: {folder}")
    
    def load_config_to_ui(self):
        """載入配置到 UI"""
        # 配置已在 create_widgets 中載入
        pass
    
    def save_ui_to_config(self):
        """儲存 UI 設定到配置"""
        try:
            self.config.set("width", int(self.width_var.get()))
            self.config.set("height", int(self.height_var.get()))
            self.config.set("bitrate", self.bitrate_var.get())
            self.config.set("encoder", self.encoder_var.get())
            self.config.set("threads", self.threads_var.get())
            self.config.set("delete_original", self.delete_original_var.get())
            self.config.save_config()
        except ValueError as e:
            self.log(f"配置錯誤: {e}", "ERROR")
    
    def start_conversion(self):
        """開始轉換"""
        if not self.input_files:
            messagebox.showwarning("警告", "請先選擇要轉換的檔案")
            return
        
        if not self.output_folder.get():
            messagebox.showwarning("警告", "請先選擇輸出資料夾")
            return
        
        # 儲存設定
        self.save_ui_to_config()
        
        # 更新 UI 狀態
        self.is_converting = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.stop_event.clear()
        
        # 建立轉換器
        self.converter = VideoConverter(
            encoder=self.encoder_var.get(),
            width=int(self.width_var.get()),
            height=int(self.height_var.get()),
            bitrate=self.bitrate_var.get(),
            threads=self.threads_var.get(),
            timeout=self.config.get("timeout", 300),
            sequence_manager=self.sequence_manager
        )
        
        # 啟動轉換執行緒
        thread = threading.Thread(target=self.convert_thread)
        thread.daemon = True
        thread.start()
    
    def convert_thread(self):
        """轉換執行緒"""
        try:
            self.log("開始批次轉換...")
            self.status_var.set("轉換中...")
            
            def progress_callback(current: int, total: int, filename: str):
                """進度回調"""
                progress = int((current / total) * 100) if total > 0 else 0
                self.progress_bar["value"] = progress
                self.progress_var.set(
                    f"處理中 ({current}/{total}): {Path(filename).name}"
                )
                self.log(f"[{current}/{total}] 處理: {Path(filename).name}")
            
            # 執行批次轉換
            result = self.converter.convert_batch(
                self.input_files,
                self.output_folder.get(),
                delete_original=self.delete_original_var.get(),
                progress_callback=progress_callback
            )
            
            # 顯示結果
            self.progress_bar["value"] = 100
            self.progress_var.set("轉換完成")
            self.status_var.set(
                f"完成: 成功 {result['success']}/{result['total']}, "
                f"失敗 {result['failed']}"
            )
            
            self.log(f"轉換完成: 成功 {result['success']}, 失敗 {result['failed']}")
            
            if result['failed'] > 0:
                self.log("失敗的檔案:", "WARNING")
                for item in result['failed_files']:
                    if isinstance(item, tuple):
                        self.log(f"  - {item[0]}: {item[1]}", "ERROR")
                    else:
                        self.log(f"  - {item}", "ERROR")
            
            messagebox.showinfo(
                "轉換完成",
                f"轉換完成！\n成功: {result['success']}\n失敗: {result['failed']}"
            )
            
        except Exception as e:
            self.log(f"轉換錯誤: {e}", "ERROR")
            messagebox.showerror("錯誤", f"轉換過程中發生錯誤: {e}")
        finally:
            # 重置 UI 狀態
            self.is_converting = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.progress_bar["value"] = 0
    
    def stop_conversion(self):
        """停止轉換"""
        if self.converter:
            self.converter.stop()
            self.stop_event.set()
            self.log("正在停止轉換...", "WARNING")
            self.status_var.set("正在停止...")
    
    def run(self):
        """執行主迴圈"""
        self.root.mainloop()
