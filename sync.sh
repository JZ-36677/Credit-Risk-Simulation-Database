#!/bin/bash
# sync.sh - 用GitHub token拉取private repo並執行評分腳本
#
# 第一次設定：
#   1. 編輯下面的 REPO_PATH（改成 你的帳號/repo名稱）
#   2. 建立token檔案（注意：這個檔案放在repo外面，不要commit進去）
#        echo "你的github_token" > ~/.github_token
#        chmod 600 ~/.github_token
#   3. chmod +x sync.sh
#   4. ./sync.sh

set -e

REPO_PATH="你的帳號/你的repo"          # 例如 aaa0970067608/credit-dashboard
REPO_DIR=~/credit-dashboard
TOKEN_FILE=~/.github_token

if [ ! -f "$TOKEN_FILE" ]; then
    echo "錯誤：找不到 $TOKEN_FILE"
    echo "請先執行： echo \"你的token\" > ~/.github_token && chmod 600 ~/.github_token"
    exit 1
fi

TOKEN=$(tr -d '[:space:]' < "$TOKEN_FILE")
REMOTE_URL="https://${TOKEN}@github.com/${REPO_PATH}.git"

if [ -d "$REPO_DIR/.git" ]; then
    echo "=== git pull更新 ==="
    cd "$REPO_DIR"
    git remote set-url origin "$REMOTE_URL"
    git pull
else
    echo "=== git clone ==="
    git clone "$REMOTE_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

pip3 install pymysql --break-system-packages -q

echo ""
echo "=== 先跑5筆樣本測試 ==="
python3 batch_scoring.py --sample 5
