#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
スクレイピング機能拡張版
set-ten.comのウェブスクレイピングスクリプト（拡張版）
記事情報を詳細に収集してCSVとSQLiteデータベースに保存します
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import os
import json
import sqlite3
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging

# 基本設定
BASE_URL = "https://set-ten.com/"
OUTPUT_FILE = f"setten_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
DB_FILE = "setten_articles.db"  # データベースファイル名
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}
REQUEST_DELAY = 2  # サイトに負荷をかけないよう2秒間の間隔を設ける
MAX_PAGES = 100  # スクレイピングする最大ページ数（無限ループ防止のため）

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("setten_scraper")

# 収集済みURLを管理するセット
visited_urls = set()
# 記事情報を保存するリスト
articles_data = []


def initialize_db():
    """データベースの初期化とテーブル作成"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # articlesテーブルの作成（存在しない場合のみ）
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS articles (
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
        frequent_words TEXT,
        broken_links TEXT,
        crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    conn.commit()
    return conn


def is_valid_url(url):
    """有効なURLかつset-ten.comドメインに属しているか確認"""
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc == "set-ten.com"


def clean_text(text):
    """テキストを整形する（改行削除、複数スペースを一つに）"""
    if text:
        text = re.sub(r"\s+", " ", text.strip())
        return text
    return ""


def extract_article_info(url):
    """記事ページから情報を抽出（拡張版）"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            logger.warning(f"ページの取得に失敗しました: {url} - ステータスコード: {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        # 記事タイトル
        title = ""
        title_elem = soup.select_one("h1.entry-title")
        if title_elem:
            title = clean_text(title_elem.get_text())

        # 投稿日
        date = ""
        date_elem = soup.select_one("time.entry-date")
        if date_elem:
            date = date_elem.get_text().strip()

        # 更新日（投稿日と異なる場合があるのでmeta情報から取得を試みる）
        updated_date = ""
        updated_meta = soup.select_one("meta[property='article:modified_time']")
        if updated_meta and updated_meta.get('content'):
            updated_date = updated_meta.get('content').split('T')[0]  # YYYY-MM-DD形式で取得
        
        # カテゴリ
        categories = []
        category_elems = soup.select(".cat-links a")
        if category_elems:
            categories = [cat.get_text().strip() for cat in category_elems]
        category_str = ", ".join(categories)
        
        # タグ
        tags = []
        tag_elems = soup.select(".tags-links a")
        if tag_elems:
            tags = [tag.get_text().strip() for tag in tag_elems]
        tags_str = ", ".join(tags)

        # 本文冒頭（最初の段落）
        content_intro = ""
        content_elem = soup.select_one(".entry-content p")
        if content_elem:
            content_intro = clean_text(content_elem.get_text())[:200] + "..."  # 先頭200文字のみ
        
        # 記事の見出し
        headings = []
        heading_elems = soup.select(".entry-content h2, .entry-content h3")
        if heading_elems:
            for h in heading_elems:
                headings.append({
                    'level': h.name,  # h2, h3など
                    'text': clean_text(h.get_text())
                })
        
        # 書籍情報の抽出（主にAmazonへのリンクから）
        book_title = ""
        book_author = ""
        book_isbn = ""
        book_asin = ""
        
        # Amazon商品リンクからASINを抽出
        amazon_links = soup.select("a[href*='amazon.co.jp']")
        for link in amazon_links:
            href = link.get('href', '')
            # ASINを抽出（通常は10桁の英数字）
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', href)
            if asin_match:
                book_asin = asin_match.group(1)
                # リンク近くにあるテキストから書籍名や著者を推測
                parent = link.parent
                if parent:
                    text = clean_text(parent.get_text())
                    if not book_title and "著" in text:
                        parts = text.split("著")
                        if len(parts) > 1:
                            book_title = parts[0].strip()
                            author_part = parts[1].strip()
                            if author_part:
                                book_author = author_part.split()[0]  # 最初の部分を著者とする
                break
        
        # コンテンツから書籍情報を抽出（ISBNなど）
        content_element = soup.select_one(".entry-content")
        content_text = content_element.get_text() if content_element else ""
        isbn_match = re.search(r'ISBN[:\-]?\s*(\d[\d\-]{10,})', content_text)
        if isbn_match:
            book_isbn = isbn_match.group(1).replace('-', '')
            
        # 全文からテキストを抽出して文字数をカウント
        full_content = ""
        content_elems = soup.select(".entry-content p")
        for elem in content_elems:
            full_content += elem.get_text() + " "
        word_count = len(full_content)
        
        # 外部リンクを収集
        external_links = []
        for a in soup.select(".entry-content a[href^='http']"):
            href = a.get('href')
            if href and not href.startswith(BASE_URL) and "set-ten.com" not in href:
                external_links.append({
                    'url': href,
                    'text': clean_text(a.get_text()) or href
                })
        
        # 頻出単語を抽出（単純なカウント方式）
        frequent_words = {}
        if full_content:
            # 簡易的な単語分割（日本語のため形態素解析が理想だが、簡易版として）
            words = re.findall(r'[一-龠々〆〤ぁ-んァ-ヶa-zA-Z0-9]+', full_content)
            # ストップワードのリスト
            stopwords = ['これ', 'それ', 'あれ', 'この', 'その', 'あの', 'は', 'が', 'の', 'に', 'を', 'で', 'て', 'に', 'と']
            # 単語カウント
            word_count_dict = {}
            for word in words:
                if len(word) > 1 and word not in stopwords:  # 2文字以上の単語のみカウント
                    if word in word_count_dict:
                        word_count_dict[word] += 1
                    else:
                        word_count_dict[word] = 1
            
            # 出現頻度順にソート
            sorted_words = sorted(word_count_dict.items(), key=lambda x: x[1], reverse=True)
            # 上位20単語を取得
            frequent_words = dict(sorted_words[:20]) if sorted_words else {}
        
        # リンク切れをチェック（実際には全てのリンクをチェックするのは負荷が大きいため、実装は限定的）
        broken_links = []
        # 実用的には、実際のリンクチェックは外部スクリプトで定期的に行うべき

        article_info = {
            "title": title,
            "url": url,
            "date": date,
            "updated_date": updated_date,
            "category": category_str,
            "tags": tags_str,
            "content_intro": content_intro,
            "headings": json.dumps(headings, ensure_ascii=False),
            "book_title": book_title,
            "book_author": book_author,
            "book_isbn": book_isbn,
            "book_asin": book_asin,
            "word_count": word_count,
            "external_links": json.dumps(external_links, ensure_ascii=False),
            "frequent_words": json.dumps(frequent_words, ensure_ascii=False),
            "broken_links": json.dumps(broken_links, ensure_ascii=False),
        }
        
        return article_info

    except Exception as e:
        logger.error(f"記事情報抽出中にエラー発生: {url} - {str(e)}", exc_info=True)
        return None


def extract_links(url):
    """ページからリンクを抽出する"""
    links = set()
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            logger.warning(f"ページの取得に失敗しました: {url} - ステータスコード: {response.status_code}")
            return links

        soup = BeautifulSoup(response.content, "html.parser")

        # すべてのaタグからhref属性を取得
        for a_tag in soup.find_all("a", href=True):
            link = urljoin(url, a_tag["href"])

            # 同一ドメイン内のリンクのみを収集する
            if is_valid_url(link) and link not in visited_urls:
                links.add(link)
    except Exception as e:
        logger.error(f"リンク抽出でエラー発生: {url} - {str(e)}")

    return links


def is_article_page(url):
    """記事ページかどうかを判定する（簡易的な判定）"""
    # 通常、記事ページは階層が深いURLになる（例: https://set-ten.com/category/article_name/）
    parts = urlparse(url).path.strip("/").split("/")
    return (
        len(parts) >= 2
        and "category" not in parts
        and "tag" not in parts
        and "page" not in parts
    )


def crawl():
    """再帰的にサイトをクロール"""
    # キューにトップページを追加
    queue = [BASE_URL]
    page_count = 0

    while queue and page_count < MAX_PAGES:
        current_url = queue.pop(0)

        # 既に訪問済みであればスキップ
        if current_url in visited_urls:
            continue

        logger.info(f"処理中: {current_url}")
        visited_urls.add(current_url)
        page_count += 1

        # 記事ページであれば情報を抽出
        if is_article_page(current_url):
            article_info = extract_article_info(current_url)
            if article_info:
                logger.info(f"記事を発見: {article_info['title']}")
                articles_data.append(article_info)

        # ページからリンクを取得し、キューに追加
        links = extract_links(current_url)
        queue.extend(links)

        # サーバーに負荷をかけないよう一定時間待機
        time.sleep(REQUEST_DELAY)

    logger.info(f"クロール完了。処理したページ数: {page_count}, 収集した記事数: {len(articles_data)}")


def save_to_csv():
    """収集したデータをCSVファイルに保存"""
    fieldnames = [
        "title", "url", "date", "updated_date", "category", "tags",
        "content_intro", "headings", "book_title", "book_author",
        "book_isbn", "book_asin", "word_count", "external_links",
        "frequent_words", "broken_links"
    ]

    try:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for article in articles_data:
                # CSVに書き込むデータを整形
                row = {k: article.get(k, "") for k in fieldnames}
                # dateをpost_dateに置き換え
                row["date"] = article.get("date", "")
                writer.writerow(row)

        logger.info(f"データを {OUTPUT_FILE} に保存しました。")
    except Exception as e:
        logger.error(f"CSVファイル保存中にエラーが発生しました: {str(e)}")


def save_to_db(conn, articles):
    """収集したデータをデータベースに保存"""
    cursor = conn.cursor()
    saved_count = 0
    updated_count = 0

    try:
        for article in articles:
            try:
                # 既存の記事がある場合は更新、なければ新規追加
                cursor.execute(
                    """
                INSERT OR REPLACE INTO articles (
                    title, url, post_date, updated_date, category, tags, 
                    content_intro, headings, book_title, book_author, 
                    book_isbn, book_asin, word_count, external_links, 
                    frequent_words, broken_links
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        article.get("title", ""),
                        article.get("url", ""),
                        article.get("date", ""),
                        article.get("updated_date", ""),
                        article.get("category", ""),
                        article.get("tags", ""),
                        article.get("content_intro", ""),
                        article.get("headings", "[]"),
                        article.get("book_title", ""),
                        article.get("book_author", ""),
                        article.get("book_isbn", ""),
                        article.get("book_asin", ""),
                        article.get("word_count", 0),
                        article.get("external_links", "[]"),
                        article.get("frequent_words", "{}"),
                        article.get("broken_links", "[]"),
                    ),
                )

                if cursor.rowcount > 0:
                    if cursor.lastrowid:
                        saved_count += 1
                    else:
                        updated_count += 1
            except sqlite3.Error as e:
                logger.error(f"記事の保存中にエラー発生: {article.get('url', 'Unknown URL')} - {str(e)}")

        conn.commit()
        logger.info(f"データベースに {saved_count} 件の新しい記事を保存、{updated_count} 件の記事を更新しました。")
    except Exception as e:
        logger.error(f"データベース保存中にエラーが発生しました: {str(e)}")
        conn.rollback()


def main():
    start_time = time.time()
    logger.info(f"拡張スクレイピングを開始します: {BASE_URL}")

    # データベース初期化
    db_conn = initialize_db()

    # クロール実行
    crawl()

    # 結果をCSVに保存
    save_to_csv()

    # 結果をデータベースに保存
    save_to_db(db_conn, articles_data)

    # データベース接続を閉じる
    db_conn.close()

    elapsed_time = time.time() - start_time
    logger.info(f"処理完了！経過時間: {elapsed_time:.2f}秒")
    logger.info(f"処理したURL数: {len(visited_urls)}")
    logger.info(f"収集した記事数: {len(articles_data)}")


if __name__ == "__main__":
    main()


def query_db(query_type=None, keyword=None):
    """データベースから記事を検索する

    Args:
        query_type (str): 'date', 'category', 'title'などの検索タイプ
        keyword (str): 検索キーワード

    Returns:
        list: 検索結果のリスト
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
    cursor = conn.cursor()

    try:
        if query_type == "category":
            cursor.execute(
                "SELECT * FROM articles WHERE category LIKE ?", (f"%{keyword}%",)
            )
        elif query_type == "date":
            cursor.execute(
                "SELECT * FROM articles WHERE post_date LIKE ?", (f"%{keyword}%",)
            )
        elif query_type == "title":
            cursor.execute(
                "SELECT * FROM articles WHERE title LIKE ?", (f"%{keyword}%",)
            )
        else:
            # デフォルトは全件取得（新しい順）
            cursor.execute("SELECT * FROM articles ORDER BY crawled_at DESC")

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    except sqlite3.Error as e:
        logger.error(f"データベース検索中にエラーが発生しました: {str(e)}")
        conn.close()
        return []
