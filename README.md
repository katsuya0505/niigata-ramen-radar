# 新潟ラーメンレーダー v0.3

## v0.3 の方針

v0.2 は「ラーメン関連記事」を広く拾っていましたが、
v0.3 は **街の変化だけを検知するRADAR** に変更しました。

掲載対象:
- NEW OPEN
- OPENING SOON
- LIMITED
- CLOSED
- RELOCATION
- RENEWAL

原則として掲載しないもの:
- おすすめ○選
- まとめ記事
- 食べ歩き
- 普通の店舗紹介
- ランキング
- 特集
- NGT48らーめん部などの企画記事

## 主な改善

- サンプル・デモデータを完全削除
- `NEW` の誤判定を抑制
- タイトルの変化語を優先して分類
- 店名抽出を改善
- 文字化け判定を追加
- 既存の誤判定データを次回実行時に除外
- `policy: change-only` をJSONに保存

## GitHubへの反映

既存リポジトリで以下を置き換えてください。

- `collector.py`
- `data/ramen.json`
- `app.js`
- `index.html`

またはv0.3の中身をリポジトリに上書きしてください。

既存の `.github/workflows/update-radar.yml` はそのまま使えます。

アップロード後:

1. GitHub → Actions
2. Update Ramen Radar
3. Run workflow
4. 緑チェックを待つ
5. `data/ramen.json` を確認

`meta.version` が `0.3`、
`meta.policy` が `change-only`
になっていれば新バージョンです。
