# Dodge the Magma

Một game arcade nhỏ: người chơi né magma rơi từ trên xuống, nhặt coin, dùng
dash và shield để sống lâu nhất có thể.

Repo này hiện có **2 bản**:

| Thư mục | Ngôn ngữ / Engine | Trạng thái |
|---|---|---|
| [`py version/`](py%20version) | Python + `pygame-ce` | Bản gốc, đầy đủ tính năng |
| [`cpp_version/`](cpp_version) | C++ + `raylib` | Đang port từ bản Python, chưa đầy đủ 100% |

> Bản C++ đang trong quá trình port sang từ bản Python nên vẫn giữ song song
> cả hai — chưa xoá bản Python vì còn vài phần chưa port xong hoặc để tương thích trên 1 số máy

## Features (chung cho cả 2 bản)
- Di chuyển trái/phải mượt với cảm giác quán tính nhẹ.
- Jump có `double jump`, `variable jump`, `jump buffer`, và `coyote time`.
- Dash có cooldown và bật nảy khi chạm tường.
- Shield có thời gian hoạt động, cooldown, và hiệu ứng hình ảnh.
- Magma và coin spawn theo pattern thay vì chỉ random đơn giản.
- Có `shop`, `game over menu`, save/load coin và upgrade.
- Có startup screen để chọn fullscreen, preset resolution, hoặc custom resolution.
- Có `pause menu` bằng `ESC` khi đang chơi.
- Có cheat console (`` ` `` để mở).

## Bản Python (`py version/`)
Bản gốc, đầy đủ tính năng, chạy bằng `pygame-ce`.

### Requirements
- Python `3.14+`
- `pygame-ce`

### Install
```bash
cd "py version"
uv sync            # nếu dùng uv
# hoặc
pip install -e .   # nếu dùng virtualenv thường
```

### Run
```bash
python "Dodge the Magma with Shield!.py"
```

Chi tiết controls, save system, cheat console: xem README riêng trong
[`py version/`](py%20version) (nếu có) hoặc phần dưới đây — controls giống hệt bản C++.

## Bản C++ (`cpp_version/`)
Bản port sang C++ dùng `raylib`, đang phát triển song song, chưa port hết
100% tính năng của bản Python.

### Requirements
- Trình biên dịch C++17 trở lên (GCC / Clang / MSVC)
- CMake `3.15+`
- Kết nối mạng lúc `cmake ..` lần đầu (để tự tải raylib nếu máy chưa cài sẵn)
- Trên Linux cần thêm: `build-essential`, `libgl1-mesa-dev`, `libx11-dev`,
  `libxrandr-dev`, `libxi-dev`, `libxcursor-dev`, `libxinerama-dev`

### Build
```bash
cd cpp_version
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j
```
File thực thi nằm ở `cpp_version/build/bin/dodge_magma` (`.exe` trên Windows).

### Run
```bash
./build/bin/dodge_magma
```

## Controls (áp dụng cho cả 2 bản)
### Menu
- `SPACE`: Start game
- `S`: Open shop
- `Q`: Exit game

### In Game
- `A` / `D` (hoặc mũi tên trái/phải): Move
- `SPACE`: Jump / double jump / hold to jump higher
- `Q`: Dash
- `E`: Activate shield
- `ESC`: Pause / resume
- `` ` ``: Open cheat console

### Shop
- `1`: Speed upgrade
- `2`: Jump upgrade
- `3`: Shield upgrade
- `ESC`: Back to menu

### Pause
- `ESC`: Resume
- `M`: Back to menu
- `Q`: Save and quit

### Game Over
- `SPACE`: Retry
- `M`: Back to menu
- `S`: Open shop
- `Q`: Exit game

## Save System
- Bản Python lưu vào `save.json`.
- Bản C++ lưu vào `save.txt` (định dạng `key=value` đơn giản, không phụ
  thuộc thư viện JSON ngoài).

Cả 2 bản đều lưu: coins, player speed, jump strength, shield cooldown,
shield active time — và đều dùng cơ chế `queue + autosave` để tránh ghi file
quá thường xuyên khi nhặt nhiều coin.

## Cheat Console
Nhấn `` ` `` để mở console trong game (cả 2 bản).

Các lệnh hiện có:
- `help`
- `coin [n]`
- `speed [n]`
- `jump [n]`
- `god`
- `reset [coins/speed/shield/all]`
- `save`
- `stats`
- `exit`

## Project Structure
```
Dodge-the-Magma/
├── py version/       # bản gốc Python + pygame-ce
├── cpp_version/      # bản port C++ + raylib (đang port dở)
├── web ver py going to rm/   # bản thử nghiệm web, sẽ xoá
└── .gitignore
```

## Warning
- Nếu máy bạn yếu, hãy dùng bản c++.
- Nếu có thể, hãy dùng bản py vì nó là bản gốc.