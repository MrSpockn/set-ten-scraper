# セッテン記事ビューア

セッテンサイトから収集した記事データを閲覧するためのウェブアプリケーション。

## 機能

- 記事の一覧表示と詳細表示
- キーワード検索
- カテゴリーフィルター
- 管理画面からのデータ閲覧

## 技術スタック

- Python 3.12
- Django 5.2.1
- SQLite3 データベース
- HTML/CSS

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repository-url>
cd scraper-batch
```

2. 環境設定ファイルを準備
```bash
cp .env.example .env
# .envファイルを編集して適切な設定を行う
```

3. 必要なパッケージをインストール
```bash
pip install -r requirements.txt
```

4. マイグレーションを適用
```bash
python manage.py migrate
```

5. 開発サーバーを起動
```bash
python manage.py runserver
```

6. ブラウザで http://127.0.0.1:8000/ にアクセスして確認

## 使い方

1. ホームページから記事一覧を閲覧
2. 検索機能を使って特定の記事を検索
3. 記事タイトルをクリックして詳細表示
4. 元の記事にアクセスするには「元記事を見る」ボタンをクリック

## プロジェクト構造

- `setten_viewer/` - Djangoプロジェクト設定
- `articles/` - 記事表示用アプリケーション
  - `models.py` - データモデル
  - `views.py` - ビュー関数
  - `templates/` - HTMLテンプレート
  - `static/` - CSS、JavaScript等の静的ファイル

## 注意事項

- このアプリは既存のSQLiteデータベースを読み込む設定になっています
- クローラーによって収集されたデータのみを表示します（アプリからの記事追加は不可）

## ライセンス

MIT

## 作者

Your Name
