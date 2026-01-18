import os
import queue
import subprocess
import threading
from tkinter import Tk, filedialog, Text, Scrollbar, Frame, Label, Button, IntVar, OptionMenu
import time

SEQUENCE_FILE = "sequence_number.txt"
TIMEOUT = 300  # 秒

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Converter")
        self.create_widgets()
        self.process_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.update_log()

    def create_widgets(self):
        frame = Frame(self.root)
        frame.pack(fill="both", expand=True)

        self.text = Text(frame, wrap="word", state="disabled")
        self.text.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(frame, command=self.text.yview)
        scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=scrollbar.set)

        self.label = Label(self.root, text="Status: Idle")
        self.label.pack()

        button_frame = Frame(self.root)
        button_frame.pack(pady=10)

        Button(button_frame, text="Select Files", command=self.select_files).grid(row=0, column=0, padx=5)
        Button(button_frame, text="Select Output Folder", command=self.select_output_folder).grid(row=0, column=1, padx=5)
        Button(button_frame, text="Start Conversion", command=self.start_conversion).grid(row=0, column=2, padx=5)
        Button(button_frame, text="Stop Conversion", command=self.stop_conversion).grid(row=0, column=3, padx=5)

        self.threads_var = IntVar(value=1)
        OptionMenu(button_frame, self.threads_var, 1, 2, 4, 8).grid(row=0, column=4, padx=5)
        Label(button_frame, text="Threads").grid(row=0, column=5, padx=5)

    def log(self, message):
        self.log_queue.put(str(message))

    def update_log(self):
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.text.config(state="normal")
            self.text.insert("end", message + "\n")
            self.text.yview("end")
            self.text.config(state="disabled")
        self.root.after(100, self.update_log)

    def select_files(self):
        self.input_files = filedialog.askopenfilenames(filetypes=[("MP4 files", "*.mp4")])
        self.log(f"Selected files: {self.input_files}")

    def select_output_folder(self):
        self.output_folder = filedialog.askdirectory()
        self.log(f"Selected output folder: {self.output_folder}")

    def start_conversion(self):
        if not hasattr(self, 'input_files') or not self.input_files:
            self.log("No files selected.")
            return
        if not hasattr(self, 'output_folder') or not self.output_folder:
            self.log("No output folder selected.")
            return

        self.stop_event.clear()
        self.process_thread = threading.Thread(target=self.resize_and_convert_videos)
        self.process_thread.start()

    def stop_conversion(self):
        if self.process_thread and self.process_thread.is_alive():
            self.log("Stopping conversion...")
            self.stop_event.set()
            self.process_thread.join()
            self.label.config(text="Status: Conversion stopped.")
            self.process_thread = None

    def get_next_sequence_number(self):
        try:
            if os.path.exists(SEQUENCE_FILE):
                with open(SEQUENCE_FILE, "r") as f:
                    return int(f.read().strip())
        except Exception:
            pass
        return 1

    def increment_sequence_number(self, last_sequence):
        try:
            with open(SEQUENCE_FILE, "w") as f:
                f.write(str(last_sequence + 1))
        except Exception as e:
            self.log(f"Failed to update sequence number: {e}")

    def resize_and_convert_videos(self, width=1280, height=720, bitrate="1000k"):
        total_files = len(self.input_files)
        sequence_number = self.get_next_sequence_number()

        for idx, file_path in enumerate(self.input_files):
            if self.stop_event.is_set():
                self.log("Conversion stopped by user.")
                self.label.config(text="Status: Conversion stopped.")
                return
            try:
                self.log(f"Processing file {idx + 1}/{total_files}: {os.path.basename(file_path)}")
                self.label.config(text=f"Status: Converting ({idx + 1}/{total_files}) {os.path.basename(file_path)}")
                self.root.update_idletasks()

                output_filename = f"av{sequence_number:04d}.mp4"
                output_path = os.path.join(self.output_folder, output_filename)

                threads = min(self.threads_var.get(), os.cpu_count() or 1)

                command = [
                    "ffmpeg", "-threads", str(threads), "-i", file_path,
                    "-c:v", "h264_nvenc",
                    "-b:v", bitrate,
                    "-vf", f"scale={width}:{height}",
                    output_path
                ]

                self.log(f"Running command: {' '.join(command)}")
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')

                try:
                    stdout, stderr = process.communicate(timeout=TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    self.log(f"Timeout expired for {file_path}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                        self.log(f"Deleted incomplete output file {output_path}")
                    continue

                if stdout:
                    self.log(stdout)
                if stderr:
                    self.log(stderr)

                if process.returncode == 0:
                    self.log(f"Saved resized video to {output_path}")
                    try:
                        os.remove(file_path)
                        self.log(f"Deleted original file {file_path}")
                    except Exception as e:
                        self.log(f"Failed to delete original: {e}")
                    sequence_number += 1
                else:
                    self.log(f"Error processing {file_path}, return code: {process.returncode}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                        self.log(f"Deleted incomplete output file {output_path}")

            except FileNotFoundError:
                self.log("Error: ffmpeg not found. Ensure it is installed and in system PATH.")
                self.label.config(text="Status: ffmpeg not found.")
                return
            except Exception as e:
                self.log(f"Unexpected error: {e}")

        self.increment_sequence_number(sequence_number - 1)
        self.label.config(text="Status: Conversion completed.")

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()
