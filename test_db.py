#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベース接続テスト
"""

import sqlite3
import os

DB_FILE = "setten_articles.db"


def main():
    try:
        print(f"データベースファイルのパス: {os.path.abspath(DB_FILE)}")
        print(f"データベースファイルの存在: {os.path.exists(DB_FILE)}")

        if not os.path.exists(DB_FILE):
            print("エラー: データベースファイルが見つかりません。")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # テーブル一覧を取得
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"テーブル一覧: {tables}")

            # articlesテーブルの構造を確認
            cursor.execute("PRAGMA table_info(articles);")
            columns = cursor.fetchall()
            print(f"articlesテーブルの構造: {columns}")

            # 記事数を確認
            cursor.execute("SELECT COUNT(*) FROM articles;")
            count = cursor.fetchone()[0]
            print(f"記事数: {count}")

            # 最初の3件の記事を取得
            cursor.execute("SELECT id, title, url FROM articles LIMIT 3;")
            articles = cursor.fetchall()
            for article in articles:
                print(f"ID: {article[0]}, タイトル: {article[1]}, URL: {article[2]}")

        except sqlite3.Error as e:
            print(f"SQLiteエラー: {e}")

        finally:
            conn.close()

    except Exception as e:
        print(f"エラー発生: {type(e).__name__} - {str(e)}")


if __name__ == "__main__":
    main()
