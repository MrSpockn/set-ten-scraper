from django.db import models
import json


class Article(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name='タイトル')
    url = models.URLField(unique=True, blank=True, null=True, verbose_name='URL')
    post_date = models.CharField(max_length=50, blank=True, null=True, verbose_name='投稿日')
    updated_date = models.CharField(max_length=50, blank=True, null=True, verbose_name='更新日')
    category = models.CharField(max_length=255, blank=True, null=True, verbose_name='カテゴリ')
    tags = models.TextField(blank=True, null=True, verbose_name='タグ')  # カンマ区切りで保存
    content_intro = models.TextField(blank=True, null=True, verbose_name='本文冒頭')
    headings = models.TextField(blank=True, null=True, verbose_name='見出し')  # JSONで保存
    
    # 書籍情報
    book_title = models.CharField(max_length=255, blank=True, null=True, verbose_name='書籍名')
    book_author = models.CharField(max_length=255, blank=True, null=True, verbose_name='著者')
    book_isbn = models.CharField(max_length=20, blank=True, null=True, verbose_name='ISBN')
    book_asin = models.CharField(max_length=20, blank=True, null=True, verbose_name='ASIN')
    
    # 付加情報
    word_count = models.IntegerField(blank=True, null=True, verbose_name='文字数')
    external_links = models.TextField(blank=True, null=True, verbose_name='外部リンク')  # JSONで保存
    
    # 加工情報
    frequent_words = models.TextField(blank=True, null=True, verbose_name='頻出単語')  # JSONで保存
    broken_links = models.TextField(blank=True, null=True, verbose_name='リンク切れ')  # JSONで保存
    
    crawled_at = models.DateTimeField(auto_now_add=True, verbose_name='取得日時')

    class Meta:
        managed = False  # 既存のデータベースを使用するため、マイグレーションで管理しない
        db_table = 'articles'  # 既存のテーブル名を指定
        ordering = ['-id']  # IDの降順で並べ替え（新しい記事が先に表示される）
        verbose_name = '記事'
        verbose_name_plural = '記事'

    def __str__(self):
        return self.title or f"記事 {self.id}"
        
    def get_tags_list(self):
        """タグをリストとして取得"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',')]
        
    def get_headings(self):
        """見出しをリストとして取得"""
        if not self.headings:
            return []
        try:
            return json.loads(self.headings)
        except:
            return []
            
    def get_external_links(self):
        """外部リンクをリストとして取得"""
        if not self.external_links:
            return []
        try:
            return json.loads(self.external_links)
        except:
            return []
            
    def get_frequent_words(self):
        """頻出単語を辞書として取得"""
        if not self.frequent_words:
            return {}
        try:
            return json.loads(self.frequent_words)
        except:
            return {}
            
    def get_broken_links(self):
        """リンク切れをリストとして取得"""
        if not self.broken_links:
            return []
        try:
            return json.loads(self.broken_links)
        except:
            return []
            
    def get_related_articles(self):
        """内部リンク（同じドメイン内の記事）を取得"""
        related = []
        try:
            external_links = self.get_external_links()
            for link in external_links:
                url = link.get('url', '')
                if 'set-ten.com' in url:
                    # 同じドメイン内のリンク
                    article = Article.objects.filter(url=url).first()
                    if article:
                        related.append(article)
            return related
        except Exception as e:
            print(f"関連記事取得エラー: {e}")
            return []
    
    @classmethod
    def get_link_structure(cls):
        """記事間のリンク構造を解析"""
        nodes = []
        edges = []
        articles = cls.objects.all()
        
        # ノードの作成（すべての記事）
        for article in articles:
            nodes.append({
                'id': article.id,
                'label': article.title,
                'category': article.category,
                'url': f'/article/{article.id}/'
            })
        
        # エッジの作成（記事間のリンク）
        for article in articles:
            try:
                external_links = json.loads(article.external_links or '[]')
                for link in external_links:
                    url = link.get('url', '')
                    if 'set-ten.com' in url:
                        # リンク先の記事を検索
                        target = cls.objects.filter(url=url).first()
                        if target:
                            edges.append({
                                'from': article.id,
                                'to': target.id,
                                'arrows': 'to'
                            })
            except Exception as e:
                print(f"リンク構造解析エラー: {e}")
        
        return {'nodes': nodes, 'edges': edges}
