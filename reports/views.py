from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import json
from tenants.models import School
from students.models import Student
from accounts.models import User
from academics.models import Class, Section

# Try to import optional libraries
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ReportsIndexView(LoginRequiredMixin, TemplateView):
    """Reports dashboard"""
    template_name = 'reports/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Get school
        school_slug = self.kwargs.get('school_slug')
        try:
            school = School.objects.get(slug=school_slug)
            context['school'] = school
            
            # Quick stats
            context['total_students'] = Student.objects.filter(school=school, is_active=True).count()
            context['total_teachers'] = User.objects.filter(school=school, role='teacher', is_active=True).count()
            context['total_classes'] = Class.objects.filter(school=school, is_active=True).count()
        except School.DoesNotExist:
            pass
        
        return context


class StudentEnrollmentReportView(LoginRequiredMixin, TemplateView):
    """Student enrollment report"""
    template_name = 'reports/student_enrollment.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug', '')
        context['school_slug'] = school_slug
        
        try:
            school = School.objects.get(slug=school_slug)
            context['school'] = school
            
            # Get enrollment by class
            classes = Class.objects.filter(school=school, is_active=True)
            enrollment_data = []
            
            for cls in classes:
                total = Student.objects.filter(current_class=cls, is_active=True).count()
                male = Student.objects.filter(current_class=cls, is_active=True, gender='male').count()
                female = Student.objects.filter(current_class=cls, is_active=True, gender='female').count()
                
                enrollment_data.append({
                    'class': cls,
                    'total': total,
                    'male': male,
                    'female': female
                })
            
            context['enrollment_data'] = enrollment_data
            context['total_students'] = sum(d['total'] for d in enrollment_data)
            context['total_male'] = sum(d['male'] for d in enrollment_data)
            context['total_female'] = sum(d['female'] for d in enrollment_data)
            
        except School.DoesNotExist:
            context['enrollment_data'] = []
        
        return context


class ExportStudentEnrollmentView(LoginRequiredMixin, View):
    """Export student enrollment report"""
    
    def get(self, request, school_slug, format='csv'):
        school = get_object_or_404(School, slug=school_slug)
        
        # Get data
        classes = Class.objects.filter(school=school, is_active=True)
        data = []
        
        for cls in classes:
            total = Student.objects.filter(current_class=cls, is_active=True).count()
            male = Student.objects.filter(current_class=cls, is_active=True, gender='male').count()
            female = Student.objects.filter(current_class=cls, is_active=True, gender='female').count()
            
            data.append({
                'class': cls.name,
                'total': total,
                'male': male,
                'female': female
            })
        
        if format == 'csv':
            return self.export_csv(data, school)
        elif format == 'excel' and EXCEL_AVAILABLE:
            return self.export_excel(data, school)
        elif format == 'pdf' and PDF_AVAILABLE:
            return self.export_pdf(data, school)
        else:
            return HttpResponse('Format not supported', status=400)
    
    def export_csv(self, data, school):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="enrollment_report_{school.slug}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student Enrollment Report', school.name])
        writer.writerow([])
        writer.writerow(['Class', 'Total Students', 'Male', 'Female'])
        
        for row in data:
            writer.writerow([row['class'], row['total'], row['male'], row['female']])
        
        writer.writerow([])
        writer.writerow(['Total', sum(d['total'] for d in data), sum(d['male'] for d in data), sum(d['female'] for d in data)])
        
        return response
    
    def export_excel(self, data, school):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Enrollment Report'
        
        # Header
        ws['A1'] = 'Student Enrollment Report'
        ws['A1'].font = Font(bold=True, size=14)
        ws['A2'] = school.name
        ws['A2'].font = Font(size=12)
        
        # Column headers
        headers = ['Class', 'Total Students', 'Male', 'Female']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        
        # Data
        for row_idx, row_data in enumerate(data, 5):
            ws.cell(row=row_idx, column=1, value=row_data['class'])
            ws.cell(row=row_idx, column=2, value=row_data['total'])
            ws.cell(row=row_idx, column=3, value=row_data['male'])
            ws.cell(row=row_idx, column=4, value=row_data['female'])
        
        # Total
        total_row = len(data) + 6
        ws.cell(row=total_row, column=1, value='Total').font = Font(bold=True)
        ws.cell(row=total_row, column=2, value=sum(d['total'] for d in data)).font = Font(bold=True)
        ws.cell(row=total_row, column=3, value=sum(d['male'] for d in data)).font = Font(bold=True)
        ws.cell(row=total_row, column=4, value=sum(d['female'] for d in data)).font = Font(bold=True)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="enrollment_report_{school.slug}.xlsx"'
        wb.save(response)
        
        return response
    
    def export_pdf(self, data, school):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="enrollment_report_{school.slug}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f'<b>Student Enrollment Report</b><br/>{school.name}', styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Table data
        table_data = [['Class', 'Total Students', 'Male', 'Female']]
        for row in data:
            table_data.append([row['class'], str(row['total']), str(row['male']), str(row['female'])])
        
        table_data.append(['Total', str(sum(d['total'] for d in data)), 
                          str(sum(d['male'] for d in data)), 
                          str(sum(d['female'] for d in data))])
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.beige),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        return response
