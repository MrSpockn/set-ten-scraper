import sqlite3
import os

def apply_migration():
    """parent_categoryカラムを追加するマイグレーションを適用"""
    db_path = 'setten_articles.db'
    sql_path = 'migrations/add_parent_category_to_articles.sql'
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found")
        return
        
    if not os.path.exists(sql_path):
        print(f"Error: SQL file {sql_path} not found")
        return
    
    try:
        # マイグレーションSQLを読み込む
        with open(sql_path, 'r') as f:
            sql = f.read()
            
        # SQLiteデータベースに接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # トランザクション開始
        cursor.execute('BEGIN TRANSACTION')
        
        try:
            # マイグレーションを実行
            cursor.executescript(sql)
            
            # 変更をコミット
            conn.commit()
            print("Migration successful: parent_category column added to articles table")
            
        except Exception as e:
            # エラーが発生した場合はロールバック
            conn.rollback()
            print(f"Error during migration: {str(e)}")
            raise
            
    except Exception as e:
        print(f"Error: {str(e)}")
        
    finally:
        # 接続を閉じる
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    apply_migration()
