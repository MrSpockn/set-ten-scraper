-- SQLiteデータベース拡張スクリプト
-- 既存のarticlesテーブルに新しい列を追加

-- まず既存のテーブルに列を追加
ALTER TABLE articles ADD COLUMN updated_date TEXT;
ALTER TABLE articles ADD COLUMN tags TEXT;
ALTER TABLE articles ADD COLUMN headings TEXT;

-- 書籍情報
ALTER TABLE articles ADD COLUMN book_title TEXT;
ALTER TABLE articles ADD COLUMN book_author TEXT;
ALTER TABLE articles ADD COLUMN book_isbn TEXT;
ALTER TABLE articles ADD COLUMN book_asin TEXT;

-- 付加情報
ALTER TABLE articles ADD COLUMN word_count INTEGER;
ALTER TABLE articles ADD COLUMN external_links TEXT;

-- 加工情報
ALTER TABLE articles ADD COLUMN frequent_words TEXT;
ALTER TABLE articles ADD COLUMN broken_links TEXT;
