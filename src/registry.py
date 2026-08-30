"""
registry.py — the bot catalogue.

Every bot declares its script, its risk tier, and the human name of each step.
The risk tier lives here rather than in the script because it is a property of
what the bot does to the business, not of how it is written.
"""

from pathlib import Path

from contracts import RISK_TIERS, ContractError, read_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "rpa-bots" / "bots.json"


def load_bots() -> dict:
    """Load and validate the bot registry."""
    bots = read_json(REGISTRY_PATH, default=None)
    if bots is None:
        raise FileNotFoundError(f"Bot registry not found at {REGISTRY_PATH}")

    for bot_id, bot in bots.items():
        if bot.get("risk_tier") not in RISK_TIERS:
            raise ContractError(
                f"Bot '{bot_id}' declares risk_tier={bot.get('risk_tier')!r}, "
                f"which is not one of {RISK_TIERS}"
            )
        bot["bot_id"] = bot_id
        bot["wal_path"] = str(PROJECT_ROOT / bot["wal"])
    return bots


def get_bot(bot_id: str) -> dict:
    """Look up one bot by id."""
    bots = load_bots()
    if bot_id not in bots:
        raise KeyError(f"Unknown bot '{bot_id}'. Known bots: {', '.join(bots)}")
    return bots[bot_id]


def step_names(bot: dict) -> dict:
    """Map ordinal step keys to human step ids for one bot."""
    return bot.get("steps", {})


def step_key_for(bot: dict, step_id: str) -> str | None:
    """Reverse lookup: human step id back to its ordinal key."""
    for key, name in bot.get("steps", {}).items():
        if name == step_id:
            return key
    return None


if __name__ == "__main__":
    for bot_id, bot in load_bots().items():
        print(f"{bot_id:<16} {bot['risk_tier']:<18} {bot['bot_name']}")
