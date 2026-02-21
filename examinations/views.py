from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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


class ExamCreateView(LoginRequiredMixin, CreateView):
    model = Exam
    
    def post(self, request, *args, **kwargs):
        try:
            school = get_current_school(request)
            is_online = request.POST.get('is_online') == 'true'
            duration = request.POST.get('duration_minutes')
            class_id = request.POST.get('class_assigned')
            subject_id = request.POST.get('subject')
            
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
                created_by=request.user
            )
            
            # Send notifications to students, teachers, and admins
            from core.notifications import NotificationService
            try:
                if school:
                    NotificationService.notify_exam_created(exam, request.user, school)
            except Exception as e:
                print(f"Error sending exam notifications: {e}")
            
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
            exam = exam_qs.get(pk=exam_id)
            
            # Get all students in the exam's class
            students = Student.objects.filter(
                current_class=exam.class_assigned,
                is_active=True
            ).order_by('first_name', 'last_name')
            
            students_data = []
            for student in students:
                # Check if marks already exist
                try:
                    mark = ExamMark.objects.get(
                        exam=exam,
                        student=student,
                        subject=exam.subject if exam.subject else None
                    )
                    marks_obtained = float(mark.marks_obtained)
                    remarks = mark.remarks
                except ExamMark.DoesNotExist:
                    marks_obtained = None
                    remarks = ''
                
                students_data.append({
                    'id': student.id,
                    'name': f"{student.first_name} {student.last_name}",
                    'admission_number': student.admission_number,
                    'marks_obtained': marks_obtained,
                    'remarks': remarks
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
        return context


class StudentResultDetailView(LoginRequiredMixin, DetailView):
    """View for students to see detailed results and submit corrections"""
    model = ExamSubmission
    template_name = 'examinations/student_result_detail.html'
    context_object_name = 'submission'
    pk_url_kwarg = 'submission_id'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_parent:
            messages.info(request, "Parents can only view results for their children.")
            school_slug = kwargs.get('school_slug')
            return redirect(f"/school/{school_slug}/children-results/")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        if not MODELS_EXIST or not hasattr(self.request.user, 'student_profile'):
            return ExamSubmission.objects.none()
        
        student = self.request.user.student_profile
        school = get_current_school(self.request)
        qs = ExamSubmission.objects.filter(student=student, status='graded')
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
