"""
Codex Rate Limit Tracker
Read session data from Codex CLI (Windows) and format for display
"""

import json
import os
import glob
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# ============ FUTURE FEATURE FLAGS ============
# เปิด/ปิด ฟีเจอร์ที่จะใช้ในอนาคต
ENABLE_TOTAL_STATS = False  # << ปิดไว้ตอนนี้ เปลี่ยนเป็น True เมื่อต้องการใช้งาน
# ==============================================


class CodexRateLimitTracker:
    """Track Codex CLI rate limits from session files."""

    def __init__(self, sessions_path: str = None):
        # Priority: Linux sessions first (correct data), then Windows (fallback)
        linux_path = os.path.expanduser("~/.codex/sessions")
        windows_path = "/mnt/c/Users/User/.codex/sessions"

        if sessions_path:
            self.sessions_path = sessions_path
        elif os.path.exists(linux_path) and any(os.listdir(linux_path)):
            self.sessions_path = linux_path
        else:
            self.sessions_path = windows_path

        self.enable_totals = ENABLE_TOTAL_STATS

    def get_latest_session_file(self) -> Optional[str]:
        """Find the most recent .jsonl session file for *today* only.

        This avoids accidentally surfacing stale data from yesterday's Codex
        sessions when no fresh session has been created yet.
        """
        if not os.path.exists(self.sessions_path):
            return None

        today = datetime.now().strftime("%Y/%m/%d")
        pattern = os.path.join(self.sessions_path, today, "*.jsonl")
        files = glob.glob(pattern)

        if not files:
            return None

        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]

    def parse_latest_data(self) -> Optional[Dict[str, Any]]:
        """Parse the latest session file for rate limit and token data"""
        session_file = self.get_latest_session_file()
        if not session_file:
            return None

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return None

        # Find the latest token_count event
        latest_data = None

        for line in reversed(lines):  # Start from newest
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                if event.get("type") == "event_msg":
                    payload = event.get("payload", {})
                    if payload.get("type") == "token_count":
                        latest_data = payload
                        break
            except json.JSONDecodeError:
                continue

        if not latest_data:
            return None

        # Extract rate limits
        rate_limits = latest_data.get("rate_limits", {})
        primary = rate_limits.get("primary", {})
        secondary = rate_limits.get("secondary", {})

        # Extract token info
        info = latest_data.get("info", {})
        token_usage = info.get("total_token_usage", {})
        context_window = info.get("model_context_window", 258400)

        tokens_used = token_usage.get("total_tokens", 0)
        try:
            tokens_used = int(tokens_used)
        except (TypeError, ValueError):
            tokens_used = 0
        tokens_used = max(0, tokens_used)
        if context_window:
            tokens_used = min(tokens_used, context_window)
            context_left_pct = round((1 - (tokens_used / context_window)) * 100)
            context_left_pct = max(0, min(100, context_left_pct))
        else:
            context_left_pct = 0

        # Calculate reset times
        now = datetime.now(timezone.utc)

        def format_reset_time(epoch_ts):
            if not epoch_ts:
                return "unknown"
            try:
                reset_dt = datetime.fromtimestamp(epoch_ts, tz=timezone.utc)
                # Convert to Bangkok time (UTC+7)
                reset_local = reset_dt.astimezone(timezone(timedelta(hours=7)))

                # Always show clear time format: "12:01 AM" or "12:37 PM"
                return reset_local.strftime("%I:%M %p")
            except:
                return "unknown"

        from datetime import timedelta

        data = {
            "context_used": tokens_used,
            "context_window": context_window,
            "context_left_pct": context_left_pct,
            "used_5h_pct": max(0, min(100, int(primary.get("used_percent", 0) or 0))),
            "left_5h_pct": 100 - max(0, min(100, int(primary.get("used_percent", 0) or 0))),
            "reset_5h": format_reset_time(primary.get("resets_at")),
            "used_7d_pct": max(0, min(100, int(secondary.get("used_percent", 0) or 0))),
            "left_7d_pct": 100 - max(0, min(100, int(secondary.get("used_percent", 0) or 0))),
            "reset_7d": format_reset_time(secondary.get("resets_at")),
            "plan_type": rate_limits.get("plan_type", "unknown"),
        }

        # ========== FUTURE STATS (DISABLED) ==========
        if self.enable_totals:
            # คำนวณ Total sessions และ Total tokens วันนี้
            today_sessions = self._count_today_sessions()
            today_tokens = self._sum_today_tokens()
            data["total_sessions_today"] = today_sessions
            data["total_tokens_today"] = today_tokens
        # =============================================

        return data

    # ========== FUTURE METHODS (DISABLED) ==========
    def _count_today_sessions(self) -> int:
        """Count sessions created today - DISABLED"""
        # Implementation ready but not used
        return 0  # Placeholder

    def _sum_today_tokens(self) -> int:
        """Sum tokens used today - DISABLED"""
        # Implementation ready but not used
        return 0  # Placeholder
    # =============================================

    def format_telegram(self, data: Dict[str, Any]) -> str:
        """Format data for Telegram (with emojis)"""
        if not data:
            return "❌ ไม่พบข้อมูล Codex Session\nโปรดตรวจสอบว่าเคยใช้ Codex CLI ในวันนี้หรือไม่"

        # Status indicator
        if data["context_left_pct"] > 50:
            status_emoji = "🟢"
        elif data["context_left_pct"] > 20:
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"

        lines = [
            "🤖 **Codex GPT Status**",
            "",
            f"📊 **Context Usage**",
            f"   {data['context_left_pct']}% เหลือ ({data['context_used']:,} / {data['context_window']:,} tokens)",
            f"   {status_emoji} สถานะ: {'ดี' if data['context_left_pct'] > 50 else 'ปานกลาง' if data['context_left_pct'] > 20 else 'เหลือน้อย'}",
            "",
            f"⏱️ **5h Limit** (รีเซ็ตทุก 5 ชั่วโมง)",
            f"   ใช้ไป: {data['used_5h_pct']:.0f}% (เหลือ {data['left_5h_pct']:.0f}%)",
            f"   ⏳ รีเซ็ต: {data['reset_5h']}",
            "",
            f"📅 **7d Limit** (รีเซ็ตทุก 7 วัน)",
            f"   ใช้ไป: {data['used_7d_pct']:.0f}% (เหลือ {data['left_7d_pct']:.0f}%)",
            f"   ⏳ รีเซ็ต: {data['reset_7d']}",
            "",
            f"💎 Plan: {data.get('plan_type', 'unknown').upper()}",
        ]

        # ========== FUTURE STATS (DISABLED) ==========
        if self.enable_totals and "total_sessions_today" in data:
            lines.extend([
                "",
                f"📈 **สถิติวันนี้**",
                f"   Sessions: {data['total_sessions_today']}",
                f"   Total tokens: {data['total_tokens_today']:,}",
            ])
        # =============================================

        return "\n".join(lines)

    def format_terminal(self, data: Dict[str, Any]) -> str:
        """Format data for Terminal (no emojis)"""
        if not data:
            return "Codex GPT Status\n\nError: No session data found.\nPlease use Codex CLI first."

        lines = [
            "Codex GPT Status",
            "",
            f"Context:        {data['context_left_pct']}% left ({data['context_used']:,} / {data['context_window']:,} tokens)",
            f"5h limit:       {data['used_5h_pct']:.0f}% used (resets {data['reset_5h']})",
            f"7d limit:       {data['used_7d_pct']:.0f}% used (resets {data['reset_7d']})",
            "",
            f"Plan: {data.get('plan_type', 'unknown')}",
        ]

        # ========== FUTURE STATS (DISABLED) ==========
        if self.enable_totals and "total_sessions_today" in data:
            lines.extend([
                "",
                f"Sessions today: {data['total_sessions_today']}",
                f"Tokens today:   {data['total_tokens_today']:,}",
            ])
        # =============================================

        return "\n".join(lines)
