from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Max
from django.http import JsonResponse
from .models import Article, Category

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
    # カテゴリー一覧を取得（親カテゴリ順、その後に子カテゴリ）
    parent_categories = Category.objects.filter(parent__isnull=True).order_by('name')
    all_categories = []
    for parent in parent_categories:
        all_categories.append(parent)
        child_categories = Category.objects.filter(parent=parent).order_by('name')
        all_categories.extend(child_categories)
    
    # 検索とフィルタリングの処理
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    has_book_info = request.GET.get('has_book', '')
    
    articles = Article.objects.all().order_by('-post_date')
    
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
    selected_category = None
    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        # 選択されたカテゴリが親カテゴリの場合、すべての子カテゴリを含める
        if selected_category.parent is None:
            articles = articles.filter(
                Q(category=selected_category) |
                Q(category__parent=selected_category)
            )
        else:
            # 子カテゴリが選択された場合は、その特定のカテゴリのみ
            articles = articles.filter(category=selected_category)
        
    # 書籍情報あり/なしのフィルター
    if has_book_info == '1':
        articles = articles.filter(
            Q(book_title__isnull=False, book_title__gt='') | 
            Q(book_isbn__isnull=False, book_isbn__gt='') | 
            Q(book_asin__isnull=False, book_asin__gt='')
        )
    
    # 記事を日付順に並べ替え
    articles = articles.order_by('-post_date', '-crawled_at')
    
    # ページネーション
    paginator = Paginator(articles, 10)  # 1ページあたり10件の記事
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'articles': page_obj,
        'categories': all_categories,
        'query': query,
        'selected_category': selected_category,
        'has_book_info': has_book_info,
        'total_count': articles.count(),  # 検索結果の総数
    }
    
    return render(request, 'articles/article_list.html', context)

def article_detail(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    return render(request, 'articles/article_detail.html', {'article': article})

def network_graph(request):
    """カテゴリネットワークのビューを表示"""
    return render(request, 'articles/network_graph.html')

def network_graph_data(request):
    """カテゴリネットワークのデータを返すAPI"""
    from django.db.models import Count
    import json
    
    try:
        # カテゴリー一覧を取得（記事数も含める）
        categories = list(Category.objects.all().annotate(article_count=Count('articles')).order_by('name'))
        print(f"取得したカテゴリ数: {len(categories)}")  # デバッグ出力
        
        nodes = []
        edges = []
        
        # カテゴリをノードとして追加
        for category in categories:
            # カテゴリごとの記事数を取得
            article_count = category.article_count
            print(f"カテゴリ '{category.name}' の記事数: {article_count}")  # デバッグ出力
            
            node = {
                'id': str(category.id),
                'label': f"{category.name}\n({article_count}件)",
                'value': max(article_count * 2, 10),
                'title': f"{category.name}: {article_count}件の記事",
                'group': 'parent' if category.parent is None else 'child',
                'articles': article_count
            }
            nodes.append(node)
            
            # 親カテゴリがある場合、エッジを追加
            if category.parent:
                edge = {
                    'from': str(category.parent.id),
                    'to': str(category.id),
                    'value': max(article_count, 1)
                }
                edges.append(edge)
        
        data = {
            'nodes': nodes,
            'edges': edges
        }
        print(f"生成したデータ: {json.dumps(data, ensure_ascii=False)}")  # デバッグ出力
        return JsonResponse(data)
        
    except Exception as e:
        print(f"エラーが発生: {str(e)}")  # エラー出力
        import traceback
        print(traceback.format_exc())  # スタックトレース
        return JsonResponse({
            'error': str(e),
            'nodes': [],
            'edges': []
        })

def api_article_network(request):
    """記事ネットワークデータを JSON 形式で提供する API"""
    # カテゴリーフィルター
    category = request.GET.get('category', '')
    
    # 記事を取得
    articles = Article.objects.all()
    if category:
        articles = articles.filter(category=category)
    
    # ノードとエッジのデータを準備
    nodes = []
    edges = []
    node_ids = set()  # 処理済みのノードを追跡
    edge_counts = {}  # エッジの参照数を追跡
    
    for article in articles:
        # 記事自体をノードとして追加
        node_data = {
            'id': article.id,
            'label': article.title[:30] + '...' if article.title and len(article.title) > 30 else (article.title or "無題"),
            'title': article.title or "無題",  # ホバー時に表示する完全なタイトル
            'group': article.category or 'その他',
            'value': 1  # ノードの大きさ（後で更新）
        }
        
        if article.id not in node_ids:
            nodes.append(node_data)
            node_ids.add(article.id)
        
        # 内部リンクからエッジを作成
        if article.internal_links:
            try:
                links = eval(article.internal_links)
                for link in links:
                    try:
                        # URLから記事IDを抽出
                        target_id = int(link.split('/')[-2])
                        # エッジの参照数をカウント
                        edge_key = f"{article.id}-{target_id}"
                        edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1
                        
                        # リンク先の記事が存在する場合、ノードを追加
                        target_article = Article.objects.filter(id=target_id).first()
                        if target_article:
                            target_title = target_article.title if target_article.title else "無題"
                            # リンク先の記事をノードとして追加
                            if target_id not in node_ids:
                                nodes.append({
                                    'id': target_id,
                                    'label': target_title[:30] + '...' if len(target_title) > 30 else target_title,
                                    'title': target_title,
                                    'group': target_article.category or 'その他',
                                    'value': 1
                                })
                                node_ids.add(target_id)
                    except (ValueError, IndexError):
                        continue
            except:
                continue
    
    # エッジを作成（参照数を含める）
    for edge_key, count in edge_counts.items():
        source_id, target_id = map(int, edge_key.split('-'))
        edges.append({
            'from': source_id,
            'to': target_id,
            'value': count,  # エッジの太さに参照数を反映
            'title': f'参照数: {count}回',  # ホバー時に表示する参照数
            'arrows': 'to',  # 矢印の方向
        })
    
    # ノードの価値（大きさ）を更新：参照される回数に基づく
    node_references = {}
    for edge in edges:
        node_references[edge['to']] = node_references.get(edge['to'], 0) + edge['value']
    
    for node in nodes:
        node['value'] = node_references.get(node['id'], 1)
    
    return JsonResponse({'nodes': nodes, 'edges': edges})
