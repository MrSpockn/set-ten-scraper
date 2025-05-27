from django.db import models
import json


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='カテゴリ名')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, verbose_name='親カテゴリ')
    slug = models.SlugField(unique=True, verbose_name='スラッグ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = 'カテゴリ'
        verbose_name_plural = 'カテゴリ'
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('articles:category_detail', kwargs={'slug': self.slug})

    @property
    def full_name(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Article(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=500, null=True, verbose_name='タイトル')
    url = models.URLField(unique=True, null=True, verbose_name='URL')
    post_date = models.DateField(null=True, blank=True, verbose_name='投稿日')
    updated_date = models.DateField(null=True, blank=True, verbose_name='更新日')
    content_intro = models.TextField(blank=True, null=True, verbose_name='導入文')
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, 
                                verbose_name='カテゴリ', related_name='articles')
    tags = models.CharField(max_length=500, blank=True, null=True, verbose_name='タグ')
    headings = models.TextField(blank=True, null=True, verbose_name='見出し')
    book_title = models.CharField(max_length=500, blank=True, null=True, verbose_name='書籍タイトル')
    book_author = models.CharField(max_length=200, blank=True, null=True, verbose_name='著者')
    book_isbn = models.CharField(max_length=13, blank=True, null=True, verbose_name='ISBN')
    book_asin = models.CharField(max_length=10, blank=True, null=True, verbose_name='ASIN')
    word_count = models.IntegerField(default=0, verbose_name='文字数')
    internal_links = models.TextField(blank=True, null=True, verbose_name='内部リンク')
    frequent_words = models.TextField(blank=True, null=True, verbose_name='頻出語')
    broken_links = models.TextField(blank=True, null=True, verbose_name='リンク切れ')
    crawled_at = models.DateTimeField(auto_now_add=True, verbose_name='取得日時')

    class Meta:
        managed = True
        db_table = 'articles'
        ordering = ['-post_date']
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
            
    def get_internal_links(self):
        """内部リンクをリストとして取得"""
        if not self.internal_links:
            return []
        try:
            return json.loads(self.internal_links)
        except:
            return []
            
    def get_frequent_words(self):
        """頻出語を辞書として取得"""
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
        links = self.get_internal_links()
        if not links:
            return []
        urls = [link['url'] for link in links]
        return Article.objects.filter(url__in=urls)

    @classmethod
    def get_link_structure(cls):
        """記事間のリンク構造を解析"""
        articles = cls.objects.all()
        structure = []
        for article in articles:
            related = article.get_related_articles()
            if related:
                structure.append({
                    'source': article.id,
                    'target_ids': [rel.id for rel in related]
                })
        return structure
