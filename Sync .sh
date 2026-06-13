#!/bin/bash
# sync.sh - 在VM上同步GitHub repo並執行評分腳本
#
# 第一次使用：
#   1. 把 REPO_URL 換成你的GitHub repo網址
#   2. chmod +x sync.sh
#   3. ./sync.sh

set -e

REPO_URL="https://github.com/你的帳號/你的repo.git"
REPO_DIR=~/credit-dashboard

if [ -d "$REPO_DIR/.git" ]; then
    echo "=== 已存在，git pull更新 ==="
    cd "$REPO_DIR" && git pull
else
    echo "=== 第一次，git clone ==="
    git clone "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

pip3 install pymysql --break-system-packages -q

echo ""
echo "=== 先跑5筆樣本測試 ==="
python3 batch_scoring.py --sample 5
