from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.TestCategoryListView.as_view(), name='test_category_list'),
    path('', views.TestListView.as_view(), name='test_list'),
    path('create/', views.TestCreateView.as_view(), name='test_create'),
    path('<int:pk>/', views.TestDetailView.as_view(), name='test_detail'),
    path('<int:pk>/update/', views.TestUpdateView.as_view(), name='test_update'),
    path('<int:pk>/delete/', views.TestDeleteView.as_view(), name='test_delete'),
    path('<int:pk>/questions/', views.QuestionListView.as_view(), name='question_list'),
    path('<int:pk>/questions/create/', views.QuestionCreateView.as_view(), name='question_create'),
    path('questions/<int:question_pk>/', views.QuestionDetailView.as_view(), name='question_detail'),
    path('questions/<int:question_pk>/update/', views.QuestionUpdateView.as_view(), name='question_update'),
    path('questions/<int:question_pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),
    path('<int:pk>/attempts/', views.TestAttemptListView.as_view(), name='test_attempt_list'),
    path('<int:pk>/attempts/<int:attempt_pk>/', views.TestAttemptDetailView.as_view(), name='test_attempt_detail'),
    path('<int:pk>/start/', views.start_test, name='start_test'),
    path('<int:pk>/submit/', views.submit_test, name='submit_test'),
    path('search/', views.search_tests, name='search_tests'),
]
