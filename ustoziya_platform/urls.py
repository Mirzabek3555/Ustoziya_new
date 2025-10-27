"""
URL configuration for ustoziya_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('materials/', views.materials_list, name='materials_list'),
    path('materials/create/', views.material_create, name='material_create'),
    path('assignments/', views.assignments_list, name='assignments_list'),
    path('videos/', views.videos_list, name='videos_list'),
    path('3d-models/', views.models_3d_list, name='models_3d_list'),
    path('tests/', views.tests_list, name='tests_list'),
    path('tests/<int:pk>/', views.test_detail, name='test_detail'),
    path('tests/create/', views.test_create, name='test_create'),
    path('tests/<int:test_id>/results/', views.test_results, name='test_results'),
    path('tests/<int:test_id>/export/', views.export_single_test_results, name='export_single_test_results'),
    path('tests/ocr-upload/', views.test_ocr_upload, name='test_ocr_upload'),
    path('test-analysis/', views.test_analysis, name='test_analysis'),
    path('export-test-results/', views.export_test_results, name='export_test_results'),
    path('ocr/', views.ocr_upload, name='ocr_upload'),
    path('api/auth/', include('accounts.urls')),
    path('api/materials/', include('materials.urls')),
    path('api/tests/', include('tests.urls')),
    path('api/ocr/', include('ocr_processing.urls', namespace='ocr_processing')),
]

# Media fayllar uchun
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
