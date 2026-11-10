# 補助金ウォッチ Ver.1

対象：長野県伊那市の個人事業主、食品製造業、従業員0人。2022年に商工会の小規模事業者持続化補助金採択歴あり。

## Windowsで最初に試す

1. ZIPを展開し、フォルダを開く。
2. Python 3.10以上が利用できる場合、フォルダのアドレス欄に `cmd` と入力してEnter。
3. `py collector.py` を実行。`docs/data.json` が作成される。
4. 同じ画面で `py -m http.server 8000 --directory docs` を実行。
5. ブラウザで `http://localhost:8000` を開く。終了時はコマンド画面で Ctrl+C。

Pythonが見つからない場合はインストールが必要です。APIへの接続に失敗した場合はエラーメッセージを確認してください。データ取得に失敗しても既存のdata.jsonは上書きしません。

## GitHub Pagesでスマホから閲覧する

1. GitHubに新しいリポジトリを作成（公開設定に注意）。このフォルダの中身をルートへアップロード。
2. リポジトリの Settings → Pages → Build and deployment で `Deploy from a branch`、`main`、`/docs` を選択して保存。
3. Actions → Update subsidies → Run workflow を実行し、成功を確認。
4. PagesのURLをスマートフォンで開く。毎日07:17 JST頃に自動更新予定（GitHub Actionsの遅延あり）。

Actionsの書き込み権限が不足する場合は Settings → Actions → General → Workflow permissions の設定を確認してください。リポジトリ保護設定によっては自動コミットできないことがあります。

## 重要な制限

- Jグランツ公式APIの検索結果に基づく候補抽出であり、全補助金の網羅性は保証しません。
- **雇用・賃上げ・インボイス・創業年数・過去採択の制限は、APIの一覧情報だけでは完全に判定できません。** 判定ラベルは申請可能性の保証ではありません。
- 地域条件が未掲載の場合は除外せず残します。文字列の地域判定は暫定的です。
- Jグランツへのリンク形式・APIの応答仕様は本番環境で確認が必要です。
- 公式APIへの直接通信はこの作成環境では成功していないため、実データでの動作は未検証です。
- `data.json` は初回収集まで存在しません。収集失敗時に架空の補助金を表示しない設計です。
- API利用規約に従って利用してください。収集元はデジタル庁のJグランツです。

## テスト

`py -m unittest discover -s tests -v`

## 出典

- https://developers.digital.go.jp/documents/jgrants/api/
- https://fs2.jgrants-portal.go.jp/API利用概要.pdf
