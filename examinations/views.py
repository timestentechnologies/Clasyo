from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Check if models exist
try:
    from .models import Exam, Grade, ExamMark, ExamResult, ExamQuestion
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


class ExamListView(LoginRequiredMixin, ListView):
    template_name = 'examinations/exam_list.html'
    context_object_name = 'exams'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return Exam.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class ExamCreateView(LoginRequiredMixin, CreateView):
    model = Exam
    
    def post(self, request, *args, **kwargs):
        try:
            is_online = request.POST.get('is_online') == 'true'
            duration = request.POST.get('duration_minutes')
            
            exam = Exam.objects.create(
                name=request.POST.get('name'),
                exam_type=request.POST.get('exam_type'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                note=request.POST.get('note', ''),
                is_published=False,
                is_online=is_online,
                duration_minutes=int(duration) if duration else None
            )
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
            return Grade.objects.all()
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
            
            Grade.objects.create(
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
            
            grade = Grade.objects.get(pk=pk)
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
            
            grade = Grade.objects.get(pk=pk)
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
            
            exam = Exam.objects.get(pk=exam_id)
            
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


class MarksEntryView(LoginRequiredMixin, ListView):
    template_name = 'examinations/marks_entry.html'
    context_object_name = 'marks'
    
    def get_queryset(self):
        if MODELS_EXIST:
            return ExamMark.objects.all()
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        if MODELS_EXIST:
            context['exams'] = Exam.objects.all()
        return context


class ResultView(LoginRequiredMixin, TemplateView):
    template_name = 'examinations/results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
