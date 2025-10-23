from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.MaterialCategoryListView.as_view(), name='material_category_list'),
    path('', views.MaterialListView.as_view(), name='material_list'),
    path('create/', views.MaterialCreateView.as_view(), name='material_create'),
    path('<int:pk>/', views.MaterialDetailView.as_view(), name='material_detail'),
    path('<int:pk>/update/', views.MaterialUpdateView.as_view(), name='material_update'),
    path('<int:pk>/delete/', views.MaterialDeleteView.as_view(), name='material_delete'),
    path('<int:pk>/download/', views.download_material, name='material_download'),
    path('<int:pk>/rate/', views.rate_material, name='material_rate'),
    path('search/', views.search_materials, name='search_materials'),
]
