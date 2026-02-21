from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator

from tenants.models import School
from .models import Club, ClubMembership, ClubActivity, ClubAttendance, ClubAchievement, ClubResource
from .forms import ClubForm, ClubMembershipForm, ClubActivityForm, ClubAchievementForm, ClubResourceForm

class ClubListView(LoginRequiredMixin, ListView):
    """List all clubs for the school"""
    model = Club
    template_name = 'clubs/club_list.html'
    context_object_name = 'clubs'
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'parent':
            school_slug = kwargs.get('school_slug')
            messages.info(request, "Parents can only view clubs for their children.")
            return redirect(f"/school/{school_slug}/children-clubs/")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        school_slug = self.kwargs.get('school_slug')
        school = get_object_or_404(School, slug=school_slug)
        
        queryset = Club.objects.filter(school=school, is_active=True)
        
        # Filter by club type if specified
        club_type = self.request.GET.get('type')
        if club_type:
            queryset = queryset.filter(club_type=club_type)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset.annotate(
            members_count=Count('memberships', filter=Q(memberships__status='active'))
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug')
        context['club_types'] = Club.CLUB_TYPES
        context['selected_type'] = self.request.GET.get('type', '')
        context['search_query'] = self.request.GET.get('search', '')
        
        # Get user's club memberships
        if self.request.user.role == 'student':
            context['user_memberships'] = ClubMembership.objects.filter(
                student=self.request.user,
                status='active'
            ).select_related('club')
        
        return context

class ClubDetailView(LoginRequiredMixin, DetailView):
    """Club details with membership and activity information"""
    model = Club
    template_name = 'clubs/club_detail.html'
    context_object_name = 'club'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'parent':
            school_slug = kwargs.get('school_slug')
            messages.info(request, "Parents can only view clubs for their children.")
            return redirect(f"/school/{school_slug}/children-clubs/")
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self):
        school_slug = self.kwargs.get('school_slug')
        club_id = self.kwargs.get('pk')
        return get_object_or_404(Club, id=club_id, school__slug=school_slug)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug')
        
        club = self.get_object()
        
        # Club membership status for current user
        if self.request.user.role == 'student':
            context['user_membership'] = ClubMembership.objects.filter(
                student=self.request.user,
                club=club
            ).first()
        
        # Recent activities
        context['recent_activities'] = ClubActivity.objects.filter(
            club=club,
            date__gte=timezone.now() - timezone.timedelta(days=30)
        ).order_by('-date')[:5]
        
        # Upcoming activities
        context['upcoming_activities'] = ClubActivity.objects.filter(
            club=club,
            date__gte=timezone.now()
        ).order_by('date')[:5]
        
        # Active members
        context['active_members'] = ClubMembership.objects.filter(
            club=club,
            status='active'
        ).select_related('student')[:20]
        
        # Recent achievements
        context['achievements'] = ClubAchievement.objects.filter(
            club=club
        ).order_by('-date_achieved')[:5]
        
        # Available resources
        context['resources'] = ClubResource.objects.filter(
            club=club,
            is_public=True
        ).order_by('-created_at')[:10]
        
        return context

class ClubCreateView(LoginRequiredMixin, CreateView):
    """Create a new club (admin/teacher only)"""
    model = Club
    form_class = ClubForm
    template_name = 'clubs/club_form.html'
    success_url = reverse_lazy('clubs:club_list')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['admin', 'teacher']:
            messages.error(request, 'You don\'t have permission to create clubs.')
            return redirect('clubs:club_list', school_slug=self.kwargs.get('school_slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        school_slug = self.kwargs.get('school_slug')
        kwargs['school'] = get_object_or_404(School, slug=school_slug)
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('clubs:club_list', kwargs={'school_slug': self.kwargs.get('school_slug')})
    
    def form_valid(self, form):
        messages.success(self.request, f'Club "{form.instance.name}" created successfully!')
        return super().form_valid(form)

class ClubUpdateView(LoginRequiredMixin, UpdateView):
    """Update club details (admin/teacher/advisor only)"""
    model = Club
    form_class = ClubForm
    template_name = 'clubs/club_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        club = self.get_object()
        if (request.user.role not in ['admin', 'teacher'] and 
            request.user != club.teacher_advisor):
            messages.error(request, 'You don\'t have permission to edit this club.')
            return redirect('clubs:club_detail', 
                          school_slug=self.kwargs.get('school_slug'),
                          pk=club.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        club = self.get_object()
        kwargs['school'] = club.school
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('clubs:club_detail', 
                          kwargs={'school_slug': self.kwargs.get('school_slug'),
                                 'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Club "{form.instance.name}" updated successfully!')
        return super().form_valid(form)

class ClubDeleteView(LoginRequiredMixin, DeleteView):
    """Delete club (admin only)"""
    model = Club
    template_name = 'clubs/club_confirm_delete.html'
    
    def dispatch(self, request, *args, **kwargs):
        club = self.get_object()
        if request.user.role != 'admin':
            messages.error(request, 'Only administrators can delete clubs.')
            return redirect('clubs:club_detail', 
                          school_slug=self.kwargs.get('school_slug'),
                          pk=club.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        messages.success(self.request, f'Club "{self.object.name}" deleted successfully!')
        return reverse_lazy('clubs:club_list', kwargs={'school_slug': self.kwargs.get('school_slug')})

@login_required
def join_club(request, school_slug, club_id):
    """Apply to join a club (students only)"""
    if request.user.role != 'student':
        messages.error(request, 'Only students can join clubs.')
        if request.user.role == 'parent':
            return redirect(f"/school/{school_slug}/children-clubs/")
        return redirect('clubs:club_detail', school_slug=school_slug, pk=club_id)
    
    club = get_object_or_404(Club, id=club_id, school__slug=school_slug)
    
    # Check if already a member
    existing_membership = ClubMembership.objects.filter(
        student=request.user,
        club=club
    ).first()
    
    if existing_membership:
        messages.warning(request, 'You have already applied to this club.')
        return redirect('clubs:club_detail', school_slug=school_slug, pk=club_id)
    
    if club.is_full():
        messages.error(request, 'This club has reached its maximum capacity.')
        return redirect('clubs:club_detail', school_slug=school_slug, pk=club_id)
    
    if request.method == 'POST':
        form = ClubMembershipForm(request.POST)
        if form.is_valid():
            membership = form.save(commit=False)
            membership.student = request.user
            membership.club = club
            membership.save()
            
            messages.success(request, f'Your application to join {club.name} has been submitted!')
            return redirect('clubs:club_detail', school_slug=school_slug, pk=club_id)
    else:
        form = ClubMembershipForm()
    
    return render(request, 'clubs/join_club.html', {
        'form': form,
        'club': club,
        'school_slug': school_slug
    })

@login_required
def leave_club(request, school_slug, club_id):
    """Leave a club (students only)"""
    if request.user.role != 'student':
        messages.error(request, 'Only students can leave clubs.')
        if request.user.role == 'parent':
            return redirect(f"/school/{school_slug}/children-clubs/")
        return redirect('clubs:club_detail', school_slug=school_slug, pk=club_id)
    
    club = get_object_or_404(Club, id=club_id, school__slug=school_slug)
    
    try:
        membership = ClubMembership.objects.get(
            student=request.user,
            club=club,
            status='active'
        )
        membership.status = 'inactive'
        membership.save()
        
        messages.success(request, f'You have left {club.name}.')
    except ClubMembership.DoesNotExist:
        messages.error(request, 'You are not an active member of this club.')
    
    return redirect('clubs:club_detail', school_slug=school_slug, pk=club_id)

class ClubActivityListView(LoginRequiredMixin, ListView):
    """List activities for a specific club"""
    model = ClubActivity
    template_name = 'clubs/activity_list.html'
    context_object_name = 'activities'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'parent':
            school_slug = kwargs.get('school_slug')
            messages.info(request, "Parents can only view clubs for their children.")
            return redirect(f"/school/{school_slug}/children-clubs/")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        club_id = self.kwargs.get('club_id')
        club = get_object_or_404(Club, id=club_id, school__slug=self.kwargs.get('school_slug'))
        
        queryset = ClubActivity.objects.filter(club=club)
        
        # Filter by activity type
        activity_type = self.request.GET.get('type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        return queryset.order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug')
        context['club'] = get_object_or_404(Club, id=self.kwargs.get('club_id'))
        context['activity_types'] = ClubActivity.ACTIVITY_TYPES
        context['selected_type'] = self.request.GET.get('type', '')
        return context

class MyClubsView(LoginRequiredMixin, ListView):
    """Student's club memberships"""
    model = ClubMembership
    template_name = 'clubs/my_clubs.html'
    context_object_name = 'memberships'
    paginate_by = 10
    
    def get_queryset(self):
        if self.request.user.role != 'student':
            return ClubMembership.objects.none()
        
        return ClubMembership.objects.filter(
            student=self.request.user
        ).select_related('club').order_by('-application_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug')
        
        # Get upcoming activities for user's clubs
        user_club_ids = [membership.club.id for membership in context['memberships'] 
                        if membership.status == 'active']
        
        if user_club_ids:
            context['upcoming_activities'] = ClubActivity.objects.filter(
                club_id__in=user_club_ids,
                date__gte=timezone.now()
            ).order_by('date')[:10]
        else:
            context['upcoming_activities'] = []
        
        return context

@login_required
def manage_memberships(request, school_slug, club_id):
    """Manage club memberships (admin/teacher/advisor only)"""
    club = get_object_or_404(Club, id=club_id, school__slug=school_slug)
    
    if (request.user.role not in ['admin', 'teacher'] and 
        request.user != club.teacher_advisor):
        messages.error(request, 'You don\'t have permission to manage memberships.')
        if request.user.role == 'parent':
            return redirect(f"/school/{school_slug}/children-clubs/")
        return redirect('clubs:club_detail', school_slug=school_slug, pk=club_id)
    
    memberships = ClubMembership.objects.filter(club=club).select_related('student')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        memberships = memberships.filter(status=status_filter)
    
    # Handle membership approval/rejection
    if request.method == 'POST':
        membership_id = request.POST.get('membership_id')
        action = request.POST.get('action')
        
        try:
            membership = ClubMembership.objects.get(id=membership_id, club=club)
            
            if action == 'approve':
                membership.status = 'active'
                membership.join_date = timezone.now().date()
                membership.save()
                messages.success(request, f'{membership.student.get_full_name()}\'s membership approved!')
            
            elif action == 'reject':
                membership.status = 'rejected'
                membership.save()
                messages.success(request, f'{membership.student.get_full_name()}\'s membership rejected!')
            
        except ClubMembership.DoesNotExist:
            messages.error(request, 'Membership not found.')
        
        return redirect('clubs:manage_memberships', school_slug=school_slug, club_id=club_id)
    
    return render(request, 'clubs/manage_memberships.html', {
        'club': club,
        'memberships': memberships,
        'school_slug': school_slug,
        'status_choices': ClubMembership.STATUS_CHOICES,
        'selected_status': status_filter or ''
    })

@login_required
def club_dashboard(request, school_slug):
    """Dashboard overview for clubs"""
    school = get_object_or_404(School, slug=school_slug)

    if request.user.role == 'parent':
        messages.info(request, "Parents can only view clubs for their children.")
        return redirect(f"/school/{school_slug}/children-clubs/")
    
    context = {
        'school_slug': school_slug,
        'total_clubs': Club.objects.filter(school=school, is_active=True).count(),
        'total_members': ClubMembership.objects.filter(
            club__school=school, 
            status='active'
        ).count(),
        'recent_activities': ClubActivity.objects.filter(
            club__school=school,
            date__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-date')[:10],
        'popular_clubs': Club.objects.filter(
            school=school, 
            is_active=True
        ).annotate(
            members_count=Count('memberships', filter=Q(memberships__status='active'))
        ).order_by('-members_count')[:5],
    }
    
    # Student-specific data
    if request.user.role == 'student':
        context['user_memberships'] = ClubMembership.objects.filter(
            student=request.user,
            status='active'
        ).select_related('club')
        
        context['user_upcoming_activities'] = ClubActivity.objects.filter(
            club__in=[m.club for m in context['user_memberships']],
            date__gte=timezone.now()
        ).order_by('date')[:5]
    
    return render(request, 'clubs/dashboard.html', context)
