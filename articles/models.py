from django.db import models


class Article(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(unique=True, blank=True, null=True)
    post_date = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    content_intro = models.TextField(blank=True, null=True)
    crawled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False  # 既存のデータベースを使用するため、マイグレーションで管理しない
        db_table = 'articles'  # 既存のテーブル名を指定
        ordering = ['-id']  # IDの降順で並べ替え（新しい記事が先に表示される）

    def __str__(self):
        return self.title or f"記事 {self.id}"
