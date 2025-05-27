#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
set-ten.comのウェブスクレイピングスクリプト
記事タイトル、URL、投稿日、カテゴリ、本文冒頭を収集してCSVとSQLiteデータベースに保存します
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup, Tag
import csv
import time
import re
import os
import json
import sqlite3
from urllib.parse import urljoin, urlparse, unquote
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from aiohttp import ClientTimeout
import logging
from tqdm import tqdm
import aiosqlite
import pytz

# 基本設定
BASE_URL = "https://set-ten.com/"
OUTPUT_FILE = f"setten_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
DB_FILE = "setten_articles.db"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}
REQUEST_DELAY = 1  # サーバーに負荷をかけないよう1秒間の間隔を設ける
MAX_PAGES = 60    # 予想される記事数に基づいて制限
MAX_CONCURRENT_REQUESTS = 3  # 同時リクエスト数を制限
TIMEOUT = ClientTimeout(total=30)

# タイムゾーン設定
JST = pytz.timezone('Asia/Tokyo')

# グローバル変数
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
visited_urls = set()
articles_data = []

def clean_text(text):
    """テキストのクリーニング"""
    if text:
        return ' '.join(text.strip().split())
    return ''

def is_valid_url(url):
    """URLの妥当性チェック"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_article_page(url):
    """記事ページかどうかの判定"""
    if not url:
        return False
        
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    path_parts = path.split('/')

    # 以下のパターンを除外
    exclude_patterns = {
        'privacy-policy', 'profile', 'contact', 
        'page', 'author', 'category', 'tag', 'date',
        'feed', 'wp-content', 'wp-admin', 'wp-includes',
        'comments', 'trackback', 'login', 'register',
        'admin', 'search', 'archive'
    }
    
    for part in path_parts:
        if part in exclude_patterns:
            return False
            
    # セッテンの記事URLは通常3階層（例: set-ten.com/programming/python/12345/）
    if len(path_parts) < 3:
        return False
        
    # 最後のパスが数字を含むことを確認（記事IDを含む）
    last_part = path_parts[-1]
    has_number = any(char.isdigit() for char in last_part)
    
    return has_number and not any(pattern in url for pattern in exclude_patterns)

def normalize_url(url):
    """URLを正規化する"""
    # URLの正規化（末尾のスラッシュを統一、クエリパラメータを削除など）
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    return f"{parsed.scheme}://{parsed.netloc}{path}"

async def fetch_page(session, url):
    """非同期でページを取得"""
    async with semaphore:
        try:
            async with session.get(url, headers=HEADERS, timeout=TIMEOUT) as response:
                if response.status == 200:
                    return await response.text()
                logging.warning(f"Failed to fetch {url}: Status {response.status}")
                return None
        except Exception as e:
            logging.error(f"Error fetching {url}: {str(e)}")
            return None

async def extract_article_info_async(session, url):
    """非同期で記事情報を抽出"""
    html = await fetch_page(session, url)
    if not html:
        return None
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # タイトル
    title_elem = soup.select_one('h1.entry-title')
    title = clean_text(title_elem.get_text()) if title_elem else ""
    
    # 投稿日
    date_meta = soup.select_one("meta[property='article:published_time']")
    date = ""
    if date_meta:
        content = date_meta.get("content", "")
        if content and isinstance(content, str):
            date = content.split("T")[0]
    
    # 更新日
    updated_meta = soup.select_one("meta[property='article:modified_time']")
    updated_date = ""
    if updated_meta:
        content = updated_meta.get("content", "")
        if content and isinstance(content, str):
            updated_date = content.split("T")[0]
    
    # カテゴリー（階層構造を考慮）
    category_path = ""
    try:
        # カテゴリの抽出方法を改善
        cat_selectors = [
            ".post-categories a",  # WordPress標準
            ".cat-links a",       # テーマ固有
            ".entry-category a",   # テーマ固有
            ".article-category a", # カスタム
            ".category a",        # 一般的
            ".breadcrumb a"       # パンくずリスト
        ]
        
        # 除外するカテゴリ
        exclude_categories = {'home', 'トップ', 'ホーム', 'index', '一覧'}
        
        category_list = []
        for selector in cat_selectors:
            cat_elems = soup.select(selector)
            for cat in cat_elems:
                if isinstance(cat, Tag) and cat.string:
                    cat_text = clean_text(cat.string)
                    if cat_text and cat_text.lower() not in exclude_categories:
                        if cat_text not in category_list:
                            category_list.append(cat_text)
                            
        if not category_list:  # バックアップ: URLからカテゴリを推測
            path_parts = urlparse(url).path.strip('/').split('/')
            if len(path_parts) >= 2:  # 最低2階層のパスがある場合
                # URLデコードとクリーニング
                from urllib.parse import unquote
                for part in path_parts[:-1]:  # 最後のパス（記事ID）を除外
                    cat = clean_text(unquote(part).replace('-', ' '))
                    if cat and cat.lower() not in exclude_categories:
                        category_list.append(cat)
        
        # カテゴリパスの生成
        if category_list:
            category_path = " > ".join(category_list)
    except Exception as e:
        logging.warning(f"カテゴリの抽出でエラー: {str(e)}")

    # タグ（重複を排除して正規化）
    tags = set()
    try:
        # タグ抽出のセレクタを強化
        tag_selectors = [
            ".tags-links a",      # WordPress標準
            ".tag-links a",       # テーマ固有
            ".entry-tags a",      # テーマ固有
            ".post-tags a",       # 一般的
            ".article-tags a",    # カスタム
            ".tags a",           # シンプルな形式
            "[rel='tag']",       # HTMLのタグ関連属性
            ".meta-tags a",      # メタ情報領域のタグ
            ".tag"              # 単純なタグクラス
        ]
        
        for selector in tag_selectors:
            for tag in soup.select(selector):
                if isinstance(tag, Tag):
                    # href属性からタグを抽出する場合
                    href = tag.get('href', '')
                    if isinstance(href, str) and href:
                        try:
                            # URLからタグ名を抽出（最後のパス部分を使用）
                            path_parts = [p for p in href.split('/') if p]
                            if path_parts:
                                tag_from_url = clean_text(unquote(path_parts[-1]).replace('-', ' '))
                                if tag_from_url:
                                    tags.add(tag_from_url)
                        except Exception as e:
                            logging.debug(f"タグURLの解析でエラー: {str(e)}")
                    
                    # タグのテキストを抽出
                    tag_text = tag.get_text(strip=True)
                    if tag_text:
                        try:
                            # テキストの正規化
                            cleaned_tag = clean_text(tag_text)
                            if cleaned_tag:
                                tags.add(cleaned_tag)
                        except Exception as e:
                            logging.debug(f"タグテキストの処理でエラー: {str(e)}")
                            
    except Exception as e:
        logging.warning(f"タグの抽出でエラー: {str(e)}")

    tags_str = ','.join(sorted(tags)) if tags else ""

    # 本文冒頭
    intro = ""
    content = soup.select_one('.entry-content')
    if content:
        paragraphs = content.find_all('p', recursive=False)
        for p in paragraphs:
            if p.text.strip():
                intro = clean_text(p.text)
                break

    # 見出し
    headings = []
    if content:
        for h in content.find_all(['h2', 'h3', 'h4']):
            heading_text = clean_text(h.get_text())
            if heading_text:
                headings.append(f"{h.name}: {heading_text}")
    headings_str = "\n".join(headings)

    # 書籍情報の抽出
    book_title = ""
    book_author = ""
    book_isbn = ""
    book_asin = ""
    
    if content:
        # 書籍のタイトルと著者を探す
        for elem in content.select('strong, b, h2, h3'):
            text = clean_text(elem.get_text())
            # 「著」「著者」で分割を試みる
            for separator in ['著者：', '著：', '著者:', '著:', ' 著 ', '著']:
                if separator in text:
                    parts = text.split(separator)
                    if len(parts) >= 2:
                        book_title = parts[0].strip()
                        book_author = parts[1].strip()
                        break
            if book_title and book_author:
                break
        
        # ISBN-13とISBN-10を探す
        text_content = content.get_text()
        isbn_patterns = [
            r'ISBN[-]?13?\s*[:：]?\s*(978[-]?\d{10})',
            r'ISBN[-]?10?\s*[:：]?\s*(\d{10})',
            r'ISBN\s*[:：]?\s*(\d{13})',
            r'978[-]?\d{10}',  # ISBN-13（プレフィックスのみ）
            r'\d{9}[0-9X]'     # ISBN-10
        ]
        
        for pattern in isbn_patterns:
            match = re.search(pattern, text_content)
            if match:
                book_isbn = match.group(1 if '(' in pattern else 0).replace('-', '')
                break

        # ASINを探す（Amazonのリンクからも抽出）
        asin_patterns = [
            r'ASIN\s*[:：]?\s*([A-Z0-9]{10})',
            r'amazon[.]co[.]jp/[^/]+/([A-Z0-9]{10})',
            r'amazon[.]co[.]jp/dp/([A-Z0-9]{10})'
        ]
        
        for pattern in asin_patterns:
            match = re.search(pattern, text_content)
            if match:
                book_asin = match.group(1)
                break

    # 文章の長さを概算
    word_count = len(''.join(content.stripped_strings)) if content else 0

    # 内部リンクと解析
    internal_links = []
    broken_links = []
    if content:
        for link in content.find_all('a', href=True):
            href = link.get('href', '')
            if href:
                try:
                    absolute_url = normalize_url(urljoin(url, href))
                    if 'set-ten.com' in absolute_url:
                        title = clean_text(link.get_text())
                        internal_links.append({
                            'url': absolute_url,
                            'title': title or '（リンクテキストなし）',
                            'text': title or '（リンクテキストなし）'
                        })
                except Exception as e:
                    broken_links.append(href)

    # 頻出語の取得
    frequent_words = []
    if content:
        # テキストの前処理
        text = content.get_text()
        # 単語の抽出（改行で区切って2文字以上の単語を抽出）
        words = []
        for line in text.split('\n'):
            # 不要な記号を除去
            line = re.sub(r'[「」『』（）\(\)［］\[\]{}｛｝〈〉《》【】・、。,.]', ' ', line)
            # 単語に分割
            for word in line.split():
                if len(word) >= 2:  # 2文字以上の単語のみ
                    words.append(word)
        # 単語数をカウント
        word_count = len(words)
        # 頻出語の抽出（上位15個）
        from collections import Counter
        word_counter = Counter(words)
        frequent_words = [word for word, _ in word_counter.most_common(15)]
    
    frequent_words_str = ", ".join(frequent_words)

    article_info = {
        'title': title,
        'url': url,
        'post_date': date,
        'updated_date': updated_date,
        'category_path': category_path,
        'tags': tags_str,
        'content_intro': intro,
        'headings': headings_str,
        'book_title': book_title,
        'book_author': book_author,
        'book_isbn': book_isbn,
        'book_asin': book_asin,
        'word_count': word_count,
        'internal_links': internal_links,
        'frequent_words': frequent_words_str,
        'broken_links': broken_links
    }
    
    return article_info

async def crawl_page(session, url, page_count):
    """ページをクロールして記事情報を収集"""
    global visited_urls, articles_data
    
    normalized_url = normalize_url(url)
    if normalized_url in visited_urls:
        return
    
    logging.info(f"処理中: {normalized_url}")
    visited_urls.add(normalized_url)
    
    if page_count >= MAX_PAGES:
        logging.warning(f"最大ページ数（{MAX_PAGES}）に到達しました")
        return
        
    html = await fetch_page(session, normalized_url)
    if not html:
        return
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 記事ページの場合は情報を抽出
    if is_article_page(normalized_url):
        article_info = await extract_article_info_async(session, normalized_url)
        if article_info and article_info['title'] and article_info['post_date']:
            logging.info(f"記事を発見: {article_info['title']}")
            articles_data.append(article_info)
        else:
            logging.warning(f"記事情報の抽出に失敗: {normalized_url}")
    
    # 次のページと記事へのリンクを収集
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').strip()
        if not href or href.startswith('#'):
            continue
            
        try:
            absolute_url = normalize_url(urljoin(url, href))
            
            # 無効なURLまたは外部URLはスキップ
            if not is_valid_url(absolute_url) or 'set-ten.com' not in absolute_url:
                continue
                
            if absolute_url not in visited_urls:
                await asyncio.sleep(REQUEST_DELAY)
                await crawl_page(session, absolute_url, page_count + 1)
                
        except Exception as e:
            logging.error(f"リンク処理エラー {href}: {str(e)}")

async def save_to_db(articles):
    """データベースに記事情報を保存"""
    async with aiosqlite.connect(DB_FILE) as db:
        # トランザクション開始
        await db.execute("BEGIN TRANSACTION")
        try:
            # articlesテーブルを作成
            await db.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    post_date TEXT,
                    updated_date TEXT,
                    category_path TEXT,
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
                )
            """)
            
            # 現在の最新のcrawled_at時刻を取得（日本時間）
            current_crawl_time = datetime.now(JST).isoformat()

            # 新しい記事データを保存
            for article in articles:
                await db.execute("""
                    INSERT OR REPLACE INTO articles (
                        title, url, post_date, category_path, content_intro,
                        crawled_at, updated_date, tags, headings, book_title,
                        book_author, book_isbn, book_asin, word_count,
                        internal_links, frequent_words, broken_links
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article['title'], article['url'], article['post_date'],
                    article.get('category_path', ''), article.get('content_intro', ''),
                    current_crawl_time, article.get('updated_date', ''),
                    article.get('tags', ''), article.get('headings', ''),
                    article.get('book_title', ''), article.get('book_author', ''),
                    article.get('book_isbn', ''), article.get('book_asin', ''),
                    article.get('word_count', 0),
                    json.dumps(article.get('internal_links', []), ensure_ascii=False),
                    article.get('frequent_words', ''),
                    json.dumps(article.get('broken_links', []), ensure_ascii=False)
                ))

            # コミット
            await db.commit()
            logging.info(f"{len(articles)}件の記事をデータベースに保存しました")
            
        except Exception as e:
            await db.execute("ROLLBACK")
            logging.error(f"Database error: {str(e)}")
            raise

async def main():
    """メイン処理"""
    global visited_urls, articles_data
    
    print(f"スクレイピングを開始します: {BASE_URL}")
    start_time = time.time()
    
    # HTTPセッションを開始
    async with aiohttp.ClientSession() as session:
        # クロール開始
        await crawl_page(session, BASE_URL, 0)
    
    print(f"クロール完了。処理したページ数: {len(visited_urls)}, 収集した記事数: {len(articles_data)}")
    
    # CSVファイルに保存
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        if articles_data:
            writer = csv.DictWriter(f, fieldnames=articles_data[0].keys())
            writer.writeheader()
            for article in articles_data:
                writer.writerow(article)
    
    print(f"データを {OUTPUT_FILE} に保存しました。")
    
    # データベースに保存
    await save_to_db(articles_data)
    
    # 処理時間とサマリーを表示
    elapsed_time = time.time() - start_time
    print(f"処理完了！経過時間: {elapsed_time:.2f}秒")
    print(f"処理したURL数: {len(visited_urls)}")
    print(f"収集した記事数: {len(articles_data)}")

if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/crawler_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        os.makedirs('logs', exist_ok=True)
    except Exception as e:
        print(f"Error creating logs directory: {str(e)}")
    
    asyncio.run(main())
