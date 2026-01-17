from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Q
from .models import Student


class StudentAutocompleteView(LoginRequiredMixin, View):
    """View for student autocomplete search"""
    
    def get(self, request, *args, **kwargs):
        school_slug = self.kwargs.get('school_slug')
        query = request.GET.get('q', '').strip()
        
        if not query:
            return JsonResponse({'results': []})
            
        from tenants.models import School
        school = School.objects.filter(slug=school_slug, is_active=True).first() if school_slug else None

        # Search in admission number, first name, last name, or email
        students = Student.objects.filter(
            Q(admission_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query),
            user__is_active=True
        )
        if school:
            students = students.filter(
                Q(current_class__school=school) | Q(user__school=school)
            ).distinct()
        students = students.select_related('user')[:10]  # Limit to 10 results
        
        results = [{
            'id': student.user.id,
            'text': f"{student.user.get_full_name()} ({student.admission_number or 'No ID'})",
            'name': student.user.get_full_name(),
            'admission_number': student.admission_number or '',
            'email': student.user.email
        } for student in students]
        
        return JsonResponse({'results': results})
