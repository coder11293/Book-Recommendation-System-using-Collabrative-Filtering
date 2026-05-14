# setup_database.py
# ========== DATA FILE SETUP - RUN THIS ONCE ==========

from pathlib import Path

# Data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.csv"
LIKES_FILE = DATA_DIR / "likes.csv"
DISLIKES_FILE = DATA_DIR / "dislikes.csv"

print("📁 Setting up data files...")

# Create users.csv
if not USERS_FILE.exists():
    with open(USERS_FILE, 'w', newline='', encoding='utf-8') as f:
        f.write('username,password,created_at,last_login\n')
    print("✅ users.csv created")
else:
    print("✅ users.csv already exists")

# Create likes.csv
if not LIKES_FILE.exists():
    with open(LIKES_FILE, 'w', newline='', encoding='utf-8') as f:
        f.write('username,book_title,liked_at\n')
    print("✅ likes.csv created")
else:
    print("✅ likes.csv already exists")

# Create dislikes.csv
if not DISLIKES_FILE.exists():
    with open(DISLIKES_FILE, 'w', newline='', encoding='utf-8') as f:
        f.write('username,book_title,disliked_at\n')
    print("✅ dislikes.csv created")
else:
    print("✅ dislikes.csv already exists")

print("\n🎉 Setup complete!")
print("   - Data will be stored in CSV files in the 'data/' folder")
print("   - users.csv: stores user accounts")
print("   - likes.csv: stores liked books")
print("   - dislikes.csv: stores disliked books")