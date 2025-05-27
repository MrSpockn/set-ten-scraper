#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベーススキーマを更新するスクリプト
既存のデータベースに新しいカラムを追加します
"""

import sqlite3
import os
import sys

DB_FILE = "setten_articles.db"


def update_database_schema():
    """データベーススキーマを更新する"""
    # データベースファイルの存在確認
    if not os.path.exists(DB_FILE):
        print(f"エラー: データベースファイル '{DB_FILE}' が見つかりません。")
        return False

    print(f"データベース '{DB_FILE}' のスキーマを更新します...")

    # SQLファイルから更新クエリを読み込む
    try:
        with open('update_database.sql', 'r') as f:
            sql_queries = f.read()
    except Exception as e:
        print(f"SQLファイルの読み込みに失敗しました: {e}")
        return False

    # データベース接続
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 現在のテーブル構造を確認
        cursor.execute("PRAGMA table_info(articles)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        print("既存のカラム:", existing_columns)
        
        # 各クエリを実行
        queries = [q.strip() for q in sql_queries.split(';') if q.strip()]
        for query in queries:
            try:
                # 列追加のクエリから列名を抽出
                if "ALTER TABLE" in query and "ADD COLUMN" in query:
                    col_name = query.split("ADD COLUMN")[1].split()[0]
                    # 既に列が存在する場合はスキップ
                    if col_name in existing_columns:
                        print(f"カラム '{col_name}' は既に存在するためスキップします。")
                        continue
                
                cursor.execute(query)
                print(f"クエリを実行しました: {query[:60]}...")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"警告: {e} - スキップします")
                else:
                    print(f"エラー: {e}")
                    # 重大なエラーでない場合は続行
        
        conn.commit()
        print("データベーススキーマの更新が完了しました。")
        return True
    
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    if update_database_schema():
        print("スキーマ更新が正常に完了しました。")
        sys.exit(0)
    else:
        print("スキーマ更新中にエラーが発生しました。")
        sys.exit(1)
