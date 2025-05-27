import os
import django
import sqlite3
from django.utils import timezone
from django.utils.text import slugify

# Django設定を設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setten_viewer.settings')
django.setup()

from articles.models import Article, Category

def get_unique_slug(name, parent_name=None):
    """ユニークなスラッグを生成する"""
    base_slug = slugify(name)
    if parent_name:
        base_slug = f"{slugify(parent_name)}-{base_slug}"
    slug = base_slug
    counter = 1
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

def migrate_categories():
    """既存の記事データからカテゴリを抽出してCategoryモデルに移行"""
    print("カテゴリの移行を開始...")
    
    # 既存のカテゴリをクリア
    Category.objects.all().delete()
    print("既存のカテゴリを削除しました")
    
    # SQLiteデータベースから既存のカテゴリ情報を取得
    old_conn = sqlite3.connect('setten_articles.db')
    old_cursor = old_conn.cursor()
    
    # ユニークなカテゴリとその親カテゴリを取得
    old_cursor.execute('''
        SELECT DISTINCT category 
        FROM articles_history 
        WHERE category IS NOT NULL AND category != ''
        ORDER BY category
    ''')
    categories = old_cursor.fetchall()
    
    print(f"移行するカテゴリ数: {len(categories)}")
    
    # カテゴリを作成
    category_map = {}  # name -> Category オブジェクト
    
    # まず、すべてのメインカテゴリを作成
    main_categories = [
        'キャリア・働き方',
        '技術・AI活用',
        'レビュー・仕事術',
        '投資・マネー'
    ]
    
    for name in main_categories:
        category = Category.objects.create(
            name=name,
            slug=get_unique_slug(name),
            parent=None
        )
        category_map[name] = category
        print(f"メインカテゴリを作成: {name}")
    
    # サブカテゴリを作成
    for (category_path,) in categories:
        parts = [p.strip() for p in category_path.split('>')]
        if len(parts) > 1:  # サブカテゴリがある場合
            subcategory_name = parts[0].strip()
            parent_name = parts[-1].strip()
            
            if subcategory_name not in category_map:
                parent = category_map.get(parent_name)
                if parent:
                    subcategory = Category.objects.create(
                        name=subcategory_name,
                        slug=get_unique_slug(subcategory_name, parent_name),
                        parent=parent
                    )
                    category_map[subcategory_name] = subcategory
                    print(f"サブカテゴリを作成: {subcategory_name} (親: {parent_name})")
    
    print("カテゴリの移行が完了しました")
    old_conn.close()

if __name__ == '__main__':
    migrate_categories()
