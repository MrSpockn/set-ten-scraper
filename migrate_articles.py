import os
import django
import sqlite3
from django.utils import timezone
from datetime import datetime

# Django設定を設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setten_viewer.settings')
django.setup()

from articles.models import Article, Category

def parse_date(date_str):
    """日付文字列をパースしてdatetimeオブジェクトを返す"""
    if not date_str:
        return None
    try:
        # タイムゾーン情報を削除
        date_str = date_str.split('+')[0].strip()
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            print(f"日付のパースに失敗: {date_str}")
            return None

def migrate_articles():
    """既存の記事データを移行"""
    print("記事データの移行を開始...")
    
    # 古いデータベースに接続
    old_conn = sqlite3.connect('setten_articles.db')
    old_cursor = old_conn.cursor()
    
    # 最新の記事データを取得
    old_cursor.execute('''
        SELECT h.*
        FROM articles_history h
        WHERE h.archived_at = (
            SELECT MAX(archived_at) 
            FROM articles_history h2 
            WHERE h2.url = h.url
        )
    ''')
    
    # カラム名を取得
    columns = [description[0] for description in old_cursor.description]
    print(f"カラム: {columns}")
    
    # 記事データを取得
    articles_data = old_cursor.fetchall()
    print(f"移行する記事数: {len(articles_data)}")
    
    if not articles_data:
        print("記事データが見つかりません")
        return
    
    # カテゴリマッピングを作成
    categories = {}  # name -> Category オブジェクト
    for category in Category.objects.all():
        categories[category.name] = category
    print(f"カテゴリ: {list(categories.keys())}")
    
    # 既存の記事を削除
    Article.objects.all().delete()
    print("既存の記事を削除しました")
    
    # 記事を作成
    created_count = 0
    error_count = 0
    for article_data in articles_data:
        # 辞書にデータを変換
        article_dict = dict(zip(columns, article_data))
        try:
            title = article_dict.get('title')
            url = article_dict.get('url')
            category_path = article_dict.get('category')
            
            if not title or not url:
                continue
            
            # カテゴリの解決
            category = None
            if category_path:
                parts = [p.strip() for p in category_path.split('>')]
                if len(parts) > 0:
                    subcategory_name = parts[0]
                    category = categories.get(subcategory_name)
            
            print(f"記事を作成: {title} ({category_path if category_path else 'カテゴリなし'})")
            
            article = Article.objects.create(
                title=title,
                url=url,
                post_date=parse_date(article_dict.get('post_date')),
                updated_date=parse_date(article_dict.get('updated_date')),
                content_intro=article_dict.get('content_intro'),
                tags=article_dict.get('tags'),
                headings=article_dict.get('headings'),
                book_title=article_dict.get('book_title'),
                book_author=article_dict.get('book_author'),
                book_isbn=article_dict.get('book_isbn'),
                book_asin=article_dict.get('book_asin'),
                word_count=int(article_dict.get('word_count', 0) or 0),
                internal_links=article_dict.get('internal_links'),
                frequent_words=article_dict.get('frequent_words'),
                broken_links=article_dict.get('broken_links'),
                crawled_at=parse_date(article_dict.get('crawled_at')) or timezone.now(),
                category=category
            )
            created_count += 1
            if created_count % 10 == 0:
                print(f"{created_count}件の記事を作成しました")
        except Exception as e:
            print(f"記事の作成に失敗: {title} - {str(e)}")
            error_count += 1
    
    print(f"合計 {created_count} 件の記事を作成しました（エラー: {error_count}件）")
    
    old_conn.close()

if __name__ == '__main__':
    migrate_articles()
