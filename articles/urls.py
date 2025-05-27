from django.urls import path
from . import views

app_name = 'articles'

urlpatterns = [
    path('', views.home, name='home'),
    path('articles/', views.article_list, name='article_list'),
    path('article/<int:article_id>/', views.article_detail, name='article_detail'),
    path('network/', views.network_graph, name='network_graph'),
    path('network/data/', views.network_graph_data, name='network_graph_data'),
]
