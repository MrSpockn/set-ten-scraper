from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Max
from django.core.paginator import Paginator
import datetime
from django.http import JsonResponse
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
    has_book_info = request.GET.get('has_book', '')
    
    articles = Article.objects.all()
    
    # 検索キーワードがある場合
    if query:
        articles = articles.filter(
            Q(title__icontains=query) | 
            Q(content_intro__icontains=query) |
            Q(tags__icontains=query) |
            Q(book_title__icontains=query) |
            Q(book_author__icontains=query)
        )
    
    # カテゴリーフィルターがある場合
    if category:
        articles = articles.filter(category=category)
        
    # 書籍情報あり/なしのフィルター
    if has_book_info == '1':
        articles = articles.filter(
            Q(book_title__isnull=False, book_title__gt='') | 
            Q(book_isbn__isnull=False, book_isbn__gt='') | 
            Q(book_asin__isnull=False, book_asin__gt='')
        )
    
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

def network_graph(request):
    """記事のネットワークグラフを表示"""
    # カテゴリー一覧を取得（重複なし、名前順）
    categories = Article.objects.exclude(
        category__isnull=True
    ).exclude(
        category__exact=''
    ).values_list(
        'category', flat=True
    ).distinct().order_by('category')
    
    # 記事の総数を取得
    article_count = Article.objects.count()
    
    context = {
        'categories': categories,
        'article_count': article_count,
    }
    
    return render(request, 'articles/network_graph.html', context)

def api_article_network(request):
    """記事ネットワークデータを JSON 形式で提供する API"""
    try:
        # フィルタリング
        category = request.GET.get('category', '')
        
        # Article モデルから記事間のリンク構造を取得
        network_data = Article.get_link_structure()
        
        # カテゴリーフィルターが指定されている場合
        if category:
            # ノードをフィルタリング
            filtered_nodes = [node for node in network_data['nodes'] if node.get('category') == category]
            node_ids = {node['id'] for node in filtered_nodes}
            
            # エッジをフィルタリング（両端のノードが選択したカテゴリーに属している場合のみ）
            filtered_edges = [
                edge for edge in network_data['edges']
                if edge['from'] in node_ids and edge['to'] in node_ids
            ]
            
            network_data = {
                'nodes': filtered_nodes,
                'edges': filtered_edges
            }
        
        return JsonResponse(network_data)
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'nodes': [],
            'edges': []
        }, status=500)
