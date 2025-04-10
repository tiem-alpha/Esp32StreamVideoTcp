import socket
import cv2
import numpy as np
import time
import struct
import sys

StreamCamera = 0




# Chuyển đổi từ BGR thành RGB565
def bgr_to_rgb565(frame):
    # Tách các kênh
    b, g, r = cv2.split(frame)
    
    # Chuyển đổi sang RGB565 (5 bit R, 6 bit G, 5 bit B)
    r = (r >> 3).astype(np.uint16) << 11
    g = (g >> 2).astype(np.uint16) << 5
    b = (b >> 3).astype(np.uint16)
    
    # Kết hợp thành RGB565
    rgb565 = r | g | b
    
    # Chuyển thành mảng byte
    return rgb565.astype(np.uint16)


# Giới hạn tốc độ khung hình
fps_target = 15
frame_time = 1.0 / fps_target

def StreamFromCamera():
        print("Stream camera "); 
        cap = cv2.VideoCapture(0)  # 0 cho camera, hoặc đường dẫn video
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 240)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        # Cấu hình kết nối
        esp32_ip = input("Nhập địa chỉ IP của ESP32: ")
        esp32_port = 8888
        
        # Tạo socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            while cap.isOpened():
                start_time = time.time()
                
                ret, frame = cap.read()
                if not ret:
                    print("Không thể đọc frame từ camera")
                    break
                    
                # Resize frame thành 240x240
                frame = cv2.resize(frame, (240, 240))
                
                # Tùy chọn: Áp dụng mask tròn cho màn hình GC9A01
                mask = np.zeros_like(frame)
                cv2.circle(mask, (120, 120), 120, (255, 255, 255), -1)
                frame = cv2.bitwise_and(frame, mask)
                
                # Chuyển đổi từ BGR thành RGB565
                rgb565_data = bgr_to_rgb565(frame)
                
                # Gửi dữ liệu RGB565
                # print(len(rgb565_data.tobytes()))
                sock.sendall(rgb565_data.tobytes())
                
                # Hiển thị frame gốc trên máy tính (tùy chọn)
                # cv2.imshow('Frame gửi đi', frame)
                
                # Nhấn 'q' để thoát
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
                # Điều chỉnh tốc độ khung hình
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_time - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # In FPS thực tế
                actual_fps = 1.0 / (time.time() - start_time)
                print(f"FPS: {actual_fps:.1f}", end="\r")
            
        finally:
            cap.release()
            cv2.destroyAllWindows()
            sock.close()
            print("\nĐã đóng kết nối")


def crop_to_square(frame):
    """Cắt frame thành hình vuông từ trung tâm"""
    height, width = frame.shape[0], frame.shape[1]
    
    if width > height:
        # Nếu chiều rộng lớn hơn chiều cao, cắt từ giữa theo chiều rộng
        left = int((width - height) / 2)
        right = left + height
        return frame[:, left:right]
    elif height > width:
        # Nếu chiều cao lớn hơn chiều rộng, cắt từ giữa theo chiều cao
        top = int((height - width) / 2)
        bottom = top + width
        return frame[top:bottom, :]
    else:
        # Nếu đã là hình vuông, giữ nguyên
        return frame
    
def StreamMP4File(filePath):
       
        video_path = filePath
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"Không thể mở video: {video_path}")
                return
        except Exception as e:
            print(f"Lỗi khi mở video: {e}")
            return
        
        # Cấu hình kết nối
        esp32_ip = input("Nhập địa chỉ IP của ESP32: ")
        esp32_port = 8888
        
        # Tạo socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Kết nối đến ESP32
            print(f"Đang kết nối đến ESP32 ({esp32_ip}:{esp32_port})...")
            sock.connect((esp32_ip, esp32_port))
            print("Đã kết nối thành công")
            
            # Thời gian đọc frame cuối cùng
            last_frame_time = time.time()
            fps_target = cap.get(cv2.CAP_PROP_FPS)
            frame_delay = 1.0 / fps_target if fps_target > 0 else 0.033  # 30fps mặc định
            
            # Đọc và xử lý video
            while True:
                # Đọc frame từ video
                ret, frame = cap.read()
                if not ret:
                    print("Đã đọc hết video hoặc có lỗi khi đọc frame")
                    # Quay lại frame đầu tiên để loop video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Điều chỉnh tốc độ frame
                current_time = time.time()
                elapsed = current_time - last_frame_time
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)
                frame_square = crop_to_square(frame)
                cv2.imshow('Stream to ESP32', frame_square)
                # print(frame_square.shape)
                # Resize frame cho màn hình 240x240
                frame_resized = cv2.resize(frame_square, (240, 240))
                # print(frame_resized.shape)
                # Hiển thị frame trên máy tính
                # cv2.imshow('Stream to ESP32', frame_resized)
                
                # Chuyển đổi frame sang RGB565
                frame_rgb565  = bgr_to_rgb565(frame_resized)
                
                # Gửi dữ liệu đến ESP32
                try:
                    sock.sendall(frame_rgb565.tobytes())
                except Exception as e:
                    print(f"Lỗi khi gửi dữ liệu: {e}")
                    break
                
                last_frame_time = time.time()
                
                # Thoát nếu nhấn 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        except Exception as e:
            print(f"Lỗi: {e}")
        
        finally:
            # Dọn dẹp
            cap.release()
            cv2.destroyAllWindows()
            sock.close()
            print("Đã đóng kết nối")

def main():
    # Mở video
    if StreamCamera ==1 :
        StreamFromCamera()
    else:
        StreamMP4File("download.mp4")
        

if __name__ == "__main__":
    main()