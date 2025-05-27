-- 一時テーブルを作成
CREATE TABLE articles_temp (
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

-- 既存のデータを一時テーブルにコピー
INSERT INTO articles_temp (
    title, url, post_date, updated_date, category,
    tags, content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, internal_links,
    frequent_words, broken_links, crawled_at
)
SELECT 
    title, url, post_date, updated_date, category,
    tags, content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, internal_links,
    frequent_words, broken_links, crawled_at
FROM articles;

-- 既存のテーブルを削除
DROP TABLE articles;

-- 新しいテーブルをarticlesにリネーム
ALTER TABLE articles_temp RENAME TO articles;

-- インデックスを作成
CREATE INDEX idx_category ON articles(category);
CREATE INDEX idx_parent_category ON articles(parent_category);
