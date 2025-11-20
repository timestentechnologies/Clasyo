from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Main views
    path('', views.LibraryDashboardView.as_view(), name='dashboard'),
    path('books/', views.BookListView.as_view(), name='book_list'),
    path('books/create/', views.BookCreateView.as_view(), name='book_create'),
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('books/<int:pk>/update/', views.BookUpdateView.as_view(), name='book_update'),
    path('books/<int:pk>/delete/', views.BookDeleteView.as_view(), name='book_delete'),
    
    # Categories
    path('categories/', views.BookCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.BookCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', views.BookCategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.BookCategoryDeleteView.as_view(), name='category_delete'),
    
    # Authors & Publishers
    path('authors/', views.AuthorListView.as_view(), name='author_list'),
    path('publishers/', views.PublisherListView.as_view(), name='publisher_list'),
    
    # Issue & Return
    path('issues/', views.BookIssueListView.as_view(), name='issue_list'),
    path('issues/create/', views.BookIssueCreateView.as_view(), name='issue_create'),
    path('issues/<int:pk>/return/', views.BookReturnView.as_view(), name='book_return'),
    path('issues/<int:pk>/renew/', views.BookRenewView.as_view(), name='book_renew'),
    
    # Reports
    path('reports/overdue/', views.OverdueReportView.as_view(), name='overdue_report'),
    path('reports/popular/', views.PopularBooksReportView.as_view(), name='popular_books_report'),
    
    # My Books (for students/users)
    path('my-books/', views.MyBooksView.as_view(), name='my_books'),
    
    # Autocomplete endpoints
    path('autocomplete/books/', views.BookAutocompleteView.as_view(), name='book_autocomplete'),
    path('get-available-copies/', views.GetAvailableCopiesView.as_view(), name='get_available_copies'),
]
