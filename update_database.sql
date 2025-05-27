-- Drop old table
DROP TABLE IF EXISTS articles_backup;

-- Rename current table
ALTER TABLE articles RENAME TO articles_backup;

-- Create new table with correct structure
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE,
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
    external_links TEXT,
    internal_links TEXT,
    frequent_words TEXT,
    broken_links TEXT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Copy data from old table to new table
INSERT INTO articles (
    id, title, url, post_date, updated_date, category, tags,
    content_intro, headings, book_title, book_author, book_isbn, book_asin,
    word_count, external_links, internal_links, frequent_words, broken_links,
    crawled_at
)
SELECT
    id, title, url, post_date, updated_date, category, tags,
    content_intro, headings, book_title, book_author, book_isbn, book_asin,
    word_count, external_links, internal_links, frequent_words, broken_links,
    crawled_at
FROM articles_backup;

-- Drop backup table
DROP TABLE articles_backup;
