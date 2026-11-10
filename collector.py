"""Jグランツ公開APIから補助金候補を収集する（標準ライブラリのみ）。"""
import datetime as dt
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'docs' / 'data.json'
BASE = 'https://api.jgrants-portal.go.jp/exp/v1/public/subsidies'
KEYWORDS = ['設備', '省エネ', '商品開発', '改修', 'IT', '食品', '販路', '製造', '小規模']
TOPICS = ['設備', '機械', '省エネ', '省力', '商品開発', '新商品', '改修', '施設', 'IT', 'デジタル', '食品', '製造', '販路', '持続化', '生産性']
EMPLOYMENT = ['新規雇用', '雇用創出', '雇用増加', '従業員の賃上げ', '給与総額', '賃金引上げ', '賃上げ']
EXCLUDE = ['東京都内限定', '大阪府内限定']


def fetch(keyword):
    query = urllib.parse.urlencode({'keyword': keyword, 'sort': 'created_date', 'order': 'DESC', 'acceptance': 1})
    req = urllib.request.Request(BASE + '?' + query, headers={'User-Agent': 'SubsidyWatch/1.0 (personal research)', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def classify(record):
    title = str(record.get('title') or '')
    area = str(record.get('target_area_search') or '')
    employees = str(record.get('target_number_of_employees') or '')
    institution = str(record.get('institution_name') or '')
    combined = ' '.join([title, institution])
    reasons = []
    if area and not any(w in area for w in ('全国', '長野', '伊那', '全地域', '日本全国', '指定なし')):
        return '対象地域外の可能性', ['対象地域の記載を確認してください']
    if re.search(r'(?:[1-9][0-9]*|[一二三四五])\s*(?:名|人)\s*以上', employees) and not re.search(r'(?:以下|以内)', employees):
        return '雇用条件に注意', ['従業員数の下限がある可能性があります']
    if any(w in combined for w in EMPLOYMENT):
        return '雇用条件に注意', ['雇用・賃上げ要件を公募要領で確認してください']
    if employees:
        reasons.append('従業員条件: ' + employees)
    else:
        reasons.append('従業員条件は一覧情報で未確認')
    if any(w.lower() in combined.lower() for w in TOPICS):
        return '有力候補・要確認', reasons + ['関心分野と関連する可能性があります']
    return '要確認', reasons


def normalize(record):
    status, reasons = classify(record)
    return {
        'id': str(record.get('id') or ''),
        'title': str(record.get('title') or '名称不明'),
        'institution': str(record.get('institution_name') or ''),
        'area': str(record.get('target_area_search') or ''),
        'employees': str(record.get('target_number_of_employees') or ''),
        'maximum': record.get('subsidy_max_limit'),
        'start': str(record.get('acceptance_start_datetime') or ''),
        'end': str(record.get('acceptance_end_datetime') or ''),
        'status': status,
        'reasons': reasons,
        'url': 'https://www.jgrants-portal.go.jp/subsidy/' + urllib.parse.quote(str(record.get('id') or '')),
    }


def collect():
    found, failures = {}, []
    for word in KEYWORDS:
        try:
            payload = fetch(word)
            results = payload.get('result', [])
            if not isinstance(results, list):
                raise ValueError('API result is not a list')
            for item in results:
                if isinstance(item, dict) and item.get('id'):
                    found[str(item['id'])] = item
        except Exception as exc:
            failures.append(f'{word}: {type(exc).__name__}: {exc}')
        time.sleep(0.2)
    if not found:
        raise RuntimeError('取得件数0件。既存データを保持します。 ' + '; '.join(failures))
    records = [normalize(v) for v in found.values()]
    records.sort(key=lambda x: (x['status'] != '有力候補・要確認', x['end'] or '9999', x['title']))
    data = {'updated_at': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds'),
            'source': 'Jグランツ（デジタル庁）公開API', 'total': len(records),
            'partial': bool(failures), 'errors': failures, 'items': records}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(OUT)
    print(f'保存完了: {len(records)}件 / エラー {len(failures)}件')


if __name__ == '__main__':
    collect()
