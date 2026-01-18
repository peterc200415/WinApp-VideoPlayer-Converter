"""
影片轉換器主程式入口
"""
import sys
from tkinter import Tk, messagebox

from video_converter.ui.main_window import MainWindow
from video_converter.core.encoder_detector import EncoderDetector


def check_requirements():
    """檢查系統需求"""
    detector = EncoderDetector()
    
    if not detector.check_ffmpeg():
        messagebox.showerror(
            "錯誤",
            "未找到 FFmpeg！\n\n"
            "請確保 FFmpeg 已安裝並在系統 PATH 中。\n"
            "下載: https://ffmpeg.org/download.html"
        )
        return False
    
    return True


def main():
    """主函數"""
    # 檢查需求
    if not check_requirements():
        sys.exit(1)
    
    # 建立主視窗
    root = Tk()
    app = MainWindow(root)
    
    # 執行應用程式
    app.run()


if __name__ == "__main__":
    main()
