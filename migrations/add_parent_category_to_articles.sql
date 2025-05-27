-- 既存のテーブルをバックアップ
CREATE TABLE articles_backup AS SELECT * FROM articles;

-- 既存のテーブルを削除
DROP TABLE articles;

-- 新しいテーブル構造で作成
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE,
    post_date TEXT,
    updated_date TEXT,
    category TEXT,
    parent_category TEXT,
    tags TEXT,
    content_intro TEXT,
    headings TEXT,
    book_title TEXT,
    book_author TEXT,
    book_isbn TEXT,
    book_asin TEXT,
    word_count INTEGER,
    internal_links TEXT,
    frequent_words TEXT,
    broken_links TEXT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- データを復元
INSERT INTO articles (
    id, title, url, post_date, updated_date, category,
    tags, content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, internal_links,
    frequent_words, broken_links, crawled_at
)
SELECT 
    id, title, url, post_date, updated_date, category,
    tags, content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, internal_links,
    frequent_words, broken_links, crawled_at
FROM articles_backup;

-- バックアップテーブルを削除
DROP TABLE articles_backup;
