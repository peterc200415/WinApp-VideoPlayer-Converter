import os
from tkinter import Tk, filedialog
import subprocess

# 文件序号保存路径
SEQUENCE_FILE = "sequence_number.txt"

def select_files():
    # 打开文件选择对话框，允许多选
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(filetypes=[("MP4 files", "*.mp4")])
    return list(file_paths)

def select_output_folder():
    # 打开文件夹选择对话框
    root = Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    return folder_path

def get_next_sequence_number():
    if os.path.exists(SEQUENCE_FILE):
        with open(SEQUENCE_FILE, "r") as file:
            sequence_number = int(file.read().strip())
    else:
        sequence_number = 1
    return sequence_number

def increment_sequence_number(sequence_number):
    with open(SEQUENCE_FILE, "w") as file:
        file.write(str(sequence_number + 1))

def resize_and_convert_videos(input_files, output_folder, width=1280, height=720, bitrate="1000k"):
    for file_path in input_files:
        try:
            sequence_number = get_next_sequence_number()
            output_filename = f"av{sequence_number:04d}.mp4"
            output_path = os.path.join(output_folder, output_filename)
            command = [
                'ffmpeg', '-init_hw_device', 'qsv=hw', '-filter_hw_device', 'hw',
                '-hwaccel', 'qsv', '-c:v', 'h264_qsv', '-i', file_path,
                '-vf', f'scale_qsv=w={width}:h={height}', '-b:v', bitrate,
                '-c:v', 'h264_qsv', output_path
            ]
            print("Running command:", " ".join(command))
            result = subprocess.run(command, capture_output=True, text=True)
            print(result.stdout)
            print(result.stderr)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command)
            print(f"Saved resized video to {output_path}")
            # 删除原始文件
            os.remove(file_path)
            print(f"Deleted original file {file_path}")
            # 更新序号
            increment_sequence_number(sequence_number)
        except subprocess.CalledProcessError as e:
            print(f"Error processing {file_path} with QSV, trying software encoding: {e}")
            try:
                command = [
                    'ffmpeg', '-i', file_path,
                    '-c:v', 'libx264',
                    '-b:v', bitrate,
                    '-vf', f'scale={width}:{height}',
                    output_path
                ]
                result = subprocess.run(command, capture_output=True, text=True)
                print(result.stdout)
                print(result.stderr)
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, command)
                print(f"Saved resized video to {output_path} using software encoding")
                # 删除原始文件
                os.remove(file_path)
                print(f"Deleted original file {file_path}")
                # 更新序号
                increment_sequence_number(sequence_number)
            except subprocess.CalledProcessError as e:
                print(f"Error processing {file_path} with software encoding: {e}")
        except OSError as e:
            print(f"Error deleting {file_path}: {e}")

if __name__ == "__main__":
    input_files = select_files()
    if not input_files:
        print("No files selected. Exiting.")
        exit()

    output_folder = select_output_folder()
    if not output_folder:
        print("No output folder selected. Exiting.")
        exit()

    resize_and_convert_videos(input_files, output_folder)
    print("All videos have been resized, saved, and original files deleted.")
