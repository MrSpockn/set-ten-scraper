from django.contrib import admin
from .models import Article
import json
from django.utils.html import format_html

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'post_date', 'updated_date', 'word_count', 'has_book_info', 'crawled_at')
    list_filter = ('category', 'post_date', 'updated_date')
    search_fields = ('title', 'content_intro', 'category', 'tags', 'book_title', 'book_author')
    readonly_fields = (
        'id', 'title', 'url', 'post_date', 'updated_date', 'category', 'tags',
        'content_intro', 'headings_display', 'book_title', 'book_author', 
        'book_isbn', 'book_asin', 'word_count', 'external_links_display', 
        'frequent_words_display', 'broken_links_display', 'crawled_at'
    )
    fieldsets = (
        ('基本情報', {
            'fields': ('id', 'title', 'url', 'post_date', 'updated_date', 'category', 'tags', 'content_intro', 'word_count')
        }),
        ('記事構造', {
            'fields': ('headings_display',)
        }),
        ('書籍情報', {
            'fields': ('book_title', 'book_author', 'book_isbn', 'book_asin')
        }),
        ('リンクとデータ分析', {
            'fields': ('external_links_display', 'frequent_words_display', 'broken_links_display')
        }),
        ('システム情報', {
            'fields': ('crawled_at',)
        }),
    )
    
    def has_book_info(self, obj):
        """書籍情報があるかどうかを表示"""
        has_info = bool(obj.book_title or obj.book_isbn or obj.book_asin)
        return '✓' if has_info else '✗'
    has_book_info.short_description = '書籍情報'
    has_book_info.boolean = True
    
    def headings_display(self, obj):
        """見出し情報を整形して表示"""
        try:
            headings = json.loads(obj.headings or '[]')
            if not headings:
                return '見出しがありません'
                
            html = '<ol>'
            for h in headings:
                level = h.get('level', 'h2')
                text = h.get('text', '')
                indent = (int(level[-1]) - 2) * 20  # h2=0px, h3=20px, h4=40px...
                html += f'<li style="margin-left:{indent}px">{text} <small>({level})</small></li>'
            html += '</ol>'
            return format_html(html)
        except:
            return 'データのパースエラー'
    headings_display.short_description = '見出し構造'
    
    def external_links_display(self, obj):
        """外部リンクを整形して表示"""
        try:
            links = json.loads(obj.external_links or '[]')
            if not links:
                return '外部リンクがありません'
                
            html = '<ul>'
            for link in links:
                url = link.get('url', '')
                text = link.get('text', url)
                html += f'<li><a href="{url}" target="_blank">{text}</a></li>'
            html += '</ul>'
            return format_html(html)
        except:
            return 'データのパースエラー'
    external_links_display.short_description = '外部リンク'
    
    def frequent_words_display(self, obj):
        """頻出単語を整形して表示"""
        try:
            words = json.loads(obj.frequent_words or '{}')
            if not words:
                return '頻出単語がありません'
                
            # 単語をリスト化して出現頻度の高い順にソート
            word_list = [(word, count) for word, count in words.items()]
            word_list.sort(key=lambda x: x[1], reverse=True)
            
            html = '<ul style="column-count: 3;">'
            for word, count in word_list:
                html += f'<li>{word}: {count}回</li>'
            html += '</ul>'
            return format_html(html)
        except:
            return 'データのパースエラー'
    frequent_words_display.short_description = '頻出単語'
    
    def broken_links_display(self, obj):
        """リンク切れを整形して表示"""
        try:
            links = json.loads(obj.broken_links or '[]')
            if not links:
                return 'リンク切れが見つかりません'
                
            html = '<ul>'
            for link in links:
                html += f'<li>{link}</li>'
            html += '</ul>'
            return format_html(html)
        except:
            return 'データのパースエラー'
    broken_links_display.short_description = 'リンク切れ'
    
    def has_add_permission(self, request):
        # 管理画面からの追加を許可しない（クローラーによってのみ追加される）
        return False
