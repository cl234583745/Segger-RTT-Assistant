import os
src = os.path.join(os.path.dirname(__file__), "更新说明.md")
dst = os.path.join(os.path.dirname(__file__), "Changelog.md")
with open(src, "r", encoding="utf-8") as f:
    c = f.read()

# Replacement pairs
R = []
def a(o, n): R.append((o, n))
a("   - 根因：`ch.read(length=1024)` 硬编码截断，MCU 20条日志约1100字节超过1024B，一次读不完导致日志行在1024B边界截断", "   - Root cause: `ch.read(length=1024)` hardcoded truncation; MCU 20 log lines ~1100 bytes exceed 1024B, incomplete read in one call causes log lines truncated at 1024B boundary")

for o, n in R:
    c = c.replace(o, n)
with open(dst, "w", encoding="utf-8") as f:
    f.write(c)
print("Done:", len(c))
