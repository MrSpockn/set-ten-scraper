#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベース検索CLI
set-ten.comから収集した記事データベースを検索・閲覧するためのCLIです
"""

import sqlite3
import os
import sys
import json
import argparse
from datetime import datetime
from tabulate import tabulate

DB_FILE = "setten_articles.db"


def connect_db():
    """データベースに接続"""
    if not os.path.exists(DB_FILE):
        print(
            f"エラー: データベースファイル '{DB_FILE}' が存在しません", file=sys.stderr
        )
        return None

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"データベース接続エラー: {e}", file=sys.stderr)
        return None


def list_articles(limit=10, json_output=False):
    """記事一覧を表示"""
    conn = connect_db()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, url, post_date, category, substr(content_intro, 1, 50) as intro
            FROM articles
            ORDER BY id DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()

        if json_output:
            # JSON形式で出力
            results = []
            for row in rows:
                item = {}
                for key in row.keys():
                    item[key] = row[key]
                results.append(item)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            # テーブル形式で出力
            print(f"\n== 記事一覧 (最新{limit}件) ==")
            if not rows:
                print("記事がありません")
                return

            table_data = []
            for row in rows:
                title = row["title"]
                if len(title) > 30:
                    title = title[:27] + "..."

                category = row["category"] or ""
                if len(category) > 15:
                    category = category[:12] + "..."

                intro = row["intro"] or ""

                table_data.append(
                    [row["id"], title, row["post_date"] or "", category, intro + "..."]
                )

            print(
                tabulate(
                    table_data,
                    headers=["ID", "タイトル", "投稿日", "カテゴリ", "内容"],
                    tablefmt="grid",
                )
            )

    except sqlite3.Error as e:
        print(f"クエリ実行エラー: {e}", file=sys.stderr)

    finally:
        conn.close()


def search_articles(field, keyword, limit=20, json_output=False):
    """記事を検索"""
    conn = connect_db()
    if not conn:
        return

    field_map = {
        "title": "title",
        "content": "content_intro",
        "category": "category",
        "date": "post_date",
    }

    if field not in field_map:
        print(f"エラー: 無効な検索フィールド '{field}'", file=sys.stderr)
        return

    try:
        cursor = conn.cursor()
        query = f"""
            SELECT id, title, url, post_date, category, substr(content_intro, 1, 50) as intro
            FROM articles
            WHERE {field_map[field]} LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """

        cursor.execute(query, (f"%{keyword}%", limit))
        rows = cursor.fetchall()

        if json_output:
            # JSON形式で出力
            results = []
            for row in rows:
                item = {}
                for key in row.keys():
                    item[key] = row[key]
                results.append(item)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            # テーブル形式で出力
            print(f"\n== '{keyword}'の検索結果 ({field}) ==")
            if not rows:
                print("該当する記事はありません")
                return

            table_data = []
            for row in rows:
                title = row["title"]
                if len(title) > 30:
                    title = title[:27] + "..."

                category = row["category"] or ""
                if len(category) > 15:
                    category = category[:12] + "..."

                intro = row["intro"] or ""

                table_data.append(
                    [row["id"], title, row["post_date"] or "", category, intro + "..."]
                )

            print(
                tabulate(
                    table_data,
                    headers=["ID", "タイトル", "投稿日", "カテゴリ", "内容"],
                    tablefmt="grid",
                )
            )

    except sqlite3.Error as e:
        print(f"検索エラー: {e}", file=sys.stderr)

    finally:
        conn.close()


def show_stats():
    """統計情報を表示"""
    conn = connect_db()
    if not conn:
        return

    try:
        cursor = conn.cursor()

        # 記事総数
        cursor.execute("SELECT COUNT(*) as count FROM articles")
        total_count = cursor.fetchone()["count"]

        # カテゴリ別記事数
        cursor.execute(
            """
            SELECT category, COUNT(*) as count 
            FROM articles 
            WHERE category != '' 
            GROUP BY category 
            ORDER BY count DESC
            LIMIT 10
        """
        )
        categories = cursor.fetchall()

        print("\n== データベース統計情報 ==")
        print(f"総記事数: {total_count}")

        if categories:
            print("\n== カテゴリ別記事数 (上位10) ==")
            cat_data = [(cat["category"], cat["count"]) for cat in categories]
            print(tabulate(cat_data, headers=["カテゴリ", "記事数"], tablefmt="simple"))

        # 月別記事数（データがある場合）
        try:
            cursor.execute(
                """
                SELECT substr(post_date, 1, 7) as month, COUNT(*) as count 
                FROM articles 
                WHERE post_date != '' 
                GROUP BY month 
                ORDER BY month DESC
                LIMIT 12
            """
            )
            months = cursor.fetchall()

            if months:
                print("\n== 月別記事数 (最新12ヶ月) ==")
                month_data = [(month["month"], month["count"]) for month in months]
                print(
                    tabulate(month_data, headers=["年月", "記事数"], tablefmt="simple")
                )
        except:
            pass  # 日付データが無効な場合はスキップ

    except sqlite3.Error as e:
        print(f"統計情報取得エラー: {e}", file=sys.stderr)

    finally:
        conn.close()


def show_article(article_id):
    """指定したIDの記事詳細を表示"""
    conn = connect_db()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, url, post_date, category, content_intro
            FROM articles
            WHERE id = ?
        """,
            (article_id,),
        )

        article = cursor.fetchone()

        if not article:
            print(f"エラー: ID '{article_id}' の記事は見つかりません")
            return

        print("\n== 記事詳細 ==")
        print(f"ID: {article['id']}")
        print(f"タイトル: {article['title']}")
        print(f"URL: {article['url']}")
        print(f"投稿日: {article['post_date'] or '不明'}")
        print(f"カテゴリ: {article['category'] or '未分類'}")
        print("\n== 本文冒頭 ==")
        print(article["content_intro"])

    except sqlite3.Error as e:
        print(f"記事取得エラー: {e}", file=sys.stderr)

    finally:
        conn.close()


def main():
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(
        description="set-ten.com 記事データベース検索ツール"
    )

    # サブコマンド設定
    subparsers = parser.add_subparsers(dest="command", help="実行コマンド")

    # list コマンド
    list_parser = subparsers.add_parser("list", help="記事一覧を表示")
    list_parser.add_argument(
        "-n", "--limit", type=int, default=10, help="表示する記事数 (デフォルト: 10)"
    )
    list_parser.add_argument("--json", action="store_true", help="JSON形式で出力")

    # search コマンド
    search_parser = subparsers.add_parser("search", help="記事を検索")
    search_parser.add_argument(
        "field",
        choices=["title", "content", "category", "date"],
        help="検索するフィールド",
    )
    search_parser.add_argument("keyword", help="検索キーワード")
    search_parser.add_argument(
        "-n", "--limit", type=int, default=20, help="表示する最大件数 (デフォルト: 20)"
    )
    search_parser.add_argument("--json", action="store_true", help="JSON形式で出力")

    # stats コマンド
    subparsers.add_parser("stats", help="データベース統計情報を表示")

    # show コマンド
    show_parser = subparsers.add_parser("show", help="記事の詳細を表示")
    show_parser.add_argument("id", type=int, help="表示する記事のID")

    # 引数解析
    args = parser.parse_args()

    # コマンド実行
    if args.command == "list":
        list_articles(args.limit, args.json)
    elif args.command == "search":
        search_articles(args.field, args.keyword, args.limit, args.json)
    elif args.command == "stats":
        show_stats()
    elif args.command == "show":
        show_article(args.id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
