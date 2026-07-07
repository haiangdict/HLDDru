"""
sync_sheets.py
HLDDru 專用：從 4 個 Google Sheets（Lemmata / Senses / Examples / Etymology）
同步資料，輸出至 data/ 資料夾（CSV + JSON 兩種格式）。
"""

import os, json, csv
import gspread
from google.oauth2.service_account import Credentials

# ── Auth ──────────────────────────────────────────────────────
creds_json = json.loads(os.environ['GOOGLE_CREDENTIALS'])
scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
gc = gspread.authorize(creds)

# ── 試算表對照表：env 變數名 → (輸出檔名, 說明) ──────────────────
SHEETS = {
    'SPREADSHEET_ID_LEMMATA':   ('08-Lemmata',   '詞目表'),
    'SPREADSHEET_ID_SENSES':    ('08-Senses',    '義項表'),
    'SPREADSHEET_ID_EXAMPLES':  ('08-Examples',  '例句表'),
    'SPREADSHEET_ID_ETYMOLOGY': ('08-Etymology', '詞源表'),
}

os.makedirs('data', exist_ok=True)

for env_key, (out_name, desc) in SHEETS.items():
    sid = os.environ.get(env_key, '').strip()
    if not sid:
        print(f'⚠ {env_key} 未設定，略過（{desc}）')
        continue

    sh = gc.open_by_key(sid)
    ws = sh.sheet1
    rows = ws.get_all_values()

    if len(rows) < 2:
        print(f'⚠ {desc}：無資料')
        continue

    headers = rows[0]
    data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]

    # ── 寫入 CSV（保留與 Google Sheets 相同的欄位順序）──────────
    csv_path = f'data/{out_name}.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data_rows)
    print(f'✅ {csv_path}（{len(data_rows)} 筆）')

    # ── 寫入 JSON（只保留有值的欄位，縮小檔案體積；供日後功能使用）──
    records = []
    for row in data_rows:
        r = {}
        for i, h in enumerate(headers):
            v = row[i].strip() if i < len(row) else ''
            if v:
                r[h] = v
        records.append(r)

    json_path = f'data/{out_name}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, separators=(',', ':'))
    print(f'✅ {json_path}（{len(records)} 筆）')

print('\n🎉 HLDDru 資料同步完成')
