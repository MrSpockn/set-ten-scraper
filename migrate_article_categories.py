import os
import django
import sqlite3
from django.db import transaction

# Django設定を設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setten_viewer.settings')
django.setup()

from articles.models import Article, Category

def migrate_article_categories():
    """既存の記事からカテゴリの関連付けを移行"""
    print("記事のカテゴリ移行を開始...")
    
    # 古いデータベースに接続
    old_conn = sqlite3.connect('setten_articles.db')
    old_cursor = old_conn.cursor()
    
    # 記事とカテゴリの関連を取得
    old_cursor.execute('''
        SELECT h.title, h.url, c.name 
        FROM articles_history h
        LEFT JOIN categories c ON h.category = c.name
        WHERE h.archived_at = (
            SELECT MAX(archived_at) 
            FROM articles_history h2 
            WHERE h2.url = h.url
        )
    ''')
    articles = old_cursor.fetchall()
    
    print(f"移行する記事数: {len(articles)}")
    
    # カテゴリ名からIDへのマッピングを作成
    categories = {cat.name: cat for cat in Category.objects.all()}
    
    # 記事のカテゴリを更新
    with transaction.atomic():
        updated_count = 0
        for title, url, category_name in articles:
            if category_name and category_name in categories:
                # 記事を更新
                updated = Article.objects.filter(url=url).update(
                    category=categories[category_name]
                )
                if updated:
                    updated_count += 1
                    print(f"記事を更新: {title} -> {category_name}")
    
    print(f"合計 {updated_count} 件の記事のカテゴリを更新しました")
    
    old_conn.close()

if __name__ == '__main__':
    migrate_article_categories()
