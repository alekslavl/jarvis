from datetime import datetime

LOG_FILE = "bot_log.txt"

def log(user_id, action, content=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{now}] [USER {user_id}] {action}"
    if content:
        msg += f": {content}"
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
