#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
set-ten.comのウェブスクレイピングスクリプト
記事タイトル、URL、投稿日、カテゴリ、本文冒頭を収集してCSVとSQLiteデータベースに保存します
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import os
import sqlite3
from urllib.parse import urljoin, urlparse
from datetime import datetime

# 基本設定
BASE_URL = "https://set-ten.com/"
OUTPUT_FILE = f"setten_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
DB_FILE = "setten_articles.db"  # データベースファイル名
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}
REQUEST_DELAY = 2  # サイトに負荷をかけないよう2秒間の間隔を設ける
MAX_PAGES = 100  # スクレイピングする最大ページ数（無限ループ防止のため）

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
        category TEXT,
        content_intro TEXT,
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
    """記事ページから情報を抽出"""
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(
                f"ページの取得に失敗しました: {url} - ステータスコード: {response.status_code}"
            )
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

        # カテゴリ
        categories = []
        category_elems = soup.select(".cat-links a")
        if category_elems:
            categories = [cat.get_text().strip() for cat in category_elems]
        category_str = ", ".join(categories)

        # 本文冒頭（最初の段落）
        content_intro = ""
        content_elem = soup.select_one(".entry-content p")
        if content_elem:
            content_intro = (
                clean_text(content_elem.get_text())[:200] + "..."
            )  # 先頭200文字のみ

        return {
            "title": title,
            "url": url,
            "date": date,
            "category": category_str,
            "content_intro": content_intro,
        }

    except Exception as e:
        print(f"エラー発生: {url} - {str(e)}")
        return None


def extract_links(url):
    """ページからリンクを抽出する"""
    links = set()
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(
                f"ページの取得に失敗しました: {url} - ステータスコード: {response.status_code}"
            )
            return links

        soup = BeautifulSoup(response.content, "html.parser")

        # すべてのaタグからhref属性を取得
        for a_tag in soup.find_all("a", href=True):
            link = urljoin(url, a_tag["href"])

            # 同一ドメイン内のリンクのみを収集する
            if is_valid_url(link) and link not in visited_urls:
                links.add(link)
    except Exception as e:
        print(f"リンク抽出でエラー発生: {url} - {str(e)}")

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

        print(f"処理中: {current_url}")
        visited_urls.add(current_url)
        page_count += 1

        # 記事ページであれば情報を抽出
        if is_article_page(current_url):
            article_info = extract_article_info(current_url)
            if article_info:
                print(f"記事を発見: {article_info['title']}")
                articles_data.append(article_info)

        # ページからリンクを取得し、キューに追加
        links = extract_links(current_url)
        queue.extend(links)

        # サーバーに負荷をかけないよう一定時間待機
        time.sleep(REQUEST_DELAY)

    print(
        f"クロール完了。処理したページ数: {page_count}, 収集した記事数: {len(articles_data)}"
    )


def save_to_csv():
    """収集したデータをCSVファイルに保存"""
    fieldnames = ["title", "url", "date", "category", "content_intro"]

    try:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for article in articles_data:
                writer.writerow(article)

        print(f"データを {OUTPUT_FILE} に保存しました。")
    except Exception as e:
        print(f"CSVファイル保存中にエラーが発生しました: {str(e)}")


def save_to_db(conn, articles):
    """収集したデータをデータベースに保存"""
    cursor = conn.cursor()
    saved_count = 0

    try:
        for article in articles:
            try:
                cursor.execute(
                    """
                INSERT OR IGNORE INTO articles (title, url, post_date, category, content_intro)
                VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        article["title"],
                        article["url"],
                        article["date"],
                        article["category"],
                        article["content_intro"],
                    ),
                )

                if cursor.rowcount > 0:
                    saved_count += 1
            except sqlite3.Error as e:
                print(f"記事の保存中にエラー発生: {article['url']} - {str(e)}")

        conn.commit()
        print(f"データベースに {saved_count} 件の新しい記事を保存しました。")
    except Exception as e:
        print(f"データベース保存中にエラーが発生しました: {str(e)}")
        conn.rollback()


def main():
    start_time = time.time()
    print(f"スクレイピングを開始します: {BASE_URL}")

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
    print(f"処理完了！経過時間: {elapsed_time:.2f}秒")
    print(f"処理したURL数: {len(visited_urls)}")
    print(f"収集した記事数: {len(articles_data)}")


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
        print(f"データベース検索中にエラーが発生しました: {str(e)}")
        conn.close()
        return []
