from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('books/', views.BookListView.as_view(), name='book_list'),
    path('categories/', views.BookCategoryView.as_view(), name='categories'),
    path('issue/', views.IssueReturnView.as_view(), name='issue_return'),
]
