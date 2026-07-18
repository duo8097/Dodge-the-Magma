// ============================================================
//  DODGE THE MAGMA  --  C++ / raylib port
//  Ported 1:1 (gameplay-wise) from the original Python/pygame
//  version. Same physics constants, same spawn patterns, same
//  shop, same console cheats.
// ============================================================

#include "raylib.h"
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <cmath>
#include <cstdlib>
#include <algorithm>
#include <cctype>

// ---------- CONSTANTS ----------
static const int   TARGET_FPS          = 60;
static const int   DEFAULT_WIDTH       = 1280;
static const int   DEFAULT_HEIGHT      = 720;
static const int   MIN_WIDTH           = 640;
static const int   MIN_HEIGHT          = 480;
static const int   GROUND_OFFSET       = 90;
static const int   PLAYER_SIZE         = 50;
static const int   MAGMA_SIZE          = 30;
static const int   COIN_SIZE           = 20;
static const float DASH_SPEED          = 19.0f;
static const float MAGMA_BASE_SPEED    = 6.2f;
static const float MAGMA_MAX_SPEED     = 13.0f;
static const float MAGMA_SCORE_SCALE   = 0.06f;
static const float COIN_FALL_SPEED     = 5.0f;
static const char* SAVE_FILE           = "save.txt";
static const int   AUTO_SAVE_INTERVAL  = 5000; // ms

// ---------- COLORS ----------
static const Color C_WHITE   = {255,255,255,255};
static const Color C_RED     = {255,80,70,255};
static const Color C_ORANGE  = {255,160,60,255};
static const Color C_BLUE    = {100,200,255,255};
static const Color C_GREEN   = {80,255,120,255};
static const Color C_YELLOW  = {255,220,70,255};
static const Color C_PURPLE  = {160,130,255,255};
static const Color C_BG      = {10,10,20,255};
static const Color C_GRID    = {30,30,60,255};

// ---------- SHOP ITEM ----------
struct ShopItem {
	int key;         // raylib key code
	const char* label;
	const char* title;
	int cost;
	Color color;
	const char* desc;
};
static ShopItem SHOP_ITEMS[3] = {
	{ KEY_ONE,   "1", "SPEED +1",       20,  C_BLUE,   "Faster movement" },
	{ KEY_TWO,   "2", "JUMP -2",        30,  C_GREEN,  "Stronger jump"   },
	{ KEY_THREE, "3", "SHIELD UPGRADE", 100, C_YELLOW, "Longer shield"   },
};

// ---------- PERSISTENT / PROGRESSION STATE ----------
static int   coins               = 0;
static int   player_speed        = 8;
static int   jump_strength       = -22;
static float shield_cooldown_real = 300;
static float shield_time_real     = 120;
static bool  save_dirty          = false;
static double last_save_tick     = 0;

static void SaveGame() {
	std::ofstream f(SAVE_FILE, std::ios::trunc);
	if (f.is_open()) {
		f << "coins=" << coins << "\n";
		f << "player_speed=" << player_speed << "\n";
		f << "jump_strength=" << jump_strength << "\n";
		f << "shield_cooldown_real=" << shield_cooldown_real << "\n";
		f << "shield_time_real=" << shield_time_real << "\n";
	}
	save_dirty = false;
	last_save_tick = GetTime() * 1000.0;
}

static void QueueSave() { save_dirty = true; }

static void LoadGame() {
	std::ifstream f(SAVE_FILE);
	if (!f.is_open()) { SaveGame(); return; }
	std::string line;
	while (std::getline(f, line)) {
		auto pos = line.find('=');
		if (pos == std::string::npos) continue;
		std::string key = line.substr(0, pos);
		std::string val = line.substr(pos + 1);
		try {
			if (key == "coins") coins = std::stoi(val);
			else if (key == "player_speed") player_speed = std::stoi(val);
			else if (key == "jump_strength") jump_strength = std::stoi(val);
			else if (key == "shield_cooldown_real") shield_cooldown_real = std::stof(val);
			else if (key == "shield_time_real") shield_time_real = std::stof(val);
		} catch (...) {}
	}
}

// ---------- HELPERS ----------
static float clampf(float v, float lo, float hi) { return std::max(lo, std::min(hi, v)); }
static float UpdateTimer(float value, float amount) { return std::max(0.0f, value - amount); }

static void DrawBox(float x, float y, float w, float h, Color fill = BLACK, Color border = C_WHITE, float radius = 0.18f) {
	Rectangle r = {x, y, w, h};
	DrawRectangleRounded(r, radius, 16, fill);
	DrawRectangleRoundedLines(r, radius, 16, border);
}

// screen size (mutable, changes after startup screen)
static int WIDTH = DEFAULT_WIDTH;
static int HEIGHT = DEFAULT_HEIGHT;

static void DrawTextCentered(const char* text, int y, Color color, int fontSize) {
	int w = MeasureText(text, fontSize);
	DrawText(text, WIDTH / 2 - w / 2, y, fontSize, color);
}

// ============================================================
//  STARTUP SCREEN  (resolution / fullscreen picker)
// ============================================================
struct StartupResult { int w; int h; bool fullscreen; };

static StartupResult RunStartupScreen() {
	const int presets[3][2] = { {1280,720}, {1600,900}, {1920,1080} };
	int selectedPreset = 0; // -1 = custom
	bool fullscreen = false;
	std::string customW = "1280";
	std::string customH = "720";
	int activeField = 0; // 0 none, 1 = w, 2 = h

	while (!WindowShouldClose()) {
		BeginDrawing();
		ClearBackground(C_BG);
		for (int x = 0; x < 560; x += 40) DrawLine(x, 0, x, 380, C_GRID);
		for (int y = 0; y < 380; y += 40) DrawLine(0, y, 560, y, C_GRID);

		DrawRectangleRounded({80,40,400,300}, 0.05f, 16, BLACK);
		DrawRectangleRoundedLines({80,40,400,300}, 0.05f, 16, C_WHITE);

		int tw = MeasureText("DODGE THE MAGMA", 26);
		DrawText("DODGE THE MAGMA", 280 - tw/2, 58, 26, C_WHITE);

		DrawText("DISPLAY MODE", 100, 100, 14, {140,140,180,255});

		Rectangle btnWindow = {100,118,175,32};
		Rectangle btnFull   = {285,118,175,32};

		auto drawBtn = [](Rectangle rect, const char* label, bool active, Color color) {
			Color bg = active ? Color{10,16,32,255} : Color{17,17,34,255};
			Color border = active ? color : Color{58,58,90,255};
			Color textColor = active ? color : Color{100,100,130,255};
			DrawRectangleRounded(rect, 0.25f, 16, bg);
			DrawRectangleRoundedLines(rect, 0.25f, 16, border);
			int w = MeasureText(label, 14);
			DrawText(label, rect.x + rect.width/2 - w/2, rect.y + rect.height/2 - 7, 14, textColor);
		};

		drawBtn(btnWindow, "WINDOW", !fullscreen, C_BLUE);
		drawBtn(btnFull, "FULLSCREEN", fullscreen, C_BLUE);

		Color resLabelColor = fullscreen ? Color{140,140,180,80} : Color{140,140,180,255};
		DrawText("RESOLUTION", 100, 164, 14, resLabelColor);

		Rectangle presetRects[3];
		for (int i = 0; i < 3; i++) {
			Rectangle rect = {(float)(100 + i*120), 182, 110, 28};
			presetRects[i] = rect;
			std::string label = std::to_string(presets[i][0]) + "x" + std::to_string(presets[i][1]);
			if (!fullscreen) drawBtn(rect, label.c_str(), selectedPreset == i, C_GREEN);
			else {
				DrawRectangleRounded(rect, 0.25f, 16, Color{17,17,34,255});
				DrawRectangleRoundedLines(rect, 0.25f, 16, Color{40,40,60,255});
			}
		}

		Rectangle customRect = {100, 218, 80, 28};
		if (!fullscreen) drawBtn(customRect, "custom", selectedPreset == -1, C_GREEN);

		Rectangle widthRect = {100, 254, 80, 28};
		Rectangle heightRect = {200, 254, 80, 28};
		bool showCustomFields = (selectedPreset == -1 && !fullscreen);
		if (showCustomFields) {
			for (int f = 0; f < 2; f++) {
				Rectangle rect = f == 0 ? widthRect : heightRect;
				std::string& val = f == 0 ? customW : customH;
				bool active = (activeField == (f+1));
				Color border = active ? C_BLUE : Color{58,58,90,255};
				DrawRectangleRounded(rect, 0.25f, 16, Color{11,11,22,255});
				DrawRectangleRoundedLines(rect, 0.25f, 16, border);
				int w = MeasureText(val.c_str(), 18);
				DrawText(val.c_str(), rect.x + rect.width/2 - w/2, rect.y + rect.height/2 - 9, 18, C_WHITE);
			}
			DrawText("x", 188, 262, 14, {80,80,110,255});
		}

		Rectangle launchRect = {100, 294, 360, 36};
		DrawRectangleRounded(launchRect, 0.2f, 16, BLACK);
		DrawRectangleRoundedLines(launchRect, 0.2f, 16, C_WHITE);
		int lw = MeasureText("[ LAUNCH ]", 18);
		DrawText("[ LAUNCH ]", launchRect.x + launchRect.width/2 - lw/2, launchRect.y + launchRect.height/2 - 9, 18, C_WHITE);

		EndDrawing();

		Vector2 mouse = GetMousePosition();
		auto hit = [&](Rectangle r){ return CheckCollisionPointRec(mouse, r); };

		if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
			if (hit(btnWindow)) fullscreen = false;
			if (hit(btnFull)) { fullscreen = true; activeField = 0; }
			if (!fullscreen) {
				for (int i = 0; i < 3; i++) if (hit(presetRects[i])) { selectedPreset = i; activeField = 0; }
				if (hit(customRect)) selectedPreset = -1;
				if (selectedPreset == -1) {
					if (hit(widthRect)) activeField = 1;
					else if (hit(heightRect)) activeField = 2;
					else activeField = 0;
				}
			}
			if (hit(launchRect)) {
				if (fullscreen) return {0, 0, true};
				if (selectedPreset >= 0) return {presets[selectedPreset][0], presets[selectedPreset][1], false};
				try {
					int w = std::stoi(customW), h = std::stoi(customH);
					return {w, h, false};
				} catch (...) {}
			}
		}

		if (activeField != 0) {
			std::string& val = activeField == 1 ? customW : customH;
			int ch = GetCharPressed();
			while (ch > 0) {
				if (std::isdigit(ch) && val.size() < 4) val += (char)ch;
				ch = GetCharPressed();
			}
			if (IsKeyPressed(KEY_BACKSPACE) && !val.empty()) val.pop_back();
			if (IsKeyPressed(KEY_TAB)) activeField = activeField == 1 ? 2 : 1;
		}

		if (IsKeyPressed(KEY_ENTER)) {
			if (fullscreen) return {0, 0, true};
			if (selectedPreset >= 0) return {presets[selectedPreset][0], presets[selectedPreset][1], false};
			try {
				int w = std::stoi(customW), h = std::stoi(customH);
				return {w, h, false};
			} catch (...) {}
		}
	}
	return {DEFAULT_WIDTH, DEFAULT_HEIGHT, false};
}

// ============================================================
//  GAME STATE
// ============================================================
enum class GameState { MENU, SHOP, GAME, PAUSE, GAMEOVER };

static GameState gameState = GameState::MENU;

// player
static Rectangle player;
static float player_pos_x, player_pos_y;
static float velocity_y = 0.0f;
static float player_vx = 0.0f;
static const float gravity = 1.35f;
static const float run_accel = 0.9f;
static const float run_friction = 0.80f;
static const int max_jumps = 2;
static int jumps_left = max_jumps;
static const float jump_hold_max = 12;
static float jump_hold_time = 0;
static int facing = 1;
static const float coyote_max = 6;
static float coyote_time = 0;
static const float jump_buffer_max = 6;
static float jump_buffer_time = 0;

// dash
static float dash_velocity = 0.0f;
static float dash_duration = 0;
static float dash_cooldown = 0;
struct TrailParticle { Rectangle rect; float life; };
static std::vector<TrailParticle> dash_trail;

// shield
static bool shield = false;
static float shield_time = 0;
static float shield_cooldown = 0;
static float shield_flash = 0;

// world objects
static std::vector<Rectangle> magma_list;
static std::vector<Rectangle> coin_list;
static double next_magma_spawn = 0;
static double next_coin_spawn = 0;

static int score = 0;
static double gameover_input_unlock_at = 0;

static bool console_open = false;
static std::string console_input = "";
struct ConsoleLine { std::string text; Color color; };
static std::vector<ConsoleLine> console_log;
static const Color CONSOLE_TEXT = {200,200,220,255};
static const Color CONSOLE_CMD  = {100,200,255,255};
static const Color CONSOLE_OK   = {80,255,120,255};
static const Color CONSOLE_ERR  = {255,80,70,255};
static const Color CONSOLE_INFO = {140,140,180,255};

static double NowMs() { return GetTime() * 1000.0; }

static int RandInt(int lo, int hi) { return GetRandomValue(lo, hi); }

static void ResetRun() {
	score = 0;
	gameState = GameState::GAME;
	gameover_input_unlock_at = 0;
	player.x = WIDTH / 2.0f;
	player.y = HEIGHT - GROUND_OFFSET - PLAYER_SIZE;
	player_pos_x = player.x;
	player_pos_y = player.y;
	velocity_y = 0.0f;
	player_vx = 0.0f;
	jumps_left = max_jumps;
	jump_hold_time = 0;
	coyote_time = 0;
	jump_buffer_time = 0;
	dash_velocity = 0.0f;
	dash_duration = 0;
	dash_cooldown = 0;
	dash_trail.clear();
	shield = false;
	shield_time = 0;
	shield_cooldown = 0;
	shield_flash = 0;
	magma_list.clear();
	coin_list.clear();
	facing = 1;
	double now = NowMs();
	next_magma_spawn = now + 300;
	next_coin_spawn = now + 900;
}

// ---------- SPAWN PATTERNS ----------
static void SpawnMagmaPattern() {
	// weighted choice: single 45, double 20, cluster 25, zigzag 10
	int roll = RandInt(1, 100);
	std::string pattern;
	if (roll <= 45) pattern = "single";
	else if (roll <= 65) pattern = "double";
	else if (roll <= 90) pattern = "cluster";
	else pattern = "zigzag";

	int spawnX = RandInt(20, std::max(20, WIDTH - 50));

	if (pattern == "single") {
		magma_list.push_back({(float)spawnX, -30, 30, 30});
	} else if (pattern == "double") {
		int offset = (RandInt(0,1) == 0) ? 40 : 55;
		float x1 = clampf((float)spawnX, 0, WIDTH - MAGMA_SIZE);
		float x2 = clampf((float)(spawnX + offset), 0, WIDTH - MAGMA_SIZE);
		magma_list.push_back({x1, -(float)MAGMA_SIZE, (float)MAGMA_SIZE, (float)MAGMA_SIZE});
		magma_list.push_back({x2, -(float)MAGMA_SIZE, (float)MAGMA_SIZE, (float)MAGMA_SIZE});
	} else if (pattern == "cluster") {
		int offsets[4] = {-44, -12, 20, 52};
		std::vector<int> idxs = {0,1,2,3};
		// shuffle
		for (int i = 3; i > 0; i--) { int j = RandInt(0, i); std::swap(idxs[i], idxs[j]); }
		int count = RandInt(3, 4);
		for (int i = 0; i < count; i++) {
			float x = clampf((float)(spawnX + offsets[idxs[i]]), 0, WIDTH - MAGMA_SIZE);
			magma_list.push_back({x, -(float)MAGMA_SIZE, (float)MAGMA_SIZE, (float)MAGMA_SIZE});
		}
	} else { // zigzag
		int lane = RandInt(0, 3);
		for (int i = 0; i < 4; i++) {
			float x = clampf((float)(spawnX + (i - lane) * 34), 0, WIDTH - MAGMA_SIZE);
			magma_list.push_back({x, -(float)MAGMA_SIZE - i * 10, (float)MAGMA_SIZE, (float)MAGMA_SIZE});
		}
	}
}

static void SpawnCoinPattern() {
	int roll = RandInt(1, 100);
	std::string pattern;
	if (roll <= 42) pattern = "single";
	else if (roll <= 70) pattern = "zigzag";
	else if (roll <= 90) pattern = "line";
	else pattern = "reward";

	int baseX = RandInt(15, std::max(15, WIDTH - 35));
	float baseY = -20;

	if (pattern == "single") {
		coin_list.push_back({(float)baseX, baseY, (float)COIN_SIZE, (float)COIN_SIZE});
	} else if (pattern == "zigzag") {
		for (int i = 0; i < 5; i++) {
			int sign = (i % 2 == 0) ? 1 : -1;
			float x = clampf((float)(baseX + sign * (18 + i*2)), 0, WIDTH - COIN_SIZE);
			float y = baseY - i * 22;
			coin_list.push_back({x, y, (float)COIN_SIZE, (float)COIN_SIZE});
		}
	} else if (pattern == "line") {
		for (int i = 0; i < 4; i++) {
			float x = clampf((float)(baseX + i * 26), 0, WIDTH - COIN_SIZE);
			coin_list.push_back({x, baseY - i * 8, (float)COIN_SIZE, (float)COIN_SIZE});
		}
	} else { // reward
		for (int i = 0; i < 3; i++) {
			float x = clampf((float)(baseX + i * 34 - 34), 0, WIDTH - COIN_SIZE);
			float y = baseY - std::abs(i - 1) * 18;
			coin_list.push_back({x, y, (float)COIN_SIZE, (float)COIN_SIZE});
		}
	}
}

// ---------- DRAWING ----------
static void DrawPlayer() {
	Color bodyColor = shield ? Color{135,240,255,255} : C_BLUE;
	int lean = (int)clampf(velocity_y / 4.0f, -4, 4);
	Rectangle body = { player.x + 2, player.y + 2, player.width - 4, player.height - 4 };

	DrawRectangleRounded({body.x, body.y + 4, body.width, body.height}, 0.28f, 16, Color{20,40,65,255});
	DrawRectangleRounded({body.x + lean, body.y, body.width, body.height}, 0.28f, 16, bodyColor);

	int eyeX = (int)(body.x + body.width/2 + (facing > 0 ? 7 : -14));
	DrawRectangleRounded({(float)eyeX, body.y + 12, 5, 5}, 0.4f, 16, C_WHITE);
	DrawRectangleRounded({(float)eyeX + 1, body.y + 13, 2, 2}, 0.4f, 16, Color{20,20,30,255});
}

static void DrawMagma(const Rectangle& m) {
	Vector2 center = { m.x + m.width/2, m.y + m.height/2 };
	DrawCircleGradient(center, 26, Fade(Color{255,90,45,255}, 0.35f), Fade(Color{255,90,45,255}, 0.0f));

	DrawRectangleRounded({m.x+2, m.y+2, m.width-4, m.height-4}, 0.3f, 16, Color{130,35,20,255});
	DrawRectangleRounded(m, 0.3f, 16, C_RED);
	DrawRectangleRounded({m.x+7, m.y+7, m.width-14, m.height-14}, 0.3f, 16, C_ORANGE);
}

static void DrawCoin(const Rectangle& c, double tick) {
	int pulse = 1 + (int)((std::sin(tick * 0.02) + 1) * 1.5);
	Vector2 center = { c.x + c.width/2, c.y + c.height/2 };
	DrawCircle(center.x, center.y, 11 + pulse/3, Color{200,160,20,255});
	DrawCircle(center.x, center.y, 8 + pulse/4, C_YELLOW);
	DrawCircle(center.x - 3, center.y - 3, 2, C_WHITE);
	DrawLine(center.x - 6, center.y, center.x + 6, center.y, C_WHITE);
	DrawLine(center.x, center.y - 6, center.x, center.y + 6, C_WHITE);
}

static void DrawGlowCircle(Vector2 center, float radius, Color color, float alpha) {
	DrawCircleGradient(center, radius, Fade(color, alpha / 255.0f), Fade(color, 0.0f));
}

// ---------- CONSOLE ----------
static void ConsoleExec(const std::string& cmdRaw) {
	std::string cmd = cmdRaw;
	for (auto& c : cmd) c = std::tolower((unsigned char)c);
	std::istringstream iss(cmd);
	std::string command, argStr;
	iss >> command;
	iss >> argStr;
	bool hasArg = !argStr.empty();
	int argInt = 0;
	bool argIsDigit = hasArg && !argStr.empty() && std::all_of(argStr.begin(), argStr.end(), ::isdigit);
	if (argIsDigit) argInt = std::stoi(argStr);

	auto log = [&](const std::string& text, Color color) {
		console_log.push_back({std::string("$ ") + cmdRaw, CONSOLE_CMD});
		console_log.push_back({text, color});
	};

	if (command.empty()) return;

	if (command == "coin") {
		int amount = argIsDigit ? argInt : 100;
		coins += amount; QueueSave();
		log("+" + std::to_string(amount) + " coins", CONSOLE_OK);
	} else if (command == "speed") {
		int amount = argIsDigit ? argInt : 2;
		player_speed += amount; QueueSave();
		log("speed -> " + std::to_string(player_speed), CONSOLE_OK);
	} else if (command == "jump") {
		int amount = argIsDigit ? argInt : 2;
		jump_strength -= amount; QueueSave();
		log("jump -> " + std::to_string(jump_strength), CONSOLE_OK);
	} else if (command == "god") {
		shield = true; shield_time = 999999;
		log("god mode ON", CONSOLE_OK);
	} else if (command == "reset") {
		if (argStr == "jump") { jump_strength = -22; QueueSave(); log("jump reset", CONSOLE_OK); }
		else if (argStr == "coin") { coins = 0; QueueSave(); log("coins reset", CONSOLE_OK); }
		else if (argStr == "speed") { player_speed = 8; QueueSave(); log("speed reset", CONSOLE_OK); }
		else if (argStr == "shield") { shield_cooldown_real = 300; shield_time_real = 120; QueueSave(); log("shield reset", CONSOLE_OK); }
		else if (argStr == "all" || !hasArg) {
			coins = 0; player_speed = 8; shield_cooldown_real = 300; shield_time_real = 120; QueueSave();
			log("full reset done", CONSOLE_OK);
		} else log("reset: unknown target '" + argStr + "'", CONSOLE_ERR);
	} else if (command == "help") {
		log("money [n] | speed [n] | god | reset [coins/speed/shield/all] | save | exit", CONSOLE_INFO);
	} else if (command == "exit") {
		SaveGame();
		CloseWindow();
		std::exit(0);
	} else if (command == "save") {
		SaveGame();
		log("saved to save.txt", CONSOLE_OK);
	} else if (command == "stats") {
		log("coins: " + std::to_string(coins) + ", speed: " + std::to_string(player_speed) +
			", jump: " + std::to_string(jump_strength) + ", shield_cd: " + std::to_string((int)shield_cooldown_real) +
			", shield_time: " + std::to_string((int)shield_time_real), CONSOLE_INFO);
	} else {
		log("unknown: " + command, CONSOLE_ERR);
	}
}

static void DrawConsole() {
	int h = 180;
	int y0 = HEIGHT - h;
	DrawRectangle(0, y0, WIDTH, h, Fade(BLACK, 0.82f));
	DrawLine(0, y0, WIDTH, y0, Color{60,60,120,255});

	DrawText("CHEAT CONSOLE  [ ESC close ]", 14, y0 + 8, 16, CONSOLE_INFO);

	int lineH = 22;
	int inputY = HEIGHT - 30;
	int maxDisplayLines = (inputY - 4 - (y0 + 32)) / lineH;
	if (maxDisplayLines < 0) maxDisplayLines = 0;

	int total = (int)console_log.size();
	int start = std::max(0, total - maxDisplayLines);
	int visibleCount = total - start;
	int startY = inputY - 4 - visibleCount * lineH;
	for (int i = start; i < total; i++) {
		DrawText(console_log[i].text.c_str(), 14, startY + (i - start) * lineH, 16, console_log[i].color);
	}

	DrawLine(0, inputY - 4, WIDTH, inputY - 4, Color{60,60,120,255});
	std::string prompt = "$ " + console_input;
	DrawText(prompt.c_str(), 14, inputY, 16, CONSOLE_CMD);
	if (((int)(GetTime() * 1000) / 500) % 2 == 0) {
		int cursorX = 14 + MeasureText(prompt.c_str(), 16) + 2;
		DrawRectangle(cursorX, inputY + 2, 2, 18, CONSOLE_CMD);
	}
}

// ---------- UI SCREENS ----------
static void DrawHud() {
	DrawBox(10, 10, 320, 108, BLACK, C_WHITE);
	DrawText(TextFormat("SCORE: %d", score), 22, 20, 28, C_WHITE);
	DrawText(TextFormat("COINS: %d", coins), 22, 52, 28, C_YELLOW);
	DrawText(TextFormat("SPD: %d", player_speed), 22, 90, 20, C_BLUE);
	DrawText(TextFormat("JUMPS: %d/%d", jumps_left, max_jumps), 150, 90, 20, C_GREEN);
}

static void DrawAbilityBar() {
	int iconSize = 34, barW = 110, barH = 12, slotGap = 24, iconBarGap = 10;
	int slotW = iconSize + iconBarGap + barW;

	struct Slot { const char* label; const char* key; float ratio; Color color; bool active; };
	Slot slots[2] = {
		{ "DASH", "[Q]", dash_cooldown <= 0 ? 1.0f : 1 - dash_cooldown / 60.0f, C_BLUE, dash_cooldown <= 0 },
		{ "SHIELD", "[E]", shield_cooldown <= 0 ? 1.0f : 1 - shield_cooldown / shield_cooldown_real, C_GREEN, shield || shield_cooldown <= 0 },
	};

	int totalW = slotW * 2 + slotGap;
	int startX = WIDTH / 2 - totalW / 2;
	int centerY = HEIGHT - 55;

	for (int i = 0; i < 2; i++) {
		Slot& s = slots[i];
		int x = startX + i * (slotW + slotGap);
		int iconY = centerY - iconSize / 2;
		Color iconBorder = s.active ? s.color : Color{58,58,90,255};
		Color iconBg = s.active ? (s.color.g == 255 && s.color.r == 80 ? Color{10,22,12,255} : Color{10,16,32,255}) : Color{17,17,34,255};
		DrawRectangleRounded({(float)x, (float)iconY, (float)iconSize, (float)iconSize}, 0.15f, 16, iconBg);
		DrawRectangleRoundedLines({(float)x, (float)iconY, (float)iconSize, (float)iconSize}, 0.15f, 16, iconBorder);
		if (s.active) DrawCircle(x + iconSize - 6, iconY + 6, 3, s.color);

		int barX = x + iconSize + iconBarGap;
		int labelH = 20, keyH = 20;
		int contentH = labelH + 4 + barH + 4 + keyH;
		int textY = centerY - contentH / 2;

		DrawText(s.label, barX, textY, 16, Color{180,180,210,255});
		int barY = textY + labelH + 4;
		DrawRectangleRounded({(float)barX, (float)barY, (float)barW, (float)barH}, 0.4f, 16, Color{26,26,46,255});
		DrawRectangleRoundedLines({(float)barX, (float)barY, (float)barW, (float)barH}, 0.4f, 16, Color{58,58,90,255});
		int fillW = std::max(0, (int)(barW * clampf(s.ratio, 0, 1)));
		if (fillW > 0) DrawRectangleRounded({(float)barX, (float)barY, (float)fillW, (float)barH}, 0.4f, 16, s.color);
		DrawText(s.key, barX, barY + barH + 4, 16, Color{90,90,120,255});
	}
}

static void DrawInfoHub() {
	int hubW = 220, hubH = 72;
	int hubX = WIDTH - hubW - 12, hubY = 12;
	DrawBox(hubX, hubY, hubW, hubH, BLACK, C_WHITE);
	DrawText(TextFormat("COINS: %d", coins), hubX + 16, hubY + 14, 20, C_YELLOW);
	DrawText(TextFormat("SCORE: %d", score), hubX + 16, hubY + 40, 20, C_WHITE);
}

static void DrawMenu() {
	DrawBox(WIDTH/2 - 260, 170, 520, 340, BLACK, C_WHITE);
	int y = 210;
	int gap = 42;
	DrawText("DODGE THE MAGMA", WIDTH/2 - 230, y, 48, C_WHITE);
	y += 72;
	DrawTextCentered("[ SPACE ] START", y, C_BLUE, 28); y += gap;
	DrawTextCentered("[ S ] SHOP", y, C_GREEN, 28); y += gap;
	DrawTextCentered("[ Q ] EXIT", y, C_RED, 28); y += gap;
	DrawTextCentered(TextFormat("COINS: %d", coins), y, C_YELLOW, 28);
}

static void DrawShop() {
	DrawBox(WIDTH/2 - 330, 140, 660, 430, BLACK, C_WHITE);
	Vector2 mouse = GetMousePosition();
	Rectangle itemRects[3] = {
		{(float)(WIDTH/2 - 250), 220, 500, 70},
		{(float)(WIDTH/2 - 250), 305, 500, 70},
		{(float)(WIDTH/2 - 250), 390, 500, 70},
	};
	DrawTextCentered("=== SHOP ===", 180, C_YELLOW, 28);

	for (int i = 0; i < 3; i++) {
		ShopItem& item = SHOP_ITEMS[i];
		Rectangle r = itemRects[i];
		bool hovered = CheckCollisionPointRec(mouse, r);
		Color fill = hovered ? Color{50,50,72,255} : Color{28,28,40,255};
		Color border = hovered ? item.color : C_WHITE;
		DrawRectangleRounded(r, 0.17f, 16, fill);
		DrawRectangleRoundedLines(r, 0.17f, 16, border);

		std::string iconTxt = std::string("[") + item.label + "]";
		DrawText(iconTxt.c_str(), r.x + 18, r.y + 16, 20, item.color);
		DrawText(item.title, r.x + 78, r.y + 12, 28, C_WHITE);
		DrawText(item.desc, r.x + 78, r.y + 38, 20, Color{180,180,190,255});
		std::string costTxt = std::to_string(item.cost) + " coins";
		int cw = MeasureText(costTxt.c_str(), 20);
		DrawText(costTxt.c_str(), r.x + r.width - cw - 18, r.y + 23, 20, C_YELLOW);
	}

	DrawTextCentered("[ ESC ] BACK", 490, C_WHITE, 28);
	DrawTextCentered(TextFormat("COINS: %d", coins), 528, C_YELLOW, 28);
}

static void DrawPause() {
	DrawBox(WIDTH/2 - 250, 180, 500, 260, BLACK, C_BLUE);
	DrawTextCentered("PAUSED", 225, C_BLUE, 48);
	DrawTextCentered("[ ESC ] RESUME", 310, C_WHITE, 28);
	DrawTextCentered("[ M ] MENU", 352, C_GREEN, 28);
	DrawTextCentered("[ Q ] SAVE & QUIT", 394, C_RED, 28);
}

static void DrawGameOver() {
	DrawBox(WIDTH/2 - 260, 160, 520, 380, BLACK, C_RED);
	int y = 200, gap = 38;
	DrawText("GAME OVER", WIDTH/2 - 150, y, 48, C_RED);
	y += 72;
	DrawTextCentered(TextFormat("SCORE: %d", score), y, C_WHITE, 28); y += gap;
	DrawTextCentered(TextFormat("COINS: %d", coins), y, C_YELLOW, 28); y += gap;
	DrawTextCentered("[ SPACE ] RETRY", y, C_BLUE, 28); y += gap;
	DrawTextCentered("[ M ] MENU", y, C_GREEN, 28); y += gap;
	DrawTextCentered("[ S ] SHOP", y, C_YELLOW, 28); y += gap;
	DrawTextCentered("[ Q ] EXIT", y, C_WHITE, 28);
	if (NowMs() < gameover_input_unlock_at) {
		DrawTextCentered("Please wait...", y + 36, Color{180,180,180,255}, 20);
	}
}

// ============================================================
//  MAIN
// ============================================================
int main() {
	SetConfigFlags(FLAG_MSAA_4X_HINT | FLAG_VSYNC_HINT);
	InitWindow(560, 380, "DODGE THE MAGMA");
	// Không ép cứng 60 FPS nữa — để VSync tự đồng bộ theo tần số quét
	// thật của màn hình (75/120/144Hz...), vật lý vẫn chuẩn vì dt đã
	// được scale theo thời gian thực (GetFrameTime), không phụ thuộc FPS.
	SetExitKey(KEY_NULL); // we handle quitting manually

	StartupResult startRes = RunStartupScreen();

	if (startRes.fullscreen) {
		int monitor = GetCurrentMonitor();
		WIDTH = GetMonitorWidth(monitor);
		HEIGHT = GetMonitorHeight(monitor);
		SetWindowSize(WIDTH, HEIGHT);
		SetWindowState(FLAG_FULLSCREEN_MODE);
	} else {
		WIDTH = std::max(MIN_WIDTH, startRes.w);
		HEIGHT = std::max(MIN_HEIGHT, startRes.h);
		SetWindowSize(WIDTH, HEIGHT);
	}
	SetWindowTitle("DODGE THE MAGMA");

	LoadGame();

	player = { WIDTH / 2.0f, HEIGHT - 100.0f, (float)PLAYER_SIZE, (float)PLAYER_SIZE };
	player_pos_x = player.x;
	player_pos_y = player.y;
	next_magma_spawn = NowMs() + 300;
	next_coin_spawn = NowMs() + 900;

	while (!WindowShouldClose()) {
		float dt = GetFrameTime() * (float)TARGET_FPS; // frame-independent scaling like pygame clock.tick/FRAME_MS
		dt = clampf(dt, 0.0f, 3.0f); // guard against spikes
		double tick = NowMs();

		if (IsWindowResized() && !IsWindowFullscreen()) {
			WIDTH = GetScreenWidth();
			HEIGHT = GetScreenHeight();
		}

		if (save_dirty && tick - last_save_tick >= AUTO_SAVE_INTERVAL) SaveGame();

		// ---------- EVENTS (key-down style) ----------
		if (IsKeyPressed(KEY_GRAVE)) {
			console_open = !console_open;
			console_input = "";
		} else if (console_open) {
			int ch = GetCharPressed();
			while (ch > 0) {
				if (ch >= 32 && ch < 127) console_input += (char)ch;
				ch = GetCharPressed();
			}
			if (IsKeyPressed(KEY_BACKSPACE) && !console_input.empty()) console_input.pop_back();
			if (IsKeyPressed(KEY_ESCAPE)) { console_open = false; console_input = ""; }
			if (IsKeyPressed(KEY_ENTER)) {
				if (!console_input.empty()) ConsoleExec(console_input);
				console_input = "";
			}
		} else {
			switch (gameState) {
				case GameState::MENU:
					if (IsKeyPressed(KEY_SPACE)) ResetRun();
					if (IsKeyPressed(KEY_S)) gameState = GameState::SHOP;
					if (IsKeyPressed(KEY_Q)) { SaveGame(); CloseWindow(); return 0; }
					break;
				case GameState::SHOP:
					if (IsKeyPressed(KEY_ONE) && coins >= 20) { player_speed += 1; coins -= 20; QueueSave(); }
					if (IsKeyPressed(KEY_TWO) && coins >= 30) { jump_strength -= 2; coins -= 30; QueueSave(); }
					if (IsKeyPressed(KEY_THREE) && coins >= 100) {
						shield_cooldown_real = std::max(120.0f, shield_cooldown_real - 10);
						shield_time_real += 10; coins -= 100; QueueSave();
					}
					if (IsKeyPressed(KEY_ESCAPE)) gameState = GameState::MENU;
					break;
				case GameState::PAUSE:
					if (IsKeyPressed(KEY_ESCAPE)) gameState = GameState::GAME;
					if (IsKeyPressed(KEY_M)) gameState = GameState::MENU;
					if (IsKeyPressed(KEY_Q)) { SaveGame(); CloseWindow(); return 0; }
					break;
				case GameState::GAMEOVER:
					if (tick >= gameover_input_unlock_at) {
						if (IsKeyPressed(KEY_SPACE)) ResetRun();
						if (IsKeyPressed(KEY_M)) gameState = GameState::MENU;
						if (IsKeyPressed(KEY_S)) gameState = GameState::SHOP;
						if (IsKeyPressed(KEY_Q)) { SaveGame(); CloseWindow(); return 0; }
					}
					break;
				case GameState::GAME:
					if (IsKeyPressed(KEY_SPACE)) jump_buffer_time = jump_buffer_max;
					if (IsKeyPressed(KEY_Q) && dash_cooldown <= 0) {
						dash_velocity = DASH_SPEED * facing;
						dash_duration = 12;
						dash_cooldown = 60;
					}
					if (IsKeyPressed(KEY_E) && shield_cooldown <= 0) {
						shield = true;
						shield_time = shield_time_real;
						shield_cooldown = shield_cooldown_real;
					}
					if (IsKeyPressed(KEY_ESCAPE)) gameState = GameState::PAUSE;
					break;
			}
			if (gameState == GameState::GAME && IsKeyReleased(KEY_SPACE)) jump_hold_time = 0;
		}

		// ---------- UPDATE + DRAW ----------
		BeginDrawing();
		ClearBackground(C_BG);
		for (int x = 0; x < WIDTH; x += 40) DrawLine(x, 0, x, HEIGHT, C_GRID);
		for (int y = 0; y < HEIGHT; y += 40) DrawLine(0, y, WIDTH, y, C_GRID);

		if (gameState == GameState::GAME && !console_open) {
			bool onGround = (player.y + player.height) >= HEIGHT - GROUND_OFFSET;

			int moveDir = 0;
			if (IsKeyDown(KEY_A) || IsKeyDown(KEY_LEFT)) moveDir -= 1;
			if (IsKeyDown(KEY_D) || IsKeyDown(KEY_RIGHT)) moveDir += 1;

			float runMaxSpeed = (float)player_speed;
			if (moveDir != 0) {
				facing = moveDir;
				player_vx += moveDir * run_accel * dt;
			} else {
				player_vx *= std::pow(run_friction, dt);
			}
			player_vx = clampf(player_vx, -runMaxSpeed, runMaxSpeed);
			player_pos_x += player_vx * dt;
			player.x = player_pos_x;
			if (player.x < 0) { player.x = 0; player_pos_x = player.x; player_vx = 0; }
			if (player.x + player.width > WIDTH) { player.x = WIDTH - player.width; player_pos_x = player.x; player_vx = 0; }

			if (IsKeyDown(KEY_SPACE) && jump_hold_time > 0 && velocity_y < 0) {
				velocity_y -= 0.75f * dt;
				jump_hold_time = UpdateTimer(jump_hold_time, dt);
			}

			if (jump_buffer_time > 0) {
				jump_buffer_time = UpdateTimer(jump_buffer_time, dt);
				if (onGround || coyote_time > 0 || jumps_left > 0) {
					velocity_y = (float)jump_strength;
					if (onGround || coyote_time > 0) jumps_left = std::max(0, jumps_left - 1);
					else jumps_left -= 1;
					jump_hold_time = jump_hold_max;
					jump_buffer_time = 0;
				}
			}

			velocity_y += gravity * dt;
			player_pos_y += velocity_y * dt;
			player.y = player_pos_y;

			if (player.y + player.height >= HEIGHT - GROUND_OFFSET) {
				player.y = HEIGHT - GROUND_OFFSET - player.height;
				player_pos_y = player.y;
				velocity_y = 0;
				jumps_left = max_jumps;
				jump_hold_time = 0;
				coyote_time = coyote_max;
			} else {
				coyote_time = UpdateTimer(coyote_time, dt);
			}

			// dash
			if (dash_duration > 0) {
				dash_velocity *= std::pow(0.95f, dt);
				player_pos_x += dash_velocity * dt;
				player.x = player_pos_x;
				dash_duration = UpdateTimer(dash_duration, dt);

				bool hitWall = false;
				if (player.x <= 0) { player.x = 0; player_pos_x = player.x; hitWall = true; }
				else if (player.x + player.width >= WIDTH) { player.x = WIDTH - player.width; player_pos_x = player.x; hitWall = true; }

				if (hitWall) {
					dash_velocity *= -0.65f;
					dash_duration = std::max(0.0f, dash_duration - 2);
					facing = dash_velocity >= 0 ? 1 : -1;
					dash_trail.push_back({player, 12});
				}
			}
			if (dash_cooldown > 0) dash_cooldown = UpdateTimer(dash_cooldown, dt);

			// shield
			if (shield) {
				shield_time = UpdateTimer(shield_time, dt);
				shield_flash = 10;
				if (shield_time <= 0) shield = false;
			}
			if (shield_cooldown > 0) shield_cooldown = UpdateTimer(shield_cooldown, dt);
			if (shield_flash > 0) shield_flash = UpdateTimer(shield_flash, dt);

			// spawn
			if (tick >= next_magma_spawn) {
				SpawnMagmaPattern();
				next_magma_spawn = tick + RandInt(380, 700);
			}
			if (tick >= next_coin_spawn) {
				SpawnCoinPattern();
				next_coin_spawn = tick + RandInt(850, 1350);
			}

			float magmaSpeed = std::min(MAGMA_MAX_SPEED, MAGMA_BASE_SPEED + score * MAGMA_SCORE_SCALE);

			// magma update
			std::vector<Rectangle> nextMagma;
			bool died = false;
			for (auto& m : magma_list) {
				m.y += magmaSpeed * dt;
				if (CheckCollisionRecs(m, player)) {
					if (shield) {
						shield_flash = std::max(shield_flash, 14.0f);
						// magma consumed, don't keep
					} else {
						coins += score;
						QueueSave();
						gameState = GameState::GAMEOVER;
						gameover_input_unlock_at = tick + 1000; // 180 frames @60fps ~ 3s
						died = true;
						nextMagma.push_back(m);
					}
				} else if (m.y > HEIGHT) {
					score += 1;
				} else {
					nextMagma.push_back(m);
				}
				if (died) break;
			}
			if (!died) magma_list = nextMagma;

			// coin update
			if (!died) {
				int collected = 0;
				std::vector<Rectangle> nextCoins;
				for (auto& c : coin_list) {
					c.y += COIN_FALL_SPEED * dt;
					if (CheckCollisionRecs(c, player)) collected += 1;
					else if (c.y > HEIGHT) continue;
					else nextCoins.push_back(c);
				}
				if (collected) { coins += collected; QueueSave(); }
				coin_list = nextCoins;
			}

			// trail update
			std::vector<TrailParticle> nextTrail;
			for (auto& p : dash_trail) {
				p.life = UpdateTimer(p.life, dt);
				if (p.life > 0) nextTrail.push_back(p);
			}
			dash_trail = nextTrail;

			// draw trail
			for (auto& p : dash_trail) {
				float alpha = 20 + p.life * 8;
				DrawRectangleRounded({p.rect.x - 15, p.rect.y - 15, p.rect.width + 30, p.rect.height + 30},
									  0.3f, 16, Fade(Color{120,210,255,255}, alpha / 255.0f));
			}

			// draw world
			for (auto& m : magma_list) DrawMagma(m);
			for (auto& c : coin_list) DrawCoin(c, tick);
			DrawPlayer();

			Vector2 playerCenter = { player.x + player.width/2, player.y + player.height/2 };
			if (shield) {
				int pulse = 28 + (int)((std::sin(tick * 0.03) + 1) * 2);
				DrawGlowCircle(playerCenter, (float)pulse, C_GREEN, 75);
				DrawCircleLines(playerCenter.x, playerCenter.y, pulse, C_GREEN);
			} else if (shield_flash > 0) {
				DrawGlowCircle(playerCenter, 28 + shield_flash, C_BLUE, 60);
			}

			DrawHud();
			DrawAbilityBar();
		} else if (gameState == GameState::MENU) {
			DrawMenu();
			DrawInfoHub();
		} else if (gameState == GameState::SHOP) {
			DrawShop();
			DrawInfoHub();
		} else if (gameState == GameState::PAUSE) {
			DrawPause();
			DrawInfoHub();
		} else if (gameState == GameState::GAMEOVER) {
			DrawGameOver();
			DrawInfoHub();
		}

		if (console_open) DrawConsole();

		EndDrawing();
	}

	SaveGame();
	CloseWindow();
	return 0;
}