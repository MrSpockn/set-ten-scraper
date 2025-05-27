-- 一時テーブルの作成
CREATE TABLE articles_temp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE,
    post_date TEXT,
    updated_date TEXT,
    category_id INTEGER,
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
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);

-- カテゴリテーブルの作成
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    parent_id INTEGER,
    slug TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(parent_id) REFERENCES categories(id)
);

-- 既存のカテゴリをカテゴリテーブルに挿入
INSERT OR IGNORE INTO categories (name, parent_id, slug)
SELECT DISTINCT 
    category,
    NULL,
    lower(replace(replace(category, ' ', '-'), '/', '-'))
FROM articles
WHERE category IS NOT NULL;

-- 親カテゴリの関係を更新
UPDATE categories
SET parent_id = (
    SELECT id FROM categories c2 
    WHERE c2.name = (
        SELECT parent_category 
        FROM articles 
        WHERE articles.category = categories.name 
        LIMIT 1
    )
)
WHERE EXISTS (
    SELECT 1 
    FROM articles 
    WHERE articles.category = categories.name 
    AND articles.parent_category IS NOT NULL
);

-- データを新しいテーブルに移行
INSERT INTO articles_temp (
    id, title, url, post_date, updated_date, category_id,
    tags, content_intro, headings, book_title, book_author,
    book_isbn, book_asin, word_count, internal_links,
    frequent_words, broken_links, crawled_at
)
SELECT 
    a.id, a.title, a.url, a.post_date, a.updated_date, c.id,
    a.tags, a.content_intro, a.headings, a.book_title, a.book_author,
    a.book_isbn, a.book_asin, a.word_count, a.internal_links,
    a.frequent_words, a.broken_links, a.crawled_at
FROM articles a
LEFT JOIN categories c ON a.category = c.name;

-- 古いテーブルを削除し、新しいテーブルをリネーム
DROP TABLE articles;
ALTER TABLE articles_temp RENAME TO articles;
