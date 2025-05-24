from django import forms
from .models import Article


class ArticleSearchForm(forms.Form):
    """記事検索フォーム"""
    q = forms.CharField(
        label='キーワード',
        required=False,
        widget=forms.TextInput(attrs={'class': 'search-input', 'placeholder': 'キーワードで検索'})
    )
    
    category = forms.ChoiceField(
        label='カテゴリー',
        required=False,
        widget=forms.Select(attrs={'class': 'category-select'})
    )
    
    date_from = forms.DateField(
        label='開始日',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'})
    )
    
    date_to = forms.DateField(
        label='終了日',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 動的にカテゴリー選択肢を設定
        categories = Article.objects.values_list('category', flat=True).distinct().order_by('category')
        self.fields['category'].choices = [('', '全カテゴリー')] + [(c, c) for c in categories if c]
