from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_GET
from django.db.models.functions import Concat
from django.db.models import Value as V
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import BookCategory, Publisher, Author, Book, BookCopy, BookIssue
from students.models import Student
from django import forms
from core.utils import get_current_school


@method_decorator(csrf_exempt, name='dispatch')
class GetAvailableCopiesView(LoginRequiredMixin, View):
    """View to get available copies of a book"""
    
    def get(self, request, school_slug, *args, **kwargs):
        book_id = request.GET.get('book')
        if not book_id:
            return JsonResponse({'error': 'Book ID is required'}, status=400)
            
        try:
            school = get_current_school(request)
            if not school:
                return JsonResponse({'error': 'School not found'}, status=400)
            book = Book.objects.get(id=book_id, school=school)
            available_copies = book.copies.filter(status='available')
            
            copies_data = [{
                'id': copy.id,
                'accession_number': copy.accession_number,
                'condition': copy.get_condition_display(),
                'status': copy.get_status_display()
            } for copy in available_copies]
            
            return JsonResponse({
                'success': True,
                'book': {
                    'id': book.id,
                    'title': book.title,
                    'available_quantity': book.available_quantity,
                    'total_quantity': book.quantity
                },
                'copies': copies_data
            })
            
        except Book.DoesNotExist:
            return JsonResponse({'error': 'Book not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class BookAutocompleteView(LoginRequiredMixin, View):
    """View for book autocomplete search"""
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        query = request.GET.get('q', '').strip()
        
        if not query:
            return JsonResponse({'results': []})
            
        # Search in title, author, or ISBN
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(isbn__iexact=query),
            school__slug=school_slug
        ).distinct()[:10]  # Limit to 10 results
        
        results = [{
            'id': book.id,
            'text': f"{book.title} - {', '.join([str(a) for a in book.authors.all()])} ({book.isbn})",
            'title': book.title,
            'authors': ', '.join([str(a) for a in book.authors.all()]),
            'isbn': book.isbn,
            'available': book.available_quantity > 0
        } for book in books]
        
        return JsonResponse({'results': results})


class LibraryDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for library"""
    template_name = 'library/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        school = get_current_school(self.request)
        # Get recent books
        recent_books = Book.objects.all()
        if school:
            recent_books = recent_books.filter(school=school)
        context['recent_books'] = recent_books.order_by('-created_at')[:10]
        
        # Get statistics
        books_qs = Book.objects.all()
        categories_qs = BookCategory.objects.all()
        authors_qs = Author.objects.all()
        publishers_qs = Publisher.objects.all()
        if school:
            books_qs = books_qs.filter(school=school)
            categories_qs = categories_qs.filter(school=school)
            authors_qs = authors_qs.filter(school=school)
            publishers_qs = publishers_qs.filter(school=school)
        context['total_books'] = books_qs.count()
        context['total_categories'] = categories_qs.count()
        context['total_authors'] = authors_qs.count()
        context['total_publishers'] = publishers_qs.count()
        
        # Count books by status
        context['available_books'] = books_qs.filter(status='available').count()
        context['issued_books'] = books_qs.filter(status='issued').count()
        
        # Get recent issues
        issues_qs = BookIssue.objects.filter(status='issued')
        if school:
            issues_qs = issues_qs.filter(book__school=school)
        context['recent_issues'] = issues_qs.order_by('-issue_date')[:10]
        
        # Get overdue books
        overdue_qs = BookIssue.objects.filter(status='issued', due_date__lt=timezone.now().date())
        if school:
            overdue_qs = overdue_qs.filter(book__school=school)
        context['overdue_issues'] = overdue_qs.order_by('due_date')
        
        return context


class BookListView(LoginRequiredMixin, ListView):
    """List all books"""
    model = Book
    template_name = 'library/book_list.html'
    context_object_name = 'books'
    paginate_by = 20
    
    def get_queryset(self):
        school = get_current_school(self.request)
        queryset = Book.objects.all()
        if school:
            queryset = queryset.filter(school=school)
        
        # Apply filters
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        author_id = self.request.GET.get('author')
        if author_id:
            queryset = queryset.filter(authors__id=author_id)
            
        publisher_id = self.request.GET.get('publisher')
        if publisher_id:
            queryset = queryset.filter(publisher_id=publisher_id)
            
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(authors__name__icontains=search) |
                Q(isbn__icontains=search) |
                Q(call_number__icontains=search)
            ).distinct()
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        categories_qs = BookCategory.objects.all()
        authors_qs = Author.objects.all()
        publishers_qs = Publisher.objects.all()
        if school:
            categories_qs = categories_qs.filter(school=school)
            authors_qs = authors_qs.filter(school=school)
            publishers_qs = publishers_qs.filter(school=school)
        context['categories'] = categories_qs
        context['authors'] = authors_qs
        context['publishers'] = publishers_qs
        context['status_choices'] = Book.BOOK_STATUS_CHOICES
        
        # Current filters
        context['current_filters'] = {}
        for param in ['category', 'status', 'author', 'publisher', 'search']:
            value = self.request.GET.get(param)
            if value:
                context['current_filters'][param] = value
        
        return context


class BookDetailView(LoginRequiredMixin, DetailView):
    """View book details"""
    model = Book
    template_name = 'library/book_detail.html'
    context_object_name = 'book'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Book.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Get book copies
        context['copies'] = self.object.copies.all()
        
        # Get current issues
        context['current_issues'] = BookIssue.objects.filter(
            book=self.object,
            status='issued'
        ).select_related('student', 'user')
        
        # Check if user is librarian or admin
        context['can_manage'] = self.request.user.is_school_admin or hasattr(self.request.user, 'librarian')
        
        return context


class BookCategoryListView(LoginRequiredMixin, ListView):
    """List all book categories"""
    model = BookCategory
    template_name = 'library/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = BookCategory.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class AuthorListView(LoginRequiredMixin, ListView):
    """List all authors"""
    model = Author
    template_name = 'library/author_list.html'
    context_object_name = 'authors'
    paginate_by = 30
    
    def get_queryset(self):
        school = get_current_school(self.request)
        queryset = Author.objects.all()
        if school:
            queryset = queryset.filter(school=school)
        
        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class PublisherListView(LoginRequiredMixin, ListView):
    """List all publishers"""
    model = Publisher
    template_name = 'library/publisher_list.html'
    context_object_name = 'publishers'
    paginate_by = 30
    
    def get_queryset(self):
        school = get_current_school(self.request)
        queryset = Publisher.objects.all()
        if school:
            queryset = queryset.filter(school=school)
        
        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class BookIssueListView(LoginRequiredMixin, ListView):
    """List all book issues"""
    model = BookIssue
    template_name = 'library/issue_list.html'
    context_object_name = 'issues'
    paginate_by = 25
    
    def get_queryset(self):
        school = get_current_school(self.request)
        queryset = BookIssue.objects.all().select_related('book', 'student', 'user')
        if school:
            queryset = queryset.filter(book__school=school)
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        book_id = self.request.GET.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
            
        overdue = self.request.GET.get('overdue')
        if overdue == 'yes':
            queryset = queryset.filter(
                status='issued',
                due_date__lt=timezone.now().date()
            )
        
        # Default ordering
        sort = self.request.GET.get('sort', '-issue_date')
        if sort in ['issue_date', '-issue_date', 'due_date', '-due_date']:
            queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-issue_date')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['status_choices'] = BookIssue.ISSUE_STATUS_CHOICES
        
        # Current filters
        context['current_filters'] = {}
        for param in ['status', 'student', 'book', 'overdue', 'sort']:
            value = self.request.GET.get(param)
            if value:
                context['current_filters'][param] = value
        
        return context


class BookCreateView(LoginRequiredMixin, CreateView):
    """Create a new book"""
    model = Book
    template_name = 'library/book_form.html'
    fields = ['title', 'subtitle', 'authors', 'isbn', 'publisher', 'publication_date', 'edition',
              'category', 'subjects', 'pages', 'dimensions', 'weight', 'description',
              'table_of_contents', 'language', 'call_number', 'location', 'acquisition_date',
              'price', 'quantity', 'available_quantity', 'cover_image', 'digital_copy',
              'is_digital', 'is_reference', 'loan_period_days', 'max_renewals']
    
    def form_valid(self, form):
        # Prepare instance
        school = get_current_school(self.request)
        obj = form.save(commit=False)
        obj.created_by = self.request.user
        obj.school = school

        # Handle dynamic publisher/category from free-text inputs
        new_publisher_name = (self.request.POST.get('new_publisher_name') or '').strip()
        new_category_name = (self.request.POST.get('new_category_name') or '').strip()

        if new_publisher_name:
            existing_pub = Publisher.objects.filter(school=school, name__iexact=new_publisher_name).first()
            obj.publisher = existing_pub or Publisher.objects.create(school=school, name=new_publisher_name)

        if new_category_name:
            existing_cat = BookCategory.objects.filter(school=school, name__iexact=new_category_name).first()
            obj.category = existing_cat or BookCategory.objects.create(school=school, name=new_category_name)

        # Save book first
        obj.save()

        # Save existing many2many selections
        form.instance = obj
        form.save_m2m()

        # Handle dynamic authors
        new_authors = [a.strip() for a in self.request.POST.getlist('new_authors') if a and a.strip()]
        for author_name in new_authors:
            existing_auth = Author.objects.filter(school=school, name__iexact=author_name).first()
            author = existing_auth or Author.objects.create(school=school, name=author_name)
            obj.authors.add(author)

        messages.success(self.request, _('Book created successfully'))
        self.object = obj
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('library:book_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.pk
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Add New Book')
        return context


class BookUpdateView(LoginRequiredMixin, UpdateView):
    """Update a book"""
    model = Book
    template_name = 'library/book_form.html'
    fields = ['title', 'subtitle', 'authors', 'isbn', 'publisher', 'publication_date', 'edition',
              'category', 'subjects', 'pages', 'dimensions', 'weight', 'description',
              'table_of_contents', 'language', 'call_number', 'location', 'acquisition_date',
              'price', 'quantity', 'available_quantity', 'cover_image', 'digital_copy',
              'is_digital', 'is_reference', 'loan_period_days', 'max_renewals']
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Book.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def form_valid(self, form):
        school = get_current_school(self.request)
        obj = form.save(commit=False)

        # Handle dynamic publisher/category
        new_publisher_name = (self.request.POST.get('new_publisher_name') or '').strip()
        new_category_name = (self.request.POST.get('new_category_name') or '').strip()

        if new_publisher_name:
            existing_pub = Publisher.objects.filter(school=school, name__iexact=new_publisher_name).first()
            obj.publisher = existing_pub or Publisher.objects.create(school=school, name=new_publisher_name)

        if new_category_name:
            existing_cat = BookCategory.objects.filter(school=school, name__iexact=new_category_name).first()
            obj.category = existing_cat or BookCategory.objects.create(school=school, name=new_category_name)

        obj.save()
        form.instance = obj
        form.save_m2m()

        # New authors appended
        new_authors = [a.strip() for a in self.request.POST.getlist('new_authors') if a and a.strip()]
        for author_name in new_authors:
            existing_auth = Author.objects.filter(school=school, name__iexact=author_name).first()
            author = existing_auth or Author.objects.create(school=school, name=author_name)
            obj.authors.add(author)

        messages.success(self.request, _('Book updated successfully'))
        self.object = obj
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('library:book_detail', kwargs={
            'school_slug': self.kwargs.get('school_slug', ''),
            'pk': self.object.pk
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Book')
        return context


class BookDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a book"""
    model = Book
    template_name = 'library/confirm_delete.html'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Book.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_success_url(self):
        return reverse('library:book_list', kwargs={'school_slug': self.kwargs.get('school_slug', '')})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Book')
        context['message'] = _('Are you sure you want to delete this book?')
        return context


class BookReturnView(LoginRequiredMixin, View):
    """Return a book"""
    
    def post(self, request, *args, **kwargs):
        issue_id = kwargs.get('pk')
        school = get_current_school(request)
        qs = BookIssue.objects.filter(pk=issue_id, status='issued')
        if school:
            qs = qs.filter(book__school=school)
        issue = get_object_or_404(qs)
        
        # Update issue status
        issue.status = 'returned'
        issue.returned_date = timezone.now().date()
        issue.received_by = request.user
        
        # Get condition on return
        condition = request.POST.get('condition', 'good')
        issue.condition_on_return = condition
        
        # Save changes
        issue.save()
        
        messages.success(request, _('Book returned successfully'))
        return redirect('library:issue_list', school_slug=self.kwargs.get('school_slug', ''))


class BookRenewView(LoginRequiredMixin, View):
    """Renew a book loan"""
    
    def post(self, request, *args, **kwargs):
        issue_id = kwargs.get('pk')
        school = get_current_school(request)
        qs = BookIssue.objects.filter(pk=issue_id, status='issued')
        if school:
            qs = qs.filter(book__school=school)
        issue = get_object_or_404(qs)
        
        # Get renewal days from post or use default
        days = request.POST.get('days')
        if days:
            days = int(days)
        
        # Call renew method
        if issue.renew(days):
            messages.success(request, _('Book renewed successfully'))
        else:
            messages.error(request, _('Cannot renew this book. Maximum renewals reached.'))
            
        return redirect('library:issue_list', school_slug=self.kwargs.get('school_slug', ''))


class MyBooksView(LoginRequiredMixin, ListView):
    """View books issued to current user"""
    model = BookIssue
    template_name = 'library/my_books.html'
    context_object_name = 'issues'
    
    def get_queryset(self):
        user = self.request.user
        school = get_current_school(self.request)
        
        # Get student if user is a student
        student = None
        if hasattr(user, 'student'):
            student = user.student
        
        # Get book issues
        if student:
            qs = BookIssue.objects.filter(student=student).select_related('book')
        else:
            qs = BookIssue.objects.filter(user=user).select_related('book')
        if school:
            qs = qs.filter(book__school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Split issues into current and past
        all_issues = self.get_queryset()
        context['current_issues'] = all_issues.filter(status='issued')
        context['past_issues'] = all_issues.exclude(status='issued')
        
        # Check for overdue books
        context['has_overdue'] = context['current_issues'].filter(
            due_date__lt=timezone.now().date()
        ).exists()
        
        return context


class OverdueReportView(LoginRequiredMixin, ListView):
    """View overdue books report"""
    model = BookIssue
    template_name = 'library/overdue_report.html'
    context_object_name = 'overdue_issues'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = BookIssue.objects.filter(status='issued', due_date__lt=timezone.now().date()).select_related('book', 'student', 'user')
        if school:
            qs = qs.filter(book__school=school)
        return qs.order_by('due_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Group by days overdue
        overdue_issues = self.get_queryset()
        today = timezone.now().date()
        
        context['overdue_groups'] = {
            'critical': overdue_issues.filter(due_date__lt=today - timezone.timedelta(days=30)),
            'high': overdue_issues.filter(due_date__range=[today - timezone.timedelta(days=30), today - timezone.timedelta(days=15)]),
            'medium': overdue_issues.filter(due_date__range=[today - timezone.timedelta(days=15), today - timezone.timedelta(days=7)]),
            'low': overdue_issues.filter(due_date__range=[today - timezone.timedelta(days=7), today - timezone.timedelta(days=1)]),
        }
        
        return context


class PopularBooksReportView(LoginRequiredMixin, TemplateView):
    """View report on popular books"""
    template_name = 'library/popular_books_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        
        # Most issued books
        books_qs = Book.objects.all()
        if school:
            books_qs = books_qs.filter(school=school)
        context['most_issued'] = books_qs.annotate(
            issue_count=Count('issues')
        ).order_by('-issue_count')[:10]
        
        # Most issued by category
        categories_qs = BookCategory.objects.all()
        if school:
            categories_qs = categories_qs.filter(school=school)
        context['by_category'] = categories_qs.annotate(
            issue_count=Count('books__issues')
        ).order_by('-issue_count')
        
        # Recent issues
        issues_qs = BookIssue.objects.all()
        if school:
            issues_qs = issues_qs.filter(book__school=school)
        context['recent_issues'] = issues_qs.order_by('-issue_date')[:20]
        
        return context


class BookCategoryCreateView(LoginRequiredMixin, CreateView):
    """Create a new book category"""
    model = BookCategory
    template_name = 'library/category_form.html'
    fields = ['name', 'description', 'parent_category', 'icon']
    
    def form_valid(self, form):
        # Set creator
        form.instance.created_by = self.request.user
        
        # Associate with school
        school_slug = self.kwargs.get('school_slug')
        from tenants.models import School
        try:
            school = School.objects.get(slug=school_slug)
            form.instance.school = school
        except School.DoesNotExist:
            pass
        
        messages.success(self.request, _('Book category created successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('library:category_list', kwargs={
            'school_slug': self.kwargs.get('school_slug', '')
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Add New Category')
        return context


class BookCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """Update a book category"""
    model = BookCategory
    template_name = 'library/category_form.html'
    fields = ['name', 'description', 'parent_category', 'icon']
    
    def form_valid(self, form):
        messages.success(self.request, _('Book category updated successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('library:category_list', kwargs={
            'school_slug': self.kwargs.get('school_slug', '')
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Category')
        return context


class BookCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a book category"""
    model = BookCategory
    template_name = 'library/confirm_delete.html'
    
    def get_success_url(self):
        return reverse('library:category_list', kwargs={
            'school_slug': self.kwargs.get('school_slug', '')
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Category')
        context['message'] = _('Are you sure you want to delete this category?')
        context['note'] = _('This will NOT delete the books in this category.')
        return context


class BookIssueCreateView(LoginRequiredMixin, CreateView):
    """Create a new book issue"""
    model = BookIssue
    template_name = 'library/issue_form.html'
    fields = ['book', 'book_copy', 'user', 'student', 'due_date', 'condition_on_issue']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Add classes and improve widgets
        form.fields['book'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['book_copy'].widget.attrs.update({'class': 'form-select'})
        form.fields['user'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['student'].widget.attrs.update({'class': 'form-select select2'})
        form.fields['due_date'].widget = forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        
        school = get_current_school(self.request)
        qs = Book.objects.filter(available_quantity__gt=0)
        if school:
            qs = qs.filter(school=school)
        form.fields['book'].queryset = qs
        
        # Filter book copies based on selected book (to be enhanced with AJAX)
        if 'book' in self.request.GET:
            book_id = self.request.GET.get('book')
            form.fields['book_copy'].queryset = BookCopy.objects.filter(
                book_id=book_id,
                status='available'
            )
        else:
            form.fields['book_copy'].queryset = BookCopy.objects.none()
        
        return form
    
    def form_valid(self, form):
        # Set issued_by to current user
        form.instance.issued_by = self.request.user
        
        # Set issue_date to today
        form.instance.issue_date = timezone.now().date()
        
        # Set status to issued
        form.instance.status = 'issued'
        
        messages.success(self.request, _('Book issued successfully'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('library:issue_list', kwargs={
            'school_slug': self.kwargs.get('school_slug', '')
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Issue Book')
        return context
