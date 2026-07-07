"""
scripts/sync_sheets.py

從 Google Sheets 抓取 HLDDru（Haiang Learner's Dictionary of Rukai）的詞典資料，
輸出成 data/*.csv，供 index.html 在瀏覽器端 fetch 使用。

執行方式：由 GitHub Actions 排程呼叫（見 .github/workflows/sync-sheets.yml），
使用 Service Account 憑證讀取 Sheets API，不需要互動式登入。

新增第2/3/4份資料時，只要在下方 SHEETS 這個清單多加一筆設定即可，
不需要更動其餘程式碼。
"""

import csv
import json
import os
import sys

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

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
    # 之後其餘3份資料的欄位結構確認後，比照這個格式加進來，例如：
    # {
    #     'id_env': 'SPREADSHEET_ID_2',
    #     'sheet_name': '工作表1',
    #     'output': 'data/xx-XXX.csv',
    # },
]


def get_credentials():
    raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')
    if not raw:
        print('錯誤：找不到環境變數 GCP_SERVICE_ACCOUNT_KEY', file=sys.stderr)
        sys.exit(1)
    info = json.loads(raw)
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def fetch_sheet_values(service, spreadsheet_id, sheet_name):
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name,
        valueRenderOption='UNFORMATTED_VALUE',
    ).execute()
    return result.get('values', [])


def write_csv(values, output_path):
    if not values:
        print(f'  ⚠ 沒有資料，略過寫入 {output_path}')
        return

    header = values[0]
    col_count = len(header)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in values:
            # Sheets API 會省略每列尾端的空白儲存格，補齊到跟表頭一樣的欄數，
            # 確保空白欄（例如 08-Lemmata 裡標示 ne 的那一欄）不會被吃掉。
            padded = row + [''] * (col_count - len(row))
            writer.writerow([str(c) for c in padded[:col_count]])

    print(f'  ✓ 寫入 {output_path}（{len(values) - 1} 筆資料列）')


def main():
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)

    for sheet_cfg in SHEETS:
        spreadsheet_id = os.environ.get(sheet_cfg['id_env'])
        if not spreadsheet_id:
            print(f"  ⚠ 找不到環境變數 {sheet_cfg['id_env']}，略過此份資料")
            continue

        print(f"同步 {sheet_cfg['output']} ← Sheet({sheet_cfg['id_env']})...")
        values = fetch_sheet_values(service, spreadsheet_id, sheet_cfg['sheet_name'])
        write_csv(values, sheet_cfg['output'])


if __name__ == '__main__':
    main()
