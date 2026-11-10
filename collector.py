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


def describe(title):
    """タイトルから用途を推定。募集要領の要約ではない。"""
    categories = [
        ('商品開発', ('新商品', '商品開発', '新製品', '試作品', '研究開発')),
        ('販路開拓', ('販路', '展示会', '販売促進', '持続化補助金')),
        ('設備投資・省力化', ('設備投資', '省力化', '機械導入', '生産性向上', 'ものづくり補助金')),
        ('省エネ・改修', ('省エネ', '省エネルギー', '脱炭素', '改修')),
        ('IT・デジタル化', ('IT導入', 'デジタル化', 'DX', '情報化')),
    ]
    for label, words in categories:
        if any(w.lower() in title.lower() for w in words):
            return label + 'に関係する制度の可能性があります。対象経費・申請条件は未確認です。', label
    return '補助対象の内容はタイトルだけでは判断できません。公募要領の確認が必要です。', 'その他'


def classify(record):
    title = str(record.get('title') or '')
    area = str(record.get('target_area_search') or '')
    employees = str(record.get('target_number_of_employees') or '')
    description, category = describe(title)
    reasons = []
    # タイトルの自治体名は、広域の検索地域より優先する。
    if re.search(r'茅野市|諏訪市|松本市|長野市|飯田市|駒ヶ根市|岡谷市|塩尻市|安曇野市', title):
        return '対象外候補', ['伊那市以外の市町村向け制度の可能性があります'], description, category
    if '創業型' in title or '創業枠' in title:
        return '対象外候補', ['創業期間の要件に合わない可能性があります'], description, category
    # 特定産業・用途に限定した制度は「非表示候補」とする。完全除外はしない。
    narrow = ('紙パルプ', 'セメント', '鉄鋼', '重要鉱物', '農業機械', '建設機械',
              '鉄道事業', '船舶', '航空機', '難病患者', '介護施設', '医療機関',
              '保育所', '学校法人', '水産養殖', '外国出願', '天然ガス利用設備')
    if any(w in title for w in narrow):
        return '対象外候補', ['タイトルに食品加工業と異なる特定業種・用途の記載があります'], description, category
    if area and not any(w in area for w in ('全国', '長野', '伊那', '全地域', '日本全国', '指定なし')):
        return '対象外候補', ['対象地域に長野県・全国が見当たりません'], description, category
    if any(w in title for w in ('新規雇用', '雇用創出', '従業員の賃上げ', '賃金引上げ', '賃上げ')):
        return '条件に注意', ['雇用・賃上げ条件がある可能性があります'], description, category
    if re.search(r'(?:[1-9][0-9]*|[一二三四五])\s*(?:名|人)\s*以上', employees) and not re.search(r'(?:以下|以内)', employees):
        return '条件に注意', ['従業員数の下限がある可能性があります'], description, category
    if category != 'その他':
        reasons.append('用途が関心分野に近いとタイトルから推定')
        reasons.append('申請資格・対象経費は未確認')
        return '関連候補', reasons, description, category
    return '要確認', ['用途・対象業種が不明なため要確認'], description, category


def normalize(record):
    status, reasons, description, category = classify(record)
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
        'description': description,
        'category': category,
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
    records.sort(key=lambda x: (x['status'] != '関連候補', x['end'] or '9999', x['title']))
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
