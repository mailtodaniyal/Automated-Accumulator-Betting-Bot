import os
import time
import json
import random
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

API_BASE = os.getenv("MOCK_API_BASE", "https://mock-betting.local/api")
USERNAME = os.getenv("BOT_USERNAME", "test_user")
PASSWORD = os.getenv("BOT_PASSWORD", "test_pass")
DEFAULT_STAKE = float(os.getenv("DEFAULT_STAKE", "5.0"))
MAX_LEGS = int(os.getenv("MAX_LEGS", "4"))
MIN_ODDS = float(os.getenv("MIN_ODDS", "1.20"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
RETRY_BACKOFF_BASE = float(os.getenv("RETRY_BACKOFF_BASE", "1.5"))
LOG_FILE = os.getenv("BOT_LOG_FILE", "accumulator_bot.log")
MATCH_SELECTION_MODE = os.getenv("MATCH_SELECTION", "top")  
SIMULATED_NETWORK_FAILURE_RATE = float(os.getenv("SIM_NET_FAIL", "0.05")) 

logger = logging.getLogger("AccumulatorBotMock")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

# ===== Mock API classes to simulate a bookmaker =====
class MockAPIError(Exception):
    pass

class MockBettingAPI:
    """
    Simulated betting API. Replace this class in production with a real API client.
    This mock supports:
      - authenticate(username, password) -> session_token
      - get_available_matches() -> list of matches with odds
      - place_accumulator(session_token, legs, stake) -> {bet_id, status}
      - get_bet(bet_id) -> bet status/details
    """
    def __init__(self):
        self._sessions = {}
        self._bets = {}
        self._next_bet_id = 1000
        random.seed(42)

    def _maybe_network_failure(self):
        if random.random() < SIMULATED_NETWORK_FAILURE_RATE:
            raise MockAPIError("Simulated transient network error")

    def authenticate(self, username: str, password: str) -> str:
        self._maybe_network_failure()
        if username == "" or password == "":
            raise MockAPIError("Invalid credentials")
        token = f"session-{random.randint(10000,99999)}"
        self._sessions[token] = {"user": username, "issued": datetime.utcnow()}
        return token

    def get_available_matches(self) -> List[Dict[str, Any]]:
        self._maybe_network_failure()
        now = datetime.utcnow()
        matches = []
        # produce a list of 20 simulated matches with random odds and availability
        for i in range(1, 21):
            match = {
                "match_id": f"M{i:03}",
                "teams": (f"Team{i}A", f"Team{i}B"),
                "start_time": (now + timedelta(minutes=30 + i*10)).isoformat(),
                "odds": round(random.uniform(1.15, 3.5), 2),
                "available": random.random() > 0.02  # 2% chance unavailable
            }
            matches.append(match)
        return matches

    def place_accumulator(self, session_token: str, legs: List[Dict[str, Any]], stake: float) -> Dict[str, Any]:
        self._maybe_network_failure()
        if session_token not in self._sessions:
            raise MockAPIError("Invalid session")
        # validate legs
        for leg in legs:
            if not leg.get("available", True):
                raise MockAPIError(f"Leg {leg['match_id']} unavailable at placement")
            if leg.get("odds", 0) < MIN_ODDS:
                raise MockAPIError(f"Leg {leg['match_id']} odds too low")
        # simulate acceptance with some chance of odds change
        if random.random() < 0.08:
            # simulate an odds change event
            for leg in legs:
                leg["odds"] = round(max(1.05, leg["odds"] * random.uniform(0.90, 1.12)), 2)
            # 50% chance the platform rejects after odds change
            if random.random() < 0.5:
                raise MockAPIError("Odds changed during placement - please retry")
        bet_id = f"B{self._next_bet_id}"
        self._next_bet_id += 1
        total_odd = 1.0
        for leg in legs:
            total_odd *= leg["odds"]
        potential_return = round(stake * total_odd, 2)
        self._bets[bet_id] = {
            "bet_id": bet_id,
            "user": self._sessions[session_token]["user"],
            "legs": legs,
            "stake": stake,
            "placed_at": datetime.utcnow().isoformat(),
            "status": "ACCEPTED",
            "total_odd": round(total_odd, 2),
            "potential_return": potential_return
        }
        return {"bet_id": bet_id, "status": "ACCEPTED", "total_odd": round(total_odd,2), "potential_return": potential_return}

    def get_bet(self, bet_id: str) -> Dict[str, Any]:
        self._maybe_network_failure()
        if bet_id not in self._bets:
            raise MockAPIError("Bet not found")
        return self._bets[bet_id]

# ===== Helper utilities =====
def exponential_backoff(attempt: int) -> float:
    # attempt starts at 1
    return (RETRY_BACKOFF_BASE ** (attempt - 1)) + random.random() * 0.5

def retry_on_exception(fn, max_retries=MAX_RETRIES, *args, **kwargs):
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            wait = exponential_backoff(attempt)
            logger.warning("Attempt %d/%d failed: %s. Backing off %.2fs", attempt, max_retries, str(e), wait)
            time.sleep(wait)
    logger.error("All %d attempts failed. Last error: %s", max_retries, str(last_exc))
    raise last_exc

# ===== Match selection logic =====
def choose_matches(matches: List[Dict[str, Any]], mode: str = "top", max_legs: int = 4) -> List[Dict[str, Any]]:
    available = [m for m in matches if m.get("available", True) and m.get("odds", 0) >= MIN_ODDS]
    if not available:
        return []
    if mode == "random":
        random.shuffle(available)
        selected = available[:max_legs]
    elif mode == "from_feed":
        # placeholder: choose earliest starting matches
        available.sort(key=lambda m: m["start_time"])
        selected = available[:max_legs]
    else:  # 'top' or default: choose highest odds while keeping odds reasonable
        available.sort(key=lambda m: m["odds"], reverse=True)
        selected = available[:max_legs]
    return selected

# ===== Main Bot Flow =====
class AccumulatorBot:
    def __init__(self, api_client: MockBettingAPI, username: str, password: str):
        self.api = api_client
        self.username = username
        self.password = password
        self.session_token: Optional[str] = None

    def login(self):
        logger.info("Logging in as %s", self.username)
        token = retry_on_exception(self.api.authenticate, MAX_RETRIES, self.username, self.password)
        self.session_token = token
        logger.info("Authenticated, session token: %s", token)

    def build_accumulator(self, stake: float, mode: str = MATCH_SELECTION_MODE, legs_target: int = MAX_LEGS) -> Dict[str, Any]:
        logger.info("Fetching matches for accumulator build (mode=%s, legs=%d)", mode, legs_target)
        matches = retry_on_exception(self.api.get_available_matches, MAX_RETRIES)
        selected = choose_matches(matches, mode, legs_target)
        if not selected or len(selected) < 2:
            raise RuntimeError("Not enough valid legs available to form an accumulator")
        logger.info("Selected legs: %s", [m["match_id"] for m in selected])
        # transform legs into placement payload
        legs_payload = [{"match_id": m["match_id"], "selection": m["teams"][0]+" vs "+m["teams"][1], "odds": m["odds"], "available": m["available"]} for m in selected]
        return {"legs": legs_payload, "stake": stake}

    def place_accumulator(self, placement: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session_token:
            raise RuntimeError("Not authenticated")
        logger.info("Placing accumulator with stake %s on %d legs", placement["stake"], len(placement["legs"]))
        result = retry_on_exception(self.api.place_accumulator, MAX_RETRIES, self.session_token, placement["legs"], placement["stake"])
        logger.info("Placement result: %s", result)
        return result

    def confirm_bet(self, bet_id: str) -> Dict[str, Any]:
        logger.info("Confirming bet id %s", bet_id)
        info = retry_on_exception(self.api.get_bet, MAX_RETRIES, bet_id)
        logger.info("Bet info: %s", info)
        return info

    def run_once(self, stake: float = DEFAULT_STAKE):
        try:
            self.login()
            placement = self.build_accumulator(stake)
            placement_result = self.place_accumulator(placement)
            bet_id = placement_result.get("bet_id")
            if not bet_id:
                logger.error("No bet_id returned from placement")
                return
            bet_info = self.confirm_bet(bet_id)
            # final reporting — write to console and log file
            logger.info("FINAL: bet_id=%s stake=%.2f total_odd=%s potential_return=%s", bet_info["bet_id"], bet_info["stake"], bet_info["total_odd"], bet_info["potential_return"])
            # persist to a local JSON log
            self._persist_bet(bet_info)
        except Exception as e:
            logger.exception("Run failed: %s", e)

    def _persist_bet(self, bet_info: Dict[str, Any]):
        out_file = "placed_bets.jsonl"
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(bet_info, default=str) + "\n")
        logger.info("Persisted bet to %s", out_file)

# ===== If used as a scheduled script, support simple locking to avoid overlapping runs =====
LOCKFILE = "accumulator_bot.lock"
def acquire_lock(timeout=0):
    if os.path.exists(LOCKFILE):
        return False
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))
    return True

def release_lock():
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
    except Exception:
        pass

# ===== CLI entrypoint =====
def main():
    if not acquire_lock():
        logger.error("Another instance appears to be running. Exiting.")
        return
    try:
        api = MockBettingAPI()
        bot = AccumulatorBot(api, USERNAME, PASSWORD)
        logger.info("Starting accumulator bot run at %s", datetime.utcnow().isoformat())
        bot.run_once()
        logger.info("Run completed")
    finally:
        release_lock()

if __name__ == "__main__":
    main()
