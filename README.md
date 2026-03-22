# Dodge the Magma

Một game arcade nhỏ viết bằng `pygame-ce`: người chơi né magma rơi từ trên xuống, nhặt coin, dùng dash và shield để sống lâu nhất có thể.

## Features

- Di chuyển trái/phải mượt hơn với cảm giác quán tính nhẹ.
- Jump có `double jump`, `variable jump`, `jump buffer`, và `coyote time`.
- Dash có cooldown và bật nảy khi chạm tường.
- Shield có thời gian hoạt động, cooldown, và hiệu ứng hình ảnh.
- Magma và coin spawn theo pattern thay vì chỉ random đơn giản.
- Có `shop`, `game over menu`, save/load coin và upgrade.
- Window mode tự fallback về resolution an toàn nếu nhập sai như `0 0`.

## Requirements

- Python `3.14+`
- `pygame-ce`

## Install

Nếu dùng `uv`:

```bash
uv sync
```

Nếu dùng virtualenv thường:

```bash
pip install -e .
```

## Run

Chạy trực tiếp file game:

```bash
python "Dodge the Magma with Shield!.py"
```

Khi start game:

- Nhập `1` để chạy fullscreen.
- Nhập `0` để chạy window mode.
- Nếu chọn window mode, nhập resolution như `1280 720`.
- Nếu nhập sai hoặc nhập `0 0`, game sẽ tự chuyển sang kích thước an toàn.

## Controls

### Menu

- `SPACE`: Start game
- `S`: Open shop
- `Q`: Exit game

### In Game

- `A` / `D`: Move
- `SPACE`: Jump / double jump / hold to jump higher
- `Q`: Dash
- `E`: Activate shield

### Shop

- `1`: Speed upgrade
- `2`: Jump upgrade
- `3`: Shield upgrade
- `ESC`: Back to menu

### Game Over

- `SPACE`: Retry
- `M`: Back to menu
- `S`: Open shop
- `Q`: Exit game

## Save System

Game lưu dữ liệu vào `save.json`.

Các dữ liệu đang được lưu:

- Coins
- Player speed
- Jump strength
- Shield cooldown
- Shield active time

Game dùng cơ chế `queue + autosave` để tránh ghi file quá thường xuyên khi nhặt nhiều coin.

## Debug Commands

Khi game đang chạy, terminal input thread vẫn nhận một số lệnh debug:

- `reset`: reset một phần progress
- `exit`: thoát game

## Project Structure

- [Dodge the Magma with Shield!.py](Dodge%20the%20Magma%20with%20Shield!.py): file game chính
- [save.json](save.json): dữ liệu save
- [pyproject.toml](pyproject.toml): metadata và dependencies

