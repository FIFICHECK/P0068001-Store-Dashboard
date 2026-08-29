#!/usr/bin/env bash
# ============================================================
# secret-guard.sh — pre-commit 防洩漏檢查（Discord webhook 等）
# 用法: 由 .git/hooks/pre-commit 呼叫; 直接跑都得 (bash scripts/secret-guard.sh)
# 2026-08-28: 因為 webhook token 曾經寫咗入公開 repo 俾 spammer 濫用
# ============================================================
set -u

# 檢查對象: 已 staged 嘅檔案
FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)

if [ -z "$FILES" ]; then
  exit 0
fi

# pattern list: 中咗任何一個 → 拒絕 commit
PATTERNS=(
  'discord(app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]{10,}'   # 真實 Discord webhook URL (有 token)
  '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'             # 私鑰
  'AKIA[0-9A-Z]{16}'                                             # AWS access key
  'ghp_[A-Za-z0-9]{36}'                                          # GitHub PAT
)

# 白名單: 設計上公開嘅 webhook（前端必須直接 POST）— token 一定要喺前端檔案
# 1. Access-Gate webhook (WEBHOOK_ID_REDACTED) — 已刪除，保留做記錄
# 2. Access-Approver (WEBHOOK_ID_REDACTED) — approve.html 用，收「批准訪問」請求
# ⚠️ 只有呢啲 webhook 可以公開；其他 webhook (MMS-Updater 等) 一律照擋
ALLOWLIST_WEBHOOK_IDS=('WEBHOOK_ID_REDACTED' 'WEBHOOK_ID_REDACTED')

FAIL=0
for f in $FILES; do
  [ -f "$f" ] || continue
  for p in "${PATTERNS[@]}"; do
    if grep -qE "$p" "$f" 2>/dev/null; then
      # 檢查係咪白名單 webhook
      ALLOWED=0
      for wid in "${ALLOWLIST_WEBHOOK_IDS[@]}"; do
        if grep -qE "discord(app)?\.com/api/webhooks/$wid/" "$f" 2>/dev/null; then
          ALLOWED=1
        fi
      done
      # 如果檔案同時含有白名單 webhook 同其他 webhook → 仍然要擋
      OTHER=$(grep -oE 'discord(app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]{10,}' "$f" 2>/dev/null | grep -vE "^discord(app)?\.com/api/webhooks/(${ALLOWLIST_WEBHOOK_IDS[*]// /|})/" | wc -l)
      if [ "$ALLOWED" -eq 1 ] && [ "$OTHER" -eq 0 ]; then
        echo "ℹ️ [secret-guard] $f 只有 Access-Gate 白名單 webhook（公開申請通道）— 允許"
        continue
      fi
      echo "❌ [secret-guard] $f 含有疑似 secret (pattern: $p)"
      echo "   commit 已拒絕。請移除 secret，改用 config/env 檔（並確保 gitignored）。"
      FAIL=1
    fi
  done
done

# 順帶檢查: 有冇人手滑 commit 咗 *webhook* 名嘅檔案
for f in $FILES; do
  if echo "$f" | grep -qiE 'webhook|\.env$'; then
    echo "⚠️ [secret-guard] $f 檔名似 secret 檔（webhook/env）— 確認冇 token 先好 commit"
  fi
done

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
