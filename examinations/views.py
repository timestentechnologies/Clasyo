from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
import json
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from core.utils import get_current_school

# Check if models exist
try:
    from .models import Exam, Grade, ExamMark, ExamResult, ExamQuestion, ExamSubmission, QuestionAnswer
    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False
    # Create dummy classes to prevent errors
    class Exam:
        pass
    class Grade:
        pass
    class ExamMark:
        pass
    class ExamResult:
        pass
    class ExamQuestion:
        pass
    class ExamSubmission:
        pass
    class QuestionAnswer:
        pass


class ExamListView(LoginRequiredMixin, ListView):
    template_name = 'examinations/exam_list.html'
    context_object_name = 'exams'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_parent:
            messages.info(request, "Parents can only view exams for their children.")
            school_slug = kwargs.get('school_slug')
            return redirect(f"/school/{school_slug}/children-exams/")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        if MODELS_EXIST:
            school = get_current_school(self.request)
            qs = Exam.objects.all()
            if school:
                qs = qs.filter(school=school)
            return qs
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug
        school = get_current_school(self.request)
        context['school'] = school
        
        # Add classes and subjects for the form
        if MODELS_EXIST:
            from academics.models import Class, Subject
            classes_qs = Class.objects.filter(is_active=True)
            subjects_qs = Subject.objects.filter(is_active=True)
            if school:
                classes_qs = classes_qs.filter(school=school)
                subjects_qs = subjects_qs.filter(school=school)
            context['classes'] = classes_qs
            context['subjects'] = subjects_qs
        else:
            context['classes'] = []
            context['subjects'] = []
        
        return context


class ExamDetailView(LoginRequiredMixin, View):
    """Return an exam's details for the edit modal."""
    def get(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})

            if not (getattr(request.user, 'is_school_admin', False) or getattr(request.user, 'is_teacher', False) or request.user.role in ['school_admin', 'teacher']):
                return JsonResponse({'success': False, 'error': 'Not authorized'})

            school = get_current_school(request)
            qs = Exam.objects.all()
            if school:
                qs = qs.filter(school=school)
            exam = qs.select_related('class_assigned', 'subject').prefetch_related('subject_configs__subject').get(pk=exam_id)

            subjects_data = [
                {'subject_id': sc.subject.id, 'name': sc.subject.name, 'total_marks': float(sc.total_marks)}
                for sc in exam.subject_configs.all()
            ]

            return JsonResponse({
                'success': True,
                'exam': {
                    'id': exam.id,
                    'name': exam.name,
                    'exam_type': exam.exam_type,
                    'class_assigned': exam.class_assigned_id,
                    'subject': exam.subject_id,
                    'start_date': exam.start_date.isoformat() if exam.start_date else '',
                    'end_date': exam.end_date.isoformat() if exam.end_date else '',
                    'note': exam.note or '',
                    'is_online': bool(exam.is_online),
                    'duration_minutes': exam.duration_minutes,
                    'attachment_url': exam.attachment.url if getattr(exam, 'attachment', None) else '',
                    'attachment_name': exam.attachment.name.split('/')[-1] if getattr(exam, 'attachment', None) else '',
                    'subjects': subjects_data,
                }
            })
        except Exam.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Exam not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class ExamUpdateView(LoginRequiredMixin, View):
    """Update an exam (used by edit modal)."""
    def post(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})

            if not (getattr(request.user, 'is_school_admin', False) or getattr(request.user, 'is_teacher', False) or request.user.role in ['school_admin', 'teacher']):
                return JsonResponse({'success': False, 'error': 'Not authorized'})

            school = get_current_school(request)
            qs = Exam.objects.all()
            if school:
                qs = qs.filter(school=school)
            exam = qs.get(pk=exam_id)

            from academics.models import Class, Subject

            exam.name = request.POST.get('name', exam.name)
            exam.exam_type = request.POST.get('exam_type', exam.exam_type)
            exam.start_date = request.POST.get('start_date', exam.start_date)
            exam.end_date = request.POST.get('end_date', exam.end_date)
            exam.note = request.POST.get('note', exam.note or '')

            class_id = request.POST.get('class_assigned')
            subject_id = request.POST.get('subject')
            exam.class_assigned = Class.objects.get(pk=class_id) if class_id else None
            exam.subject = Subject.objects.get(pk=subject_id) if subject_id else None

            # Online fields
            is_online = request.POST.get('is_online') == 'true' or request.POST.get('exam_type') == 'online'
            exam.is_online = bool(is_online)
            duration = request.POST.get('duration_minutes')
            exam.duration_minutes = int(duration) if duration else None

            # Attachment updates
            if request.POST.get('clear_attachment') == 'true':
                exam.attachment = None
            attachment = request.FILES.get('attachment')
            if attachment:
                exam.attachment = attachment

            exam.save()

            # Handle multi-subject configuration
            subjects_json = request.POST.get('subjects_json')
            if subjects_json:
                try:
                    subjects_payload = json.loads(subjects_json)
                    with transaction.atomic():
                        exam.subject_configs.all().delete()
                        for item in subjects_payload:
                            exam.subject_configs.create(
                                subject_id=item['subject_id'],
                                total_marks=Decimal(str(item['total_marks']))
                            )
                    # For backward compatibility, if only one subject, also set exam.subject
                    if len(subjects_payload) == 1:
                        exam.subject_id = subjects_payload[0]['subject_id']
                        exam.save()
                except Exception as e:
                    return JsonResponse({'success': False, 'error': f'Failed to save subjects: {e}'})
            else:
                # No multi-subject payload; keep existing single-subject logic if any
                pass

            return JsonResponse({'success': True, 'message': 'Exam updated successfully!'})
        except Exam.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Exam not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class ClassSubjectsView(LoginRequiredMixin, View):
    """Return subjects assigned to a class (for auto-loading in exam modal)."""
    def get(self, request, class_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            if not (getattr(request.user, 'is_school_admin', False) or getattr(request.user, 'is_teacher', False) or request.user.role in ['school_admin', 'teacher']):
                return JsonResponse({'success': False, 'error': 'Not authorized'})
            school = get_current_school(request)
            from academics.models import Class, AssignedSubject
            cls = Class.objects.get(pk=class_id)
            if school and cls.school != school:
                return JsonResponse({'success': False, 'error': 'Class not found'})
            # AssignedSubject may have section; include all for the class but deduplicate by subject
            assigned = AssignedSubject.objects.filter(class_name=cls, is_active=True).select_related('subject').order_by('subject__name')
            seen_ids = set()
            subjects = []
            for a in assigned:
                if a.subject.id not in seen_ids:
                    seen_ids.add(a.subject.id)
                    subjects.append({'id': a.subject.id, 'name': a.subject.name})
            return JsonResponse({'success': True, 'subjects': subjects})
        except Class.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Class not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class StudentExamView(LoginRequiredMixin, DetailView):
    """View for students to view exam details (including offline attachments)."""
    model = Exam
    template_name = 'examinations/student_exam_view.html'
    context_object_name = 'exam'
    pk_url_kwarg = 'exam_id'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_parent:
            messages.info(request, "Parents can only view exams for their children.")
            school_slug = kwargs.get('school_slug')
            return redirect(f"/school/{school_slug}/children-exams/")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if not MODELS_EXIST:
            return Exam.objects.none()
        school = get_current_school(self.request)
        qs = Exam.objects.all()
        if school:
            qs = qs.filter(school=school)
        # If student, restrict to their current class where possible
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            if getattr(student, 'current_class', None):
                from django.db.models import Q
                qs = qs.filter(Q(class_assigned=student.current_class) | Q(class_assigned__isnull=True))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')

        exam = self.object
        if MODELS_EXIST and exam.is_online:
            context['questions'] = exam.questions.all().order_by('order')

        # If student, show their overall result if it exists
        if MODELS_EXIST and hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            try:
                context['user_result'] = ExamResult.objects.get(exam=exam, student=student)
            except ExamResult.DoesNotExist:
                context['user_result'] = None

        return context


class ExamCreateView(LoginRequiredMixin, CreateView):
    model = Exam
    
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            is_online = request.POST.get('is_online') == 'true'
            duration = request.POST.get('duration_minutes')
            class_id = request.POST.get('class_assigned')
            subject_id = request.POST.get('subject')
            attachment = request.FILES.get('attachment')
            
            from academics.models import Class, Subject
            
            exam = Exam.objects.create(
                school=school,
                name=request.POST.get('name'),
                exam_type=request.POST.get('exam_type'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                note=request.POST.get('note', ''),
                is_published=False,
                is_online=is_online,
                duration_minutes=int(duration) if duration else None,
                class_assigned=Class.objects.get(pk=class_id) if class_id else None,
                subject=Subject.objects.get(pk=subject_id) if subject_id else None,
                created_by=request.user,
                attachment=attachment,
            )
            
            # Handle multi-subject configuration
            subjects_json = request.POST.get('subjects_json')
            if subjects_json:
                try:
                    subjects_payload = json.loads(subjects_json)
                    with transaction.atomic():
                        for item in subjects_payload:
                            exam.subject_configs.create(
                                subject_id=item['subject_id'],
                                total_marks=Decimal(str(item['total_marks']))
                            )
                    # For backward compatibility, if only one subject, also set exam.subject
                    if len(subjects_payload) == 1:
                        exam.subject_id = subjects_payload[0]['subject_id']
                        exam.save()
                except Exception as e:
                    return JsonResponse({'success': False, 'error': f'Failed to save subjects: {e}'})
            else:
                # No multi-subject payload; keep existing single-subject logic if any
                pass

            # Send notifications to students, teachers, and admins
            from core.notifications import NotificationService
            return JsonResponse({'success': True, 'exam_id': exam.id})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class ExamDeleteView(LoginRequiredMixin, DeleteView):
    model = Exam
    
    def post(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class GradeListView(LoginRequiredMixin, ListView):
    template_name = 'examinations/grade_list.html'
    context_object_name = 'grades'
    
    def get_queryset(self):
        if MODELS_EXIST:
            school = get_current_school(self.request)
            qs = Grade.objects.all()
            if school:
                qs = qs.filter(school=school)
            return qs
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class GradeCreateView(LoginRequiredMixin, CreateView):
    model = Grade
    
    def post(self, request, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            school = get_current_school(request)
            Grade.objects.create(
                school=school,
                name=request.POST.get('name'),
                min_percentage=float(request.POST.get('min_percentage', 0)),
                max_percentage=float(request.POST.get('max_percentage', 100)),
                point=float(request.POST.get('point', 0)),
                note=request.POST.get('note', '')
            )
            return JsonResponse({'success': True, 'message': 'Grade created successfully!'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class GradeDeleteView(LoginRequiredMixin, View):
    """Delete a grade"""
    def post(self, request, pk, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})

            school = get_current_school(request)
            qs = Grade.objects.all()
            if school:
                qs = qs.filter(school=school)
            grade = qs.get(pk=pk)
            grade.delete()
            return JsonResponse({'success': True, 'message': 'Grade deleted successfully!'})
        except Grade.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Grade not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class GradeUpdateView(LoginRequiredMixin, View):
    """Update a grade"""
    def post(self, request, pk, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})

            school = get_current_school(request)
            qs = Grade.objects.all()
            if school:
                qs = qs.filter(school=school)
            grade = qs.get(pk=pk)
            grade.name = request.POST.get('name', grade.name)
            grade.min_percentage = float(request.POST.get('min_percentage', grade.min_percentage))
            grade.max_percentage = float(request.POST.get('max_percentage', grade.max_percentage))
            grade.point = float(request.POST.get('point', grade.point))
            grade.note = request.POST.get('note', grade.note)
            grade.save()
            
            return JsonResponse({'success': True, 'message': 'Grade updated successfully!'})
        except Grade.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Grade not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class QuestionListView(LoginRequiredMixin, View):
    """List questions for an exam"""
    def get(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            questions = ExamQuestion.objects.filter(exam_id=exam_id).order_by('order', 'id')
            data = [{
                'id': q.id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'points': float(q.points),
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_answer': q.correct_answer,
            } for q in questions]
            
            return JsonResponse({'success': True, 'questions': data})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class QuestionCreateView(LoginRequiredMixin, View):
    """Create a question for an exam"""
    def post(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            school = get_current_school(request)
            exam_qs = Exam.objects.all()
            if school:
                exam_qs = exam_qs.filter(school=school)
            exam = exam_qs.get(pk=exam_id)
            
            # Get the highest order number
            max_order = ExamQuestion.objects.filter(exam=exam).aggregate(
                models.Max('order')
            )['order__max'] or 0
            
            ExamQuestion.objects.create(
                exam=exam,
                question_text=request.POST.get('question_text'),
                question_type=request.POST.get('question_type', 'multiple_choice'),
                points=request.POST.get('points', 1),
                order=max_order + 1,
                option_a=request.POST.get('option_a', ''),
                option_b=request.POST.get('option_b', ''),
                option_c=request.POST.get('option_c', ''),
                option_d=request.POST.get('option_d', ''),
                correct_answer=request.POST.get('correct_answer', '')
            )
            return JsonResponse({'success': True, 'message': 'Question added successfully!'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class QuestionDeleteView(LoginRequiredMixin, View):
    """Delete a question"""
    def post(self, request, pk, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            question = ExamQuestion.objects.get(pk=pk)
            question.delete()
            return JsonResponse({'success': True, 'message': 'Question deleted successfully!'})
        except ExamQuestion.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Question not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class MarksEntryView(LoginRequiredMixin, TemplateView):
    template_name = 'examinations/marks_entry.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if MODELS_EXIST:
            from academics.models import Class, Subject
            school = get_current_school(self.request)
            exams_qs = Exam.objects.all().select_related('class_assigned', 'subject')
            classes_qs = Class.objects.filter(is_active=True)
            subjects_qs = Subject.objects.filter(is_active=True)
            if school:
                exams_qs = exams_qs.filter(school=school)
                classes_qs = classes_qs.filter(school=school)
                subjects_qs = subjects_qs.filter(school=school)
            context['exams'] = exams_qs
            context['classes'] = classes_qs
            context['subjects'] = subjects_qs
        
        return context


class MarksSubjectsView(LoginRequiredMixin, View):
    """Return exam subjects with totals for the marks entry grid."""
    def get(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            school = get_current_school(request)
            exam_qs = Exam.objects.all()
            if school:
                exam_qs = exam_qs.filter(school=school)
            exam = exam_qs.prefetch_related('subject_configs__subject').get(pk=exam_id)
            subjects_data = [
                {'subject_id': sc.subject.id, 'name': sc.subject.name, 'total_marks': float(sc.total_marks)}
                for sc in exam.subject_configs.all()
            ]
            return JsonResponse({'success': True, 'subjects': subjects_data})
        except Exam.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Exam not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class GetStudentsForMarksEntryView(LoginRequiredMixin, View):
    """AJAX view to get students for marks entry based on exam"""
    def get(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            from students.models import Student
            
            school = get_current_school(request)
            exam_qs = Exam.objects.all()
            if school:
                exam_qs = exam_qs.filter(school=school)
            exam = exam_qs.prefetch_related('subject_configs__subject').get(pk=exam_id)
            
            # Get all students in the exam's class
            students = Student.objects.filter(
                current_class=exam.class_assigned,
                is_active=True
            ).order_by('first_name', 'last_name')
            
            # Fetch existing marks per student per subject
            from django.db.models import Q
            student_ids = list(students.values_list('id', flat=True))
            subject_ids = list(exam.subject_configs.values_list('subject_id', flat=True))
            existing_marks = {}
            if student_ids and subject_ids:
                marks_qs = ExamMark.objects.filter(
                    Q(exam=exam) & Q(student_id__in=student_ids) & Q(subject_id__in=subject_ids)
                ).select_related('subject')
                for m in marks_qs:
                    existing_marks.setdefault(m.student_id, {})[m.subject_id] = {
                        'marks_obtained': float(m.marks_obtained),
                        'remarks': m.remarks
                    }
            
            students_data = []
            for student in students:
                students_data.append({
                    'id': student.id,
                    'name': f"{student.first_name} {student.last_name}",
                    'admission_number': student.admission_number,
                    'subject_marks': existing_marks.get(student.id, {}),
                    'remarks': ''  # fallback; grid uses per-subject remarks or leave empty
                })
            
            return JsonResponse({
                'success': True,
                'students': students_data,
                'exam_name': exam.name,
                'subject_name': exam.subject.name if exam.subject else 'General'
            })
        except Exam.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Exam not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class SaveMarksGridView(LoginRequiredMixin, View):
    """Save per-subject marks for a grid of students."""
    def post(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            import json
            from decimal import Decimal, InvalidOperation
            from students.models import Student

            school = get_current_school(request)
            exam_qs = Exam.objects.all()
            if school:
                exam_qs = exam_qs.filter(school=school)
            exam = exam_qs.prefetch_related('subject_configs__subject').get(pk=exam_id)

            data = json.loads(request.POST.get('marks', '[]'))
            if not isinstance(data, list):
                return JsonResponse({'success': False, 'error': 'Invalid marks data'})

            # Prepare a mapping of subject_id -> total_marks for validation
            subject_totals = {sc.subject_id: sc.total_marks for sc in exam.subject_configs.all()}

            with transaction.atomic():
                for entry in data:
                    student_id = entry.get('student_id')
                    subject_marks = entry.get('subject_marks', {})
                    remarks = entry.get('remarks', '')

                    # Validate student
                    student = Student.objects.get(pk=student_id, current_class=exam.class_assigned)

                    # Save per-subject marks
                    for subj_id, marks_obtained in subject_marks.items():
                        subj_id = int(subj_id)
                        # Validate against total marks
                        total_marks = subject_totals.get(subj_id)
                        if total_marks is None:
                            return JsonResponse({'success': False, 'error': f'Subject {subj_id} not part of exam'})
                        if marks_obtained is not None:
                            try:
                                marks_val = Decimal(str(marks_obtained))
                                if marks_val < 0 or marks_val > total_marks:
                                    return JsonResponse({'success': False, 'error': f'Marks out of range for subject {subj_id}'})
                            except InvalidOperation:
                                return JsonResponse({'success': False, 'error': f'Invalid marks value for subject {subj_id}'})

                        # Create or update ExamMark
                        ExamMark.objects.update_or_create(
                            exam=exam,
                            student=student,
                            subject_id=subj_id,
                            defaults={
                                'marks_obtained': marks_obtained if marks_obtained is not None else Decimal('0'),
                                'remarks': remarks
                            }
                        )
            return JsonResponse({'success': True, 'message': 'Marks saved successfully!'})
        except Exam.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Exam not found'})
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found in class'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class SaveMarksEntryView(LoginRequiredMixin, View):
    """AJAX view to save marks for multiple students"""
    def post(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            import json
            from decimal import Decimal
            from students.models import Student
            
            school = get_current_school(request)
            exam_qs = Exam.objects.all()
            if school:
                exam_qs = exam_qs.filter(school=school)
            exam = exam_qs.get(pk=exam_id)
            marks_data = json.loads(request.POST.get('marks', '[]'))
            total_marks = Decimal(request.POST.get('total_marks', '100'))
            
            saved_count = 0
            for mark_entry in marks_data:
                student = Student.objects.get(
                    pk=mark_entry['student_id'],
                    current_class=exam.class_assigned,
                )
                marks_obtained = Decimal(str(mark_entry.get('marks_obtained', 0)))
                
                # Create or update exam mark
                mark, created = ExamMark.objects.update_or_create(
                    exam=exam,
                    student=student,
                    subject=exam.subject if exam.subject else None,
                    defaults={
                        'marks_obtained': marks_obtained,
                        'total_marks': total_marks,
                        'remarks': mark_entry.get('remarks', '')
                    }
                )
                
                # Assign grade based on percentage
                percentage = (marks_obtained / total_marks) * 100 if total_marks > 0 else 0
                school = get_current_school(request)
                grade_qs = Grade.objects.filter(
                    min_percentage__lte=percentage,
                    max_percentage__gte=percentage
                )
                if school:
                    grade_qs = grade_qs.filter(school=school)
                grade = grade_qs.first()
                mark.grade = grade
                mark.save()

                # Ensure the student sees results in the unified results UI.
                # Manual marks entry does not create submissions, so we mirror into ExamSubmission.
                percentage = (marks_obtained / total_marks) * Decimal('100') if total_marks > 0 else Decimal('0')
                submission_defaults = {
                    'status': 'graded',
                    'total_points': total_marks,
                    'points_obtained': marks_obtained,
                    'percentage': percentage,
                    'teacher_remarks': mark_entry.get('remarks', '') or '',
                    'graded_by': request.user,
                    'graded_at': timezone.now(),
                    'grade': grade,
                }
                ExamSubmission.objects.update_or_create(
                    exam=exam,
                    student=student,
                    defaults=submission_defaults,
                )
                
                saved_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Marks saved for {saved_count} students successfully!'
            })
        except Exam.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Exam not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class ResultView(LoginRequiredMixin, TemplateView):
    template_name = 'examinations/results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class StudentExamTakeView(LoginRequiredMixin, DetailView):
    """View for students to take an exam"""
    model = Exam
    template_name = 'examinations/student_take_exam.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_parent:
            messages.info(request, "Parents can only view exams for their children.")
            school_slug = kwargs.get('school_slug')
            return redirect(f"/school/{school_slug}/children-exams/")
        return super().dispatch(request, *args, **kwargs)
    context_object_name = 'exam'
    pk_url_kwarg = 'exam_id'

    def get_queryset(self):
        if not MODELS_EXIST:
            return Exam.objects.none()
        school = get_current_school(self.request)
        qs = Exam.objects.all()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if MODELS_EXIST and hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            exam = self.object
            
            # Get or create submission
            submission, created = ExamSubmission.objects.get_or_create(
                exam=exam,
                student=student,
                defaults={'status': 'not_started'}
            )
            context['submission'] = submission
            
            # Get questions
            context['questions'] = exam.questions.all().order_by('order')
            
            # Get existing answers
            answers_dict = {}
            for answer in submission.answers.all():
                answers_dict[answer.question.id] = answer
            context['answers_dict'] = answers_dict
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class StudentSubmitAnswerView(LoginRequiredMixin, View):
    """AJAX view for students to submit answers"""
    def post(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST or not hasattr(request.user, 'student_profile'):
                return JsonResponse({'success': False, 'error': 'Not authorized'})
            
            from django.utils import timezone
            student = request.user.student_profile
            school = get_current_school(request)
            exam_qs = Exam.objects.all()
            if school:
                exam_qs = exam_qs.filter(school=school)
            exam = exam_qs.get(pk=exam_id)
            question_id = request.POST.get('question_id')
            question = ExamQuestion.objects.get(pk=question_id, exam=exam)
            
            # Get or create submission
            submission, created = ExamSubmission.objects.get_or_create(
                exam=exam,
                student=student,
                defaults={'status': 'in_progress', 'started_at': timezone.now()}
            )
            
            # Update status to in_progress if it was not_started
            if submission.status == 'not_started':
                submission.status = 'in_progress'
                submission.started_at = timezone.now()
                submission.save()
            
            # Create or update answer
            answer, created = QuestionAnswer.objects.get_or_create(
                submission=submission,
                question=question
            )
            
            if question.question_type in ['multiple_choice', 'true_false']:
                answer.selected_option = request.POST.get('answer', '')
            else:
                answer.answer_text = request.POST.get('answer', '')
            
            answer.save()
            
            # Auto-grade if multiple choice or true/false
            answer.auto_grade()
            
            return JsonResponse({'success': True, 'message': 'Answer saved'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class StudentSubmitExamView(LoginRequiredMixin, View):
    """View for students to submit the complete exam"""
    def post(self, request, exam_id, *args, **kwargs):
        try:
            if not MODELS_EXIST or not hasattr(request.user, 'student_profile'):
                return JsonResponse({'success': False, 'error': 'Not authorized'})
            
            from django.utils import timezone
            from decimal import Decimal
            
            student = request.user.student_profile
            school = get_current_school(request)
            exam_qs = Exam.objects.all()
            if school:
                exam_qs = exam_qs.filter(school=school)
            exam = exam_qs.get(pk=exam_id)
            
            submission = ExamSubmission.objects.get(exam=exam, student=student)
            submission.status = 'submitted'
            submission.submitted_at = timezone.now()
            
            # Calculate time taken
            if submission.started_at:
                time_diff = submission.submitted_at - submission.started_at
                submission.time_taken_minutes = int(time_diff.total_seconds() / 60)
            
            # Calculate total points and auto-graded points
            total_points = Decimal('0')
            points_obtained = Decimal('0')
            
            for question in exam.questions.all():
                total_points += question.points
                
                try:
                    answer = QuestionAnswer.objects.get(submission=submission, question=question)
                    if answer.points_awarded is not None:
                        points_obtained += answer.points_awarded
                except QuestionAnswer.DoesNotExist:
                    pass
            
            submission.total_points = total_points
            submission.points_obtained = points_obtained
            
            if total_points > 0:
                submission.percentage = (points_obtained / total_points) * 100
            
            # Check if needs manual grading
            has_essay = exam.questions.filter(question_type__in=['essay', 'short_answer']).exists()
            if not has_essay:
                submission.status = 'graded'
            
            submission.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Exam submitted successfully!',
                'needs_grading': has_essay
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class TeacherGradingListView(LoginRequiredMixin, ListView):
    """View for teachers to see all submissions needing grading"""
    template_name = 'examinations/teacher_grading_list.html'
    context_object_name = 'submissions'
    
    def get_queryset(self):
        if not MODELS_EXIST:
            return []
        
        # Show submitted exams that need grading
        school = get_current_school(self.request)
        qs = ExamSubmission.objects.filter(
            status__in=['submitted', 'graded']
        )
        if school:
            qs = qs.filter(exam__school=school)
        return qs.select_related('exam', 'student', 'student__user').order_by('-submitted_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class TeacherGradeSubmissionView(LoginRequiredMixin, DetailView):
    """View for teachers to grade a specific submission"""
    model = ExamSubmission
    template_name = 'examinations/teacher_grade_submission.html'
    context_object_name = 'submission'
    pk_url_kwarg = 'submission_id'

    def get_queryset(self):
        if not MODELS_EXIST:
            return ExamSubmission.objects.none()
        school = get_current_school(self.request)
        qs = ExamSubmission.objects.all()
        if school:
            qs = qs.filter(exam__school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        if MODELS_EXIST:
            submission = self.object
            context['answers'] = submission.answers.all().select_related('question').order_by('question__order')
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class TeacherSaveGradingView(LoginRequiredMixin, View):
    """AJAX view for teachers to save grading"""
    def post(self, request, submission_id, *args, **kwargs):
        try:
            if not MODELS_EXIST:
                return JsonResponse({'success': False, 'error': 'Models not available'})
            
            from django.utils import timezone
            from decimal import Decimal
            import json
            
            school = get_current_school(request)
            submission_qs = ExamSubmission.objects.all()
            if school:
                submission_qs = submission_qs.filter(exam__school=school)
            submission = submission_qs.get(pk=submission_id)
            
            # Update answer grades
            answers_data = json.loads(request.POST.get('answers', '[]'))
            for answer_data in answers_data:
                answer = QuestionAnswer.objects.get(pk=answer_data['answer_id'], submission=submission)
                answer.points_awarded = Decimal(str(answer_data.get('points', 0)))
                answer.teacher_feedback = answer_data.get('feedback', '')
                
                # For essay/short answer questions
                if answer.question.question_type in ['essay', 'short_answer']:
                    answer.is_correct = answer.points_awarded >= (answer.question.points * Decimal('0.5'))
                
                answer.save()
            
            # Recalculate total
            total_points = Decimal('0')
            points_obtained = Decimal('0')
            
            for answer in submission.answers.all():
                total_points += answer.question.points
                points_obtained += answer.points_awarded
            
            submission.total_points = total_points
            submission.points_obtained = points_obtained
            
            if total_points > 0:
                submission.percentage = (points_obtained / total_points) * 100
            
            # Update status and metadata
            submission.status = 'graded'
            submission.teacher_remarks = request.POST.get('remarks', '')
            submission.graded_by = request.user
            submission.graded_at = timezone.now()
            
            # Assign grade based on percentage
            if MODELS_EXIST:
                school = get_current_school(request)
                grade_qs = Grade.objects.filter(
                    min_percentage__lte=submission.percentage,
                    max_percentage__gte=submission.percentage
                )
                if school:
                    grade_qs = grade_qs.filter(school=school)
                grade = grade_qs.first()
                submission.grade = grade
            
            submission.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Grading saved successfully!',
                'percentage': float(submission.percentage)
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


class StudentResultsView(LoginRequiredMixin, ListView):
    """View for students to see their exam results"""
    template_name = 'examinations/student_results.html'
    context_object_name = 'submissions'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_parent:
            messages.info(request, "Parents can only view results for their children.")
            school_slug = kwargs.get('school_slug')
            return redirect(f"/school/{school_slug}/children-results/")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        if not MODELS_EXIST or not hasattr(self.request.user, 'student_profile'):
            return []
        
        student = self.request.user.student_profile
        school = get_current_school(self.request)
        qs = ExamSubmission.objects.filter(
            student=student,
            status='graded'
        )
        if school:
            qs = qs.filter(exam__school=school)
        return qs.select_related('exam', 'grade').order_by('-submitted_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Fetch per-subject marks and compute totals for each submission
        if MODELS_EXIST and context['submissions']:
            student = self.request.user.student_profile
            for submission in context['submissions']:
                marks = ExamMark.objects.filter(
                    exam=submission.exam,
                    student=student
                ).select_related('subject', 'grade').order_by('subject__name')
                submission.subject_marks = marks
                # Compute totals using Python
                submission.total_obtained = sum(m.marks_obtained for m in marks)
                submission.total_possible = sum(m.total_marks for m in marks)
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class StudentSubmitCorrectionView(LoginRequiredMixin, View):
    """AJAX view for students to submit corrections"""
    def post(self, request, answer_id, *args, **kwargs):
        try:
            if not MODELS_EXIST or not hasattr(request.user, 'student_profile'):
                return JsonResponse({'success': False, 'error': 'Not authorized'})
            
            from django.utils import timezone
            
            student = request.user.student_profile
            answer = QuestionAnswer.objects.get(pk=answer_id, submission__student=student)
            
            answer.correction_text = request.POST.get('correction', '')
            answer.correction_submitted_at = timezone.now()
            answer.save()
            
            return JsonResponse({'success': True, 'message': 'Correction submitted!'})
        except QuestionAnswer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Answer not found'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})
