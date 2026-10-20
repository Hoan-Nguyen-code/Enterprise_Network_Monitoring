# Enterprise Network Monitoring

Hệ thống giám sát mạng doanh nghiệp mô phỏng trên **GNS3**, sử dụng **Python + Netmiko** để thu thập thông số router Cisco, lưu CSV, phát hiện cảnh báo, hiển thị **Flask Dashboard** và xuất báo cáo phân tích bằng **Pandas, Matplotlib, OpenPyXL**.

> **Lưu ý:** Tài liệu ghi lại môi trường lab đã sử dụng. Địa chỉ IP, tên interface, mật khẩu và đường dẫn có thể phải thay đổi tùy máy. Không đưa mật khẩu thật hoặc file chứa bí mật lên GitHub.

## 1. Sơ đồ mạng

```text
             VMware VMnet8 (NAT): 192.168.126.0/24
                              |
                    GNS3 Cloud / VMnet8
                         /           \
          Fa0/1 192.168.126.10      Fa0/1 192.168.126.11
                       R1 ----------- R2
             Fa0/0 10.0.12.1/30   Fa0/0 10.0.12.2/30
                         |
              Ubuntu VM (VMware NAT)
              ví dụ: 192.168.126.128
              Python monitoring / Flask
```

- Router: Cisco **c3660**, IOS **12.4** trên GNS3.
- R1 ↔ R2: kết nối qua `FastEthernet0/0`.
- R1 và R2 kết nối mạng quản trị VMnet8 qua `FastEthernet0/1` (bố trí Cloud/switch tương ứng với topology thực tế).
- Ubuntu VM dùng **NAT** cùng VMnet8 để SSH đến hai router.

## 2. Chuẩn bị

- Windows cài GNS3 và VMware Workstation.
- GNS3 có router Cisco c3660 và IOS tương thích (cần sử dụng IOS có quyền hợp lệ; **không commit IOS image**).
- Ubuntu VM có Python, pip, SSH client; có thể dùng VS Code.
- Trên VMware, kiểm tra NAT/VMnet8 và dải mạng thực tế trước khi đặt IP.

## 3. Tạo topology trên GNS3

1. Tạo project `Enterprise_Network_Monitoring`.
2. Kéo hai router c3660 vào project, đổi tên thành `R1`, `R2`.
3. Kết nối `R1 Fa0/0` ↔ `R2 Fa0/0`.
4. Kết nối `Fa0/1` của hai router vào mạng quản trị VMnet8 qua Cloud/switch phù hợp. Nếu dùng GNS3 trên Windows, chọn đúng adapter **VMware Network Adapter VMnet8** cho Cloud.
5. Nhấn **Start All Nodes** và mở Console của từng router.

> Nếu `Fa0/1` trên máy của bạn không tồn tại hoặc sơ đồ cổng khác, kiểm tra `show ip interface brief` rồi thay tên interface tương ứng.

## 4. Cấu hình Cisco R1

```cisco
 enable
 configure terminal
 hostname R1
 ip domain-name lab.local
 username admin privilege 15 secret <MAT_KHAU_MANH_CUA_BAN>
 interface FastEthernet0/0
  ip address 10.0.12.1 255.255.255.252
  no shutdown
 exit
 interface FastEthernet0/1
  ip address 192.168.126.10 255.255.255.0
  no shutdown
 exit
 crypto key generate rsa
 ! Nếu được hỏi modulus, nhập 1024 hoặc mức được IOS hỗ trợ
 ip ssh version 2
 line vty 0 4
  login local
  transport input ssh
 exit
 end
 copy running-config startup-config
```

## 5. Cấu hình Cisco R2

```cisco
 enable
 configure terminal
 hostname R2
 ip domain-name lab.local
 username admin privilege 15 secret <MAT_KHAU_MANH_CUA_BAN>
 interface FastEthernet0/0
  ip address 10.0.12.2 255.255.255.252
  no shutdown
 exit
 interface FastEthernet0/1
  ip address 192.168.126.11 255.255.255.0
  no shutdown
 exit
 crypto key generate rsa
 ! Nếu được hỏi modulus, nhập 1024 hoặc mức được IOS hỗ trợ
 ip ssh version 2
 line vty 0 4
  login local
  transport input ssh
 exit
 end
 copy running-config startup-config
```

**Chú ý:** Dòng `<MAT_KHAU_MANH_CUA_BAN>` là placeholder, phải thay bằng mật khẩu của bạn; không gõ nguyên dấu `< >` vào Cisco. Trên IOS cũ, độ dài RSA có thể bị giới hạn; đây là môi trường lab, **không dùng thuật toán SSH cũ hoặc RSA 1024-bit cho hệ thống production**.

### Kiểm tra Cisco

Trên cả hai router:

```cisco
show ip interface brief
show ip ssh
show crypto key mypubkey rsa
show running-config
show startup-config
```

Mong đợi `Fa0/0`, `Fa0/1` ở trạng thái `up/up` khi kết nối đúng; `show ip ssh` báo SSH enabled. Nhớ `copy running-config startup-config` trên **cả R1 và R2** và lưu project GNS3 bằng `Ctrl+S` trước khi thoát.

## 6. Chuẩn bị Ubuntu VM

Kiểm tra IP và kết nối:

```bash
ip -br addr
ping -c 4 192.168.126.10
ping -c 4 192.168.126.11
```

Nếu không ping được: kiểm tra NAT VMnet8, GNS3 Cloud, IP/subnet, `no shutdown` và kết nối cáp. Để thử SSH:

```bash
ssh admin@192.168.126.10
ssh admin@192.168.126.11
```

IOS 12.4 có thể dùng thuật toán SSH cũ khiến OpenSSH hiện đại từ chối kết nối. Chỉ trong **lab cô lập**, có thể cần cấu hình tương thích SSH phía client. Không giảm bảo mật SSH của máy dùng thực tế.

## 7. Thiết lập Python

Trong Ubuntu:

```bash
cd ~/Enterprise_Network_Monitoring
python3 -m venv ~/mnw-venv
~/mnw-venv/bin/python -m pip install --upgrade pip
~/mnw-venv/bin/python -m pip install netmiko==4.8.0 paramiko==3.5.1 flask pandas matplotlib openpyxl
```

Trong lab đã dùng **Netmiko 4.8.0 + Paramiko 3.5.1** để tương thích SSH của IOS cũ. Nếu project có `requirements.txt`, ưu tiên cài từ file đó:

```bash
~/mnw-venv/bin/python -m pip install -r requirements.txt
```

### Cấu hình thiết bị

Chỉnh `config/devices.json` theo đúng cấu trúc file đang có trong project, sử dụng IP:

| Router | IP quản trị | SSH user |
|---|---|---|
| R1 | `192.168.126.10` | `admin` |
| R2 | `192.168.126.11` | `admin` |

Các ngưỡng giám sát đã dùng: chu kỳ **30 giây**, CPU **80%**, RAM **85%**, traffic **80 Mbps**, errors **10**. Tên khóa JSON phải khớp với code thực tế; **không thay cấu trúc file chỉ theo bảng mô tả này**. Nếu code nhập mật khẩu bằng `getpass`, hãy nhập khi chương trình hỏi và không lưu mật khẩu trong repository.

## 8. Chạy hệ thống

### Thu thập dữ liệu

```bash
cd ~/Enterprise_Network_Monitoring
~/mnw-venv/bin/python src/main.py
```

Chương trình dùng Netmiko SSH đến R1/R2, thu thập CPU, RAM, trạng thái interface, bộ đếm RX/TX và lỗi, sau đó ghi dữ liệu để làm báo cáo. Nhấn `Ctrl+C` để dừng khi cần.

### Dashboard Flask

Mở terminal khác:

```bash
cd ~/Enterprise_Network_Monitoring
~/mnw-venv/bin/python src/dashboard.py
```

Mở URL Flask được in trong terminal (thường là `http://127.0.0.1:5000`, nếu ứng dụng sử dụng cổng mặc định). Dashboard hiển thị số liệu đã thu thập; cần chạy `main.py` để cập nhật dữ liệu.

### Analytics / Excel

```bash
cd ~/Enterprise_Network_Monitoring
~/mnw-venv/bin/python src/analytics.py
```

Phân tích CSV bằng Pandas, tạo biểu đồ Matplotlib và xuất Excel bằng OpenPyXL. Đường dẫn, tên file đầu ra phụ thuộc vào phiên bản `analytics.py` hiện tại; kiểm tra thư mục `reports/` sau khi chạy.

## 9. Các thành phần dự án

```text
Enterprise_Network_Monitoring/
├── config/
│   └── devices.json
├── src/
│   ├── main.py          # Vòng lặp giám sát
│   ├── monitor.py       # Thu thập thông số qua Netmiko
│   ├── alerts.py        # Phát hiện cảnh báo
│   ├── reports.py       # CSV / HTML report
│   ├── dashboard.py     # Flask Dashboard
│   └── analytics.py     # Pandas / Matplotlib / OpenPyXL
├── templates/
│   └── dashboard.html
├── data/                 # CSV phát sinh khi chạy
├── logs/                 # Log phát sinh khi chạy
└── reports/              # Báo cáo và biểu đồ phát sinh
```

Cấu trúc này mô tả các thành phần đã xây dựng; một số thư mục đầu ra chỉ xuất hiện sau khi chạy chương trình.

## 10. Ý nghĩa chỉ số

- **CPU (%):** mức sử dụng CPU của router.
- **RAM (%):** mức sử dụng bộ nhớ.
- **Interface status:** trạng thái `up/down` của cổng.
- **RX:** lưu lượng dữ liệu **nhận vào** interface.
- **TX:** lưu lượng dữ liệu **gửi ra** interface.
- **Errors:** số lỗi giao tiếp thu thập được từ interface.

Tốc độ RX/TX được tính từ chênh lệch bộ đếm byte giữa hai lần đo: `Mbps = (delta_bytes × 8) / (delta_seconds × 1_000_000)`.

## 11. Xử lý lỗi thường gặp

| Triệu chứng | Cách kiểm tra |
|---|---|
| Ping router thất bại | VMnet8, Cloud, địa chỉ IP, subnet, `no shutdown` |
| `show ip ssh` báo Disabled | Domain name, RSA key, `ip ssh version 2`, VTY |
| SSH bị từ chối thuật toán | IOS 12.4 dùng SSH cũ; kiểm tra tương thích Netmiko/Paramiko trong lab |
| Mất cấu hình khi mở lại | `copy running-config startup-config`, lưu project GNS3, kiểm tra RSA key |
| Dashboard không có dữ liệu | Chạy `src/main.py`, kiểm tra CSV và đường dẫn đọc trong dashboard |
| RX/TX bằng 0 | Chưa đủ hai lần lấy mẫu hoặc không có lưu lượng phát sinh |
| Analytics không xuất file | Kiểm tra CSV đầu vào, thư viện và traceback trong terminal |

## 12. Đưa dự án lên GitHub

Tạo file `.gitignore` ở thư mục gốc, ví dụ:

```gitignore
.venv/
venv/
__pycache__/
*.py[cod]
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
*.log
logs/
reports/
data/*.csv
.gns3project/
*.image
*.bin
*.qcow2
*.vmdk
.DS_Store
```

**Kiểm tra trước khi commit:** Nếu `config/devices.json` có password/token thì phải loại bỏ bí mật trước khi đẩy. Nếu từng commit bí mật, xóa ở commit mới là chưa đủ; cần thay mật khẩu và xử lý lịch sử Git.

```bash
cd ~/Enterprise_Network_Monitoring
git init
git branch -M main
git add .
git status
git commit -m "Initial commit: enterprise network monitoring"
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

Thay `USERNAME/REPO` bằng tên repository thật. Nếu đã có Git repository hoặc remote `origin`, **không chạy lại** `git init`/`git remote add origin`; kiểm tra `git remote -v` trước. GitHub có thể yêu cầu đăng nhập qua browser hoặc token/SSH key, không dùng mật khẩu GitHub trực tiếp.

## 13. Hướng phát triển

- Cảnh báo qua Telegram/email.
- Lưu dữ liệu vào PostgreSQL/SQLite thay cho CSV.
- Phân quyền tài khoản Dashboard.
- Theo dõi thêm router/switch và thống kê lịch sử dài hạn.
- Container hóa ứng dụng và bổ sung kiểm thử tự động.

---

**Môi trường:** GNS3 · Cisco IOS 12.4 · VMware Ubuntu · Python · Netmiko · Flask · Pandas · Matplotlib · OpenPyXL.
