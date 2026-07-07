"""
scripts/sync_sheets.py

從 Google Sheets 抓取 HLDDru（Haiang Learner's Dictionary of Rukai）的詞典資料，
輸出成 data/*.csv，供 index.html 在瀏覽器端 fetch 使用。

使用 gspread（而非 Sheets API 的 UNFORMATTED_VALUE）讀取儲存格「顯示文字」，
避免像方言代碼 07、08 這種需要保留前導零的欄位被讀成數字後把 0 吃掉。

執行方式：由 GitHub Actions 排程呼叫（見 .github/workflows/sync-sheets.yml），
使用 Service Account 憑證（GOOGLE_CREDENTIALS）讀取，不需要互動式登入。

新增第2/3/4份資料時，只要在下方 SHEETS 這個清單多加一筆設定即可，
不需要更動其餘程式碼。
"""

import csv
import json
import os
import sys

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
]

# ── 資料來源設定 ──────────────────────────────────────────────
# id_env    : 存放該 Sheet ID 的 GitHub Secret 名稱
# sheet_name: Google Sheet 內的分頁（工作表）名稱
# output    : 輸出到 repo 內的哪個檔案
SHEETS = [
    {
        'id_env': 'SPREADSHEET_ID_LEMMATA',
        'sheet_name': '08-Lemmata',
        'output': 'data/08-Lemmata.csv',
    },
    # 其餘3份資料（SENSES / EXAMPLES / ETYMOLOGY）欄位結構確認後，
    # 比照這個格式加進來，例如：
    # {
    #     'id_env': 'SPREADSHEET_ID_SENSES',
    #     'sheet_name': '(該檔案的分頁名稱)',
    #     'output': 'data/(該檔案輸出檔名).csv',
    # },
]


def get_client():
    raw = os.environ.get('GOOGLE_CREDENTIALS')
    if not raw:
        print('錯誤：找不到環境變數 GOOGLE_CREDENTIALS', file=sys.stderr)
        sys.exit(1)
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def fetch_sheet_values(gc, spreadsheet_id, sheet_name):
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_name)
    return ws.get_all_values()  # 保留儲存格顯示文字（含前導零），不轉型成數字


def write_csv(values, output_path):
    # 去掉尾端完全空白的列（Google Sheet 常見的格線殘留空列）
    while values and all(cell.strip() == '' for cell in values[-1]):
        values.pop()

    if not values:
        print(f'  ⚠ 沒有資料，略過寫入 {output_path}')
        return

    header = values[0]
    col_count = len(header)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in values:
            padded = row + [''] * (col_count - len(row))
            writer.writerow(padded[:col_count])

    print(f'  ✓ 寫入 {output_path}（{len(values) - 1} 筆資料列）')


def main():
    gc = get_client()

    for sheet_cfg in SHEETS:
        spreadsheet_id = os.environ.get(sheet_cfg['id_env'])
        if not spreadsheet_id:
            print(f"  ⚠ 找不到環境變數 {sheet_cfg['id_env']}，略過此份資料")
            continue

        print(f"同步 {sheet_cfg['output']} ← Sheet({sheet_cfg['id_env']})...")
        values = fetch_sheet_values(gc, spreadsheet_id, sheet_cfg['sheet_name'])
        write_csv(values, sheet_cfg['output'])


if __name__ == '__main__':
    main()
