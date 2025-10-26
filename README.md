# Automated Accumulator Betting Bot (Mock Version)

This is a **fully automated accumulator betting bot simulation** written in Python.  
It replicates the **entire flow** — authentication, match selection, accumulator building, bet placement, error handling, and result logging — without connecting to any real betting platform.  
You can safely test and demonstrate all functionality before linking it to an official API (such as 1xBet’s authorized developer interface, if available).

---

## ⚙️ Features
- Hands-free automation: from login → build → place → confirm.
- Simulated API (`MockBettingAPI`) for safe testing.
- Robust error handling (retry, exponential backoff, odds change simulation).
- Customizable configuration via environment variables.
- JSON log of placed bets and full logging to file.
- Simple scheduling & run-locking to prevent overlapping tasks.

---

## 🧩 File Overview

| File | Description |
|------|--------------|
| `accumulator_bot_mock.py` | Main bot script (runnable end-to-end). |
| `accumulator_bot.log` | Log output file generated on each run. |
| `placed_bets.jsonl` | JSON line file storing each bet placed. |
| `README.md` | This documentation file. |

---

## 🐍 Requirements

- Python **3.10+**
- No external dependencies (uses built-in libraries only)

---

## 🚀 Quick Start

1. **Clone or download** this repository.

2. **Set environment variables** (or edit defaults inside the script):

   ```bash
   export BOT_USERNAME="your_username"
   export BOT_PASSWORD="your_password"
   export DEFAULT_STAKE="10.0"
   export MAX_LEGS="4"
   export MATCH_SELECTION="top"   # options: top | random | from_feed
   ```

3. **Run the bot manually**:

   ```bash
   python accumulator_bot_mock.py
   ```

4. Watch the console output or open:
   - `accumulator_bot.log` for detailed run info
   - `placed_bets.jsonl` for all simulated bets

---

## 🧠 Configuration Variables

| Variable | Default | Description |
|-----------|----------|-------------|
| `BOT_USERNAME` | test_user | Account username |
| `BOT_PASSWORD` | test_pass | Account password |
| `DEFAULT_STAKE` | 5.0 | Amount per accumulator |
| `MAX_LEGS` | 4 | Number of legs per bet |
| `MIN_ODDS` | 1.20 | Minimum acceptable odds per leg |
| `MATCH_SELECTION` | top | Match selection mode (top/random/from_feed) |
| `MAX_RETRIES` | 5 | Number of retry attempts for network/API errors |
| `RETRY_BACKOFF_BASE` | 1.5 | Base multiplier for exponential backoff |
| `BOT_LOG_FILE` | accumulator_bot.log | Log output filename |

---

## 🕒 Scheduling (Automation)

You can schedule automatic runs using **cron (Linux/macOS)** or **Task Scheduler (Windows)**.

### Example cron job (every 30 minutes)

```bash
*/30 * * * * cd /path/to/bot && /usr/bin/python3 accumulator_bot_mock.py >> cron_run.log 2>&1
```

The bot uses a lockfile (`accumulator_bot.lock`) to ensure only one run executes at a time.

---

## 📦 Output

Example log excerpt:

```
2025-10-11 08:00:00 - INFO - Logging in as test_user
2025-10-11 08:00:02 - INFO - Authenticated, session token: session-48291
2025-10-11 08:00:03 - INFO - Selected legs: ['M001', 'M004', 'M010', 'M013']
2025-10-11 08:00:04 - INFO - Placement result: {'bet_id': 'B1000', 'status': 'ACCEPTED', ...}
2025-10-11 08:00:05 - INFO - FINAL: bet_id=B1000 stake=10.00 total_odd=8.12 potential_return=81.20
```

---

## 🔄 Adapting to a Real API

To connect this bot to a **real authorized API**, replace the `MockBettingAPI` class with an implementation that matches these method signatures:

```python
authenticate(username, password) -> str
get_available_matches() -> list[dict]
place_accumulator(session_token, legs, stake) -> dict
get_bet(bet_id) -> dict
```

Keep the rest of the bot code unchanged — it’s already designed for clean plug-and-play integration.

---

## ⚠️ Disclaimer

This mock bot is **for educational and testing purposes only**.  
It does **not** place real bets, nor should it be modified to interact with real sites without written authorization or official API documentation.  
Always ensure compliance with local laws and the terms of service of any betting platform.

---

## 👨‍💻 Author
**Automated Accumulator Bot (Mock Version)** — Python demo build  
By: *M. Dani (with GPT-5)*  
Date: October 2025
