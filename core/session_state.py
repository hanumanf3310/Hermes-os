"""
Hermes Session State System
ระบบเก็บสถานะ session ของ Hermes แบบ 4-field model
inspired by Claude OS

Dependencies: None (stdlib only)

Author: Hermes OS
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class ProjectContext:
    """Context เกี่ยวกับโปรเจกต์ที่ทำงานอยู่"""
    repo: str = ""
    active_files: List[str] = None
    
    def __post_init__(self):
        if self.active_files is None:
            self.active_files = []


@dataclass
class SessionState:
    """
    สถานะ session แบบง่าย 4 fields (inspired by Claude OS)
    + extensions สำหรับ Hermes
    """
    session_id: str = ""
    last_task: str = ""
    last_branch: str = ""
    stopped_at: str = ""  # ISO format
    one_liner: str = ""  # สรุปสั้นๆ ว่าทำอะไรค้างไว้
    
    # Hermes extensions
    project_context: ProjectContext = None
    pending_items: List[str] = None
    
    def __post_init__(self):
        if self.project_context is None:
            self.project_context = ProjectContext()
        if self.pending_items is None:
            self.pending_items = []
    
    @property
    def is_fresh(self) -> bool:
        """เช็คว่า session ยัง fresh อยู่หรือไม่ (< 24 ชั่วโมง)"""
        if not self.stopped_at:
            return False
        try:
            stopped = datetime.fromisoformat(self.stopped_at)
            return datetime.now() - stopped < timedelta(hours=24)
        except:
            return False
    
    @property
    def age_hours(self) -> float:
        """คืนค่าจำนวนชั่วโมงที่ผ่านมาตั้งแต่จบ session"""
        if not self.stopped_at:
            return float('inf')
        try:
            stopped = datetime.fromisoformat(self.stopped_at)
            return (datetime.now() - stopped).total_seconds() / 3600
        except:
            return float('inf')
    
    def to_dict(self) -> Dict[str, Any]:
        """แปลงเป็น dict สำหรับบันทึกเป็น JSON"""
        return {
            "session_id": self.session_id,
            "last_task": self.last_task,
            "last_branch": self.last_branch,
            "stopped_at": self.stopped_at,
            "one_liner": self.one_liner,
            "project_context": {
                "repo": self.project_context.repo,
                "active_files": self.project_context.active_files
            },
            "pending_items": self.pending_items
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """สร้าง SessionState จาก dict"""
        state = cls()
        state.session_id = data.get("session_id", "")
        state.last_task = data.get("last_task", "")
        state.last_branch = data.get("last_branch", "")
        state.stopped_at = data.get("stopped_at", "")
        state.one_liner = data.get("one_liner", "")
        
        # Parse project_context
        pc_data = data.get("project_context", {})
        state.project_context = ProjectContext(
            repo=pc_data.get("repo", ""),
            active_files=pc_data.get("active_files", [])
        )
        
        state.pending_items = data.get("pending_items", [])
        return state
    
    def get_summary(self) -> str:
        """สร้างข้อความสรุปสำหรับแสดงผล"""
        if not self.last_task:
            return "No previous session"
        
        age_text = f"({self.age_hours:.1f} hours ago)" if self.age_hours < 24 else "(over 24 hours ago)"
        
        lines = [
            f"📋 Last Task: {self.last_task} {age_text}",
        ]
        
        if self.last_branch:
            lines.append(f"   Branch: {self.last_branch}")
        
        if self.one_liner:
            lines.append(f"   Status: {self.one_liner}")
        
        if self.pending_items:
            lines.append(f"   ⏳ Pending: {len(self.pending_items)} items")
        
        return "\n".join(lines)


class SessionManager:
    """จัดการการอ่าน/เขียน session state"""
    
    def __init__(self, state_path: Optional[str] = None):
        """
        Args:
            state_path: Path ไปยัง session-state.json
                       ถ้าไม่ระบุ จะใช้ ~/.hermes/session-state.json
        """
        if state_path:
            self.state_path = Path(state_path)
        else:
            self.state_path = Path.home() / ".hermes" / "session-state.json"
        
        # สร้าง directory ถ้ายังไม่มี
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> SessionState:
        """โหลด session state จากไฟล์"""
        if not self.state_path.exists():
            return SessionState()
        
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SessionState.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ Failed to load session state: {e}")
            return SessionState()
    
    def save(self, state: SessionState) -> bool:
        """บันทึก session state ลงไฟล์"""
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Failed to save session state: {e}")
            return False
    
    def clear(self) -> bool:
        """ล้าง session state (ลบไฟล์)"""
        try:
            if self.state_path.exists():
                self.state_path.unlink()
            return True
        except Exception as e:
            print(f"❌ Failed to clear session state: {e}")
            return False
    
    def create_checkpoint(self, task: str, one_liner: str = "", 
                         branch: str = "", repo: str = "") -> SessionState:
        """สร้าง checkpoint/session state ใหม่"""
        state = SessionState(
            session_id=datetime.now().strftime("sess-%Y%m%d-%H%M%S"),
            last_task=task,
            last_branch=branch,
            stopped_at=datetime.now().isoformat(),
            one_liner=one_liner,
            project_context=ProjectContext(repo=repo),
            pending_items=[]
        )
        self.save(state)
        return state
    
    def add_pending(self, item: str) -> bool:
        """เพิ่ม pending item ใน session ปัจจุบัน"""
        state = self.load()
        if item not in state.pending_items:
            state.pending_items.append(item)
            return self.save(state)
        return True
    
    def remove_pending(self, item: str) -> bool:
        """ลบ pending item ออกจาก session"""
        state = self.load()
        if item in state.pending_items:
            state.pending_items.remove(item)
            return self.save(state)
        return True


# CLI Interface for testing
if __name__ == "__main__":
    import sys
    
    manager = SessionManager()
    
    if len(sys.argv) < 2:
        # Show current state
        state = manager.load()
        print(state.get_summary())
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "save":
        if len(sys.argv) < 4:
            print("Usage: python session_state.py save '<task>' '<one_liner>' [branch] [repo]")
            sys.exit(1)
        
        task = sys.argv[2]
        one_liner = sys.argv[3]
        branch = sys.argv[4] if len(sys.argv) > 4 else ""
        repo = sys.argv[5] if len(sys.argv) > 5 else ""
        
        state = manager.create_checkpoint(task, one_liner, branch, repo)
        print(f"✅ Saved session: {state.session_id}")
        print(state.get_summary())
    
    elif command == "clear":
        if manager.clear():
            print("✅ Session state cleared")
        else:
            print("❌ Failed to clear")
    
    elif command == "add-pending":
        if len(sys.argv) < 3:
            print("Usage: python session_state.py add-pending '<item>'")
            sys.exit(1)
        item = sys.argv[2]
        if manager.add_pending(item):
            print(f"✅ Added pending: {item}")
        else:
            print("❌ Failed to add")
    
    elif command == "show":
        state = manager.load()
        print(json.dumps(state.to_dict(), indent=2))
    
    else:
        print(f"Unknown command: {command}")
        print("Commands: save, clear, add-pending, show")
