# Hướng Dẫn Chạy Hệ Thống Giám Sát Giấy Vệ Sinh Sân Bay

Toàn bộ mã nguồn server, giao diện web và trình mô phỏng nằm trong thư mục `server/`.

## 1. Cài đặt thư viện
Mở terminal và di chuyển vào thư mục `server`:
```bash
cd server
pip install -r requirements.txt
```

## 2. Chạy Server
Khởi chạy máy chủ FastAPI (hệ thống tự tạo database `app.db`, tạo tài khoản `admin / admin123`, khởi tạo 2 Terminal T2, T3 cùng các tầng và tự sinh bản đồ PDF mẫu):
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Truy cập giao diện Web tại: **http://localhost:8000**
- Tài khoản quản trị mặc định: `admin` / `admin123`
- *Lưu ý*: Lần đầu đăng nhập hệ thống sẽ yêu cầu đổi mật khẩu mới.

---

## 3. Chạy Trình Mô Phỏng Gateway (Simulator)
Mở một cửa sổ terminal khác (trong thư mục `server/`) để chạy trình mô phỏng gửi dữ liệu từ các Gateway ESP32:

- **Chạy lần đầu (kèm tạo dữ liệu mẫu ~3 toilet mỗi tầng):**
```bash
cd server
python simulator.py --seed
```

- **Chạy thông thường (mặc định gửi mỗi 5 giây):**
```bash
python simulator.py --server http://127.0.0.1:8000 --api-key airport-gateway-secret-api-key-2026 --interval 5
```
