from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from students.models import Student

# Check if models exist
try:
    from .models import Book, BookCategory, BookIssue
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    class Book:
        pass
    class BookCategory:
        pass
    class BookIssue:
        pass


class BookListView(LoginRequiredMixin, ListView):
    template_name = 'library/book_list.html'
    context_object_name = 'books'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Book.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            context['categories'] = BookCategory.objects.all()
        else:
            context['categories'] = []
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            Book.objects.create(
                title=request.POST.get('title'),
                author=request.POST.get('author'),
                isbn=request.POST.get('isbn'),
                category_id=request.POST.get('category'),
                quantity=request.POST.get('quantity', 1),
                available_quantity=request.POST.get('quantity', 1)
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class BookCategoryView(LoginRequiredMixin, ListView):
    template_name = 'library/categories.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return BookCategory.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            BookCategory.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', '')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class IssueReturnView(LoginRequiredMixin, ListView):
    template_name = 'library/issue_return.html'
    context_object_name = 'issues'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return BookIssue.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            context['books'] = Book.objects.filter(available_quantity__gt=0)
        else:
            context['books'] = []
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            action = request.POST.get('action')
            if action == 'issue':
                book = Book.objects.get(pk=request.POST.get('book_id'))
                if book.available_quantity > 0:
                    BookIssue.objects.create(
                        book=book,
                        user_id=request.POST.get('user_id'),
                        issue_date=request.POST.get('issue_date'),
                        due_date=request.POST.get('due_date')
                    )
                    book.available_quantity -= 1
                    book.save()
                    return JsonResponse({'success': True})
            elif action == 'return':
                issue = BookIssue.objects.get(pk=request.POST.get('issue_id'))
                issue.return_date = request.POST.get('return_date')
                issue.save()
                book = issue.book
                book.available_quantity += 1
                book.save()
                return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
