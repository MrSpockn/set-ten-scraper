from django.contrib import admin
from .models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'post_date', 'crawled_at')
    list_filter = ('category', 'post_date')
    search_fields = ('title', 'content_intro', 'category')
    readonly_fields = ('id', 'title', 'url', 'post_date', 'category', 'content_intro', 'crawled_at')
    
    def has_add_permission(self, request):
        # 管理画面からの追加を許可しない（クローラーによってのみ追加される）
        return False
