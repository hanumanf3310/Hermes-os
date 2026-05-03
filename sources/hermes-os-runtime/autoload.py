#!/usr/bin/env python3
"""
Hermes OS Auto-Loader

This script automatically loads Hermes OS skill on Hermes startup.
Should be called from Hermes initialization (or manually on startup).
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HERMES_SKILLS_DIR = Path.home() / ".hermes" / "skills"
SKILL_NAME = "hermes-os-integration"


def auto_load_hermes_os():
    """
    Auto-load Hermes OS skill if in hermes_os mode.

    Returns:
        True if skill loaded or already active
    """
    # Check if Hermes OS mode is active
    state_file = Path.home() / ".hermes" / "state" / "hermes-os.json"

    if not state_file.exists():
        logger.info("[Auto-Load] Hermes OS state not found, skipping auto-load")
        return False

    try:
        state = json.loads(state_file.read_text())
        mode = state.get("mode", "hermes_off")

        if mode != "hermes_os":
            logger.info(f"[Auto-Load] Mode is {mode}, not auto-loading")
            return False

        # Check skill exists
        skill_dir = HERMES_SKILLS_DIR / SKILL_NAME
        if not skill_dir.exists():
            logger.warning(f"[Auto-Load] Skill directory not found: {skill_dir}")
            return False

        # Try to load skill
        sys.path.insert(0, str(skill_dir))
        try:
            from skill import load_skill
            skill = load_skill()

            if skill.is_active():
                logger.info("[Auto-Load] ✅ Hermes OS skill auto-loaded successfully")
                return True
            else:
                logger.warning("[Auto-Load] Skill loaded but Hermes OS mode not active")
                return False

        except Exception as e:
            logger.error(f"[Auto-Load] Failed to load skill: {e}")
            return False

    except Exception as e:
        logger.error(f"[Auto-Load] Error: {e}")
        return False


if __name__ == "__main__":
    # Can be called from command line
    success = auto_load_hermes_os()
    sys.exit(0 if success else 1)
