# Gateway `.pyc` Cache Reload Caveat

## Problem

Hermes Gateway ใช้ Python compile cache (`.pyc` files ใน `__pycache__` directories) เพื่อความเร็ว แต่เมื่อเราแก้ไข source `.py` file:

1. ถ้า timestamp ของ `.pyc` ใหม่กว่า `.py` → Python ใช้ `.pyc` เก่า (code ก่อนแก้)
2. ถ้า `.pyc` หายไป → Python recompile จาก `.py` ใหม่ (ใช้ code ล่าสุด)
3. ถ้า systemd restart เร็วเกินไป Python อาจยังไม่ detect `.py` เปลี่ยน

## Symptoms

- Edit `.py` แล้ว restart gateway แต่ log ยังแสดง error เดิม
- Error line number ไม่ตรงกับ file บนดิสก์
- หรือ function ที่เพิ่มไปไม่ทำงาน

## Evidence from 2025-05-03 Session

Timestamp หลังแก้ไข gateway/run.py:
```
$ ls -la gateway/run.py
May 3 15:30 /home/.../gateway/run.py   ← แก้ไข ~15:29

$ ls -la gateway/__pycache__/run.cpython-311.pyc
May 3 15:25 /home/.../gateway/__pycache__/run.cpython-311.pyc
  ← เก่ากว่า .py แต่ยังอยู่ ทำให้ Python อาจ load .pyc เก่า
```

ผลลัพธ์: Gateway restart แล้วยังอาจใช้โค้ดก่อนแก้ไข ทำให้ยัง crash จาก error เดิม

## Safe Reload Procedure After Code Edits

```bash
# 1. Kill existing gateway process เพื่อหยุด service ปัจจุบัน
bash -c 'kill $(pidof python3 -m hermes_cli.main gateway run --replace)' 2>/dev/null || true

# 2. Clear .pyc cache ของ file ที่แก้ไข
find ~/.hermes/hermes-agent/gateway/__pycache__ -name "run*.pyc" -delete

# 3. ตรวจสอบว่า .pyc หายไปแล้ว
ls ~/.hermes/hermes-agent/gateway/__pycache__/run*.pyc 2>/dev/null || echo "pyc cleared"

# 4. Start gateway service (systemd จะสร้าง .pyc ใหม่จาก .py ล่าสุด)
systemctl --user start hermes-gateway.service

# 5. Verify process started และ .pyc สร้างใหม่แล้ว
sleep 3
systemctl --user is-active hermes-gateway.service
ls -la ~/.hermes/hermes-agent/gateway/__pycache__/run.cpython-311.pyc
```

## Alternative: Force Recompile Without Restart

ถ้าไม่ต้องการ restart gateway (เช่น แก้ module ที่ยังไม่ถูก import):
```bash
python3 -c "import py_compile; py_compile.compile('path/to/file.py', doraise=True)"
```

แต่สำหรับ gateway process ที่รันอยู่แล้ว ต้อง restart ถึงจะ load code ใหม่

## Key Takeaways

1. **Always clear `.pyc` cache ก่อน restart** หลังแก้ไขโค้ดที่ gateway ใช้
2. **Verify by timestamp**: ตรวจสอบว่า `.pyc` ใหม่กว่า `.py` จริง
3. **Use `find -delete`** แทน `rm` เพื่อไม่พลาดถ้า filename pattern ไม่ตรง
4. **Check journal immediately** หลัง restart สำหรับ compile/import error ใหม่

## Related

- `hermes-os` skill: Troubleshooting section
- `systematic-debugging` skill: Cache/timing issues
- `hermes-admin-package-approval` skill: WSL/sudo patterns
