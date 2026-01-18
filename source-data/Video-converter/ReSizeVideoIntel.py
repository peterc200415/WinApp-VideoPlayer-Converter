import cv2

# 打開影片文件
cap = cv2.VideoCapture('av0754.mp4')

# 取得影片的幀寬和幀高
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

# 設定新的幀寬和幀高
new_width = 640
new_height = 360

# 定義影片寫入器並指定輸出的影片參數
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output_video.mp4', fourcc, fps, (new_width, new_height))

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 調整每一幀的大小
    resized_frame = cv2.resize(frame, (new_width, new_height))

    # 將幀寫入輸出文件
    out.write(resized_frame)

# 釋放資源
cap.release()
out.release()
cv2.destroyAllWindows()
