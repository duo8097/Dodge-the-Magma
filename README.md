# Dodge the Magma

Một game arcade nhỏ viết bằng `pygame-ce`: người chơi né magma rơi từ trên xuống, nhặt coin, dùng dash và shield để sống lâu nhất có thể.

## Features

- Di chuyển trái/phải mượt hơn với cảm giác quán tính nhẹ.
- Jump có `double jump`, `variable jump`, `jump buffer`, và `coyote time`.
- Dash có cooldown và bật nảy khi chạm tường.
- Shield có thời gian hoạt động, cooldown, và hiệu ứng hình ảnh.
- Magma và coin spawn theo pattern thay vì chỉ random đơn giản.
- Có `shop`, `game over menu`, save/load coin và upgrade.
- Có startup screen trong `pygame` để chọn fullscreen, preset resolution, hoặc custom resolution.
- Có `pause menu` bằng `ESC` khi đang chơi.

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

- Chọn `WINDOW` hoặc `FULLSCREEN`.
- Nếu ở `WINDOW`, có thể chọn preset hoặc `custom`.
- Với `custom`, click vào ô width/height để nhập kích thước.
- Nhấn `LAUNCH` hoặc `Enter` để bắt đầu.

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

Game lưu dữ liệu vào `save.json`.

Các dữ liệu đang được lưu:

- Coins
- Player speed
- Jump strength
- Shield cooldown
- Shield active time

Game dùng cơ chế `queue + autosave` để tránh ghi file quá thường xuyên khi nhặt nhiều coin.

## Cheat Console

Nhấn `` ` `` để mở console trong game.

Các lệnh hiện có:

- `help`
- `money`
- `god`
- `speed`
- `reset`

## Project Structure

- [Dodge the Magma with Shield!.py](Dodge%20the%20Magma%20with%20Shield!.py): file game chính
- [save.json](save.json): dữ liệu save
- [pyproject.toml](pyproject.toml): metadata và dependencies

