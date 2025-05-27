-- articles_historyテーブルを作成
CREATE TABLE IF NOT EXISTS articles_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT,
    post_date TEXT,
    updated_date TEXT,
    category TEXT,
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
    crawled_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 最新のcrawled_at時刻を取得
WITH latest_crawl AS (
    SELECT MAX(crawled_at) as latest_time
    FROM articles
)
-- 最新以外のデータをarticles_historyに移動
INSERT INTO articles_history (
    title, url, post_date, updated_date, category, tags,
    content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, internal_links,
    frequent_words, broken_links, crawled_at
)
SELECT 
    title, url, post_date, updated_date, category, tags,
    content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, internal_links,
    frequent_words, broken_links, crawled_at
FROM articles
WHERE crawled_at < (SELECT latest_time FROM latest_crawl);

-- 最新以外のデータを削除
DELETE FROM articles
WHERE crawled_at < (
    SELECT MAX(crawled_at)
    FROM articles
);
