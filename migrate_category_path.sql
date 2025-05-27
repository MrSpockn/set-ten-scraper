-- カテゴリパスへの移行スクリプト

-- 一時的なバックアップテーブルの作成
CREATE TABLE articles_backup AS SELECT * FROM articles;

-- カラム名の変更（articles テーブル）
ALTER TABLE articles RENAME COLUMN category TO category_path;

-- カテゴリパス用の新しいカラムの追加
ALTER TABLE articles_backup ADD COLUMN category_path TEXT;

-- 既存のカテゴリデータをカテゴリパスに変換
UPDATE articles_backup 
SET category_path = category;

-- データを新テーブルに移行
INSERT INTO articles (
    id, title, url, post_date, updated_date, category_path,
    tags, content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, external_links,
    internal_links, frequent_words, broken_links, crawled_at
)
SELECT
    id, title, url, post_date, updated_date, category_path,
    tags, content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, external_links,
    internal_links, frequent_words, broken_links, crawled_at
FROM articles_backup;

-- 検証後に不要になったバックアップテーブルを削除
-- DROP TABLE articles_backup;
