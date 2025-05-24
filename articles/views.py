from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Max
from django.core.paginator import Paginator
import datetime
from .models import Article
# フォーム関連のインポートを一時的に無効化
# from .forms import ArticleSearchForm

def home(request):
    """ホームページ表示"""
    article_count = Article.objects.count()
    latest_date = Article.objects.aggregate(latest=Max('crawled_at'))['latest']
    
    context = {
        'article_count': article_count,
        'latest_date': latest_date,
    }
    
    return render(request, 'articles/home.html', context)

def article_list(request):
    # 一時的にフォームを使わない簡易実装に戻す
    # form = ArticleSearchForm(request.GET or None)
    
    # カテゴリー一覧を取得（重複なし、名前順）
    categories = Article.objects.values_list('category', flat=True).distinct().order_by('category')
    
    # 検索とフィルタリングの処理
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    articles = Article.objects.all()
    
    # 検索キーワードがある場合
    if query:
        articles = articles.filter(
            Q(title__icontains=query) | 
            Q(content_intro__icontains=query)
        )
    
    # カテゴリーフィルターがある場合
    if category:
        articles = articles.filter(category=category)
    
    # ページネーション
    paginator = Paginator(articles, 10)  # 1ページあたり10件の記事
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    
    context = {
        'articles': articles,
        'categories': categories,
        'query': query,
        'selected_category': category,
    }
    
    return render(request, 'articles/article_list.html', context)

def article_detail(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    return render(request, 'articles/article_detail.html', {'article': article})
