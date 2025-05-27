#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
set-ten.comの記事データベースを検索するスクリプト
"""

import sqlite3
import argparse
import os
import json
from datetime import datetime
from tabulate import tabulate

DB_FILE = "setten_articles.db"

def connect_to_db():
    """データベースに接続"""
    if not os.path.exists(DB_FILE):
        print(f"エラー: データベースファイル '{DB_FILE}' が見つかりません。")
        return None
        
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
    return conn

def get_all_articles(limit=10):
    """すべての記事を最新順に取得"""
    conn = connect_to_db()
    if not conn:
        return []
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT id, title, url, post_date, category, substr(content_intro, 1, 50) as intro, crawled_at 
        FROM articles 
        ORDER BY crawled_at DESC
        LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            item = {}
            for key in row.keys():
                item[key] = row[key]
            results.append(item)
        
        conn.close()
        return results
    except sqlite3.Error as e:
        print(f"クエリ実行中にエラーが発生しました: {str(e)}")
        conn.close()
        return []

def search_articles(search_type, keyword, limit=20):
    """記事を検索"""
    conn = connect_to_db()
    if not conn:
        return []
        
    cursor = conn.cursor()
    
    query = """
    SELECT id, title, url, post_date, category, substr(content_intro, 1, 50) as intro, crawled_at 
    FROM articles 
    WHERE {field} LIKE ?
    ORDER BY crawled_at DESC
    LIMIT ?
    """
    
    field = 'title'  # デフォルト
    if search_type == 'title':
        field = 'title'
    elif search_type == 'category':
        field = 'category'
    elif search_type == 'date':
        field = 'post_date'
    elif search_type == 'content':
        field = 'content_intro'
    else:
        print(f"エラー: 無効な検索タイプ '{search_type}'")
        return []
    
    try:
        cursor.execute(query.format(field=field), (f'%{keyword}%', limit))
        results = []
        for row in cursor.fetchall():
            item = {}
            for key in row.keys():
                item[key] = row[key]
            results.append(item)
        
        conn.close()
        return results
    except sqlite3.Error as e:
        print(f"検索中にエラーが発生しました: {str(e)}")
        conn.close()
        return []

def print_results(results, format_type='table'):
    """検索結果を表示"""
    if not results:
        print("該当する記事がありません。")
        return
        
    if format_type == 'json':
        # JSON形式で出力
        # datetimeオブジェクトをJSONシリアライズ可能な形式に変換
        json_results = []
        for row in results:
            json_row = {}
            for key, value in row.items():
                if isinstance(value, datetime):
                    json_row[key] = value.isoformat()
                else:
                    json_row[key] = value
            json_results.append(json_row)
        
        print(json.dumps(json_results, ensure_ascii=False, indent=2))
    else:
        # テーブル形式で出力
        table_data = []
        for row in results:
            title_text = row['title']
            if len(title_text) > 30:
                title_text = title_text[:30] + '...'
                
            category_text = row.get('category', '')
            if category_text and len(category_text) > 20:
                category_text = category_text[:20] + '...'
                
            table_data.append([
                row['id'], 
                title_text, 
                row.get('post_date', ''), 
                category_text,
                row.get('intro', '')
            ])
        
        print(tabulate(
            table_data, 
            headers=['ID', 'タイトル', '投稿日', 'カテゴリ', '内容'], 
            tablefmt='grid'
        ))

def get_stats():
    """データベースの統計情報を取得"""
    conn = connect_to_db()
    if not conn:
        return {}
        
    cursor = conn.cursor()
    stats = {}
    
    try:
        # 記事の総数
        cursor.execute("SELECT COUNT(*) as count FROM articles")
        row = cursor.fetchone()
        if row:
            stats['total_articles'] = row['count']
        else:
            stats['total_articles'] = 0
        
        # カテゴリごとの記事数
        cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM articles 
        WHERE category != '' 
        GROUP BY category 
        ORDER BY count DESC
        """)
        stats['categories'] = []
        for row in cursor.fetchall():
            stats['categories'].append({
                'category': row['category'],
                'count': row['count']
            })
        
        # 月別の記事数
        cursor.execute("""
        SELECT substr(post_date, 1, 7) as month, COUNT(*) as count 
        FROM articles 
        WHERE post_date != '' 
        GROUP BY month 
        ORDER BY month DESC
        """)
        stats['monthly'] = []
        for row in cursor.fetchall():
            stats['monthly'].append({
                'month': row['month'],
                'count': row['count']
            })
        
    except sqlite3.Error as e:
        print(f"統計情報の取得中にエラーが発生しました: {str(e)}")
    
    conn.close()
    return stats

def print_stats(stats):
    """統計情報を表示"""
    if not stats:
        print("統計情報を取得できませんでした。")
        return
        
    print(f"\n== set-ten.com 記事データベース統計 ==")
    print(f"総記事数: {stats.get('total_articles', 0)}")
    
    if 'categories' in stats and stats['categories']:
        print("\n== カテゴリ別記事数 ==")
        cat_data = []
        for cat in stats['categories'][:10]:  # 上位10カテゴリのみ表示
            cat_data.append([cat['category'], cat['count']])
        print(tabulate(cat_data, headers=['カテゴリ', '記事数'], tablefmt='simple'))
    
    if 'monthly' in stats and stats['monthly']:
        print("\n== 月別記事数 ==")
        month_data = []
        for month in stats['monthly'][:10]:  # 直近10ヶ月分のみ表示
            month_data.append([month['month'], month['count']])
        print(tabulate(month_data, headers=['年月', '記事数'], tablefmt='simple'))

def main():
    try:
        print("検索スクリプトを開始します...")
        parser = argparse.ArgumentParser(description='set-ten.com記事データベースを検索')
        
        # サブコマンドのパーサーを作成
        subparsers = parser.add_subparsers(dest='command', help='コマンド')
        
        # listコマンド
        list_parser = subparsers.add_parser('list', help='記事一覧を表示')
        list_parser.add_argument('-n', '--limit', type=int, default=10, help='表示する記事数（デフォルト: 10）')
        list_parser.add_argument('-f', '--format', choices=['table', 'json'], default='table', help='出力形式（デフォルト: table）')
        
        # searchコマンド
        search_parser = subparsers.add_parser('search', help='記事を検索')
        search_parser.add_argument('type', choices=['title', 'category', 'date', 'content'], help='検索タイプ')
        search_parser.add_argument('keyword', help='検索キーワード')
        search_parser.add_argument('-n', '--limit', type=int, default=20, help='表示する記事数（デフォルト: 20）')
        search_parser.add_argument('-f', '--format', choices=['table', 'json'], default='table', help='出力形式（デフォルト: table）')
        
        # statsコマンド
        subparsers.add_parser('stats', help='データベース統計を表示')
        
        args = parser.parse_args()
        print(f"コマンド: {args.command if hasattr(args, 'command') else 'なし'}")
    except Exception as e:
        print(f"パーサー初期化中にエラーが発生しました: {str(e)}")
    
    # コマンドが指定されていない場合はヘルプを表示
    if not hasattr(args, 'command') or not args.command:
        parser.print_help()
        return
    
    try:
        # コマンドに応じた処理を実行
        if args.command == 'list':
            print("記事一覧を取得中...")
            results = get_all_articles(args.limit)
            print(f"{len(results)}件の記事を取得しました")
            print_results(results, args.format)
        elif args.command == 'search':
            print(f"'{args.keyword}'で{args.type}を検索中...")
            results = search_articles(args.type, args.keyword, args.limit)
            print(f"{len(results)}件の記事が見つかりました")
            print_results(results, args.format)
        elif args.command == 'stats':
            print("統計情報を取得中...")
            stats = get_stats()
            print("統計情報を表示します")
            print_stats(stats)
    except Exception as e:
        print(f"コマンド実行中にエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()
