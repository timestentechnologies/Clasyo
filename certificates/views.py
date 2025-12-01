import os
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import gettext as _
from django.template.loader import get_template
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import json
import uuid
from datetime import date, timedelta

from .models import CertificateType, Certificate, IDCard, IDCardTemplate, CertificateVerification
from .forms import (
    CertificateTypeForm, CertificateForm, CertificateVerifyForm,
    IDCardTemplateForm, IDCardForm, BulkIDCardForm
)
from students.models import Student
from academics.models import Class
from tenants.models import School


# Certificate Type Views
class CertificateTypeListView(LoginRequiredMixin, ListView):
    model = CertificateType
    template_name = 'certificates/certificate_type_list.html'
    context_object_name = 'certificate_types'
    
    def get_queryset(self):
        return CertificateType.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class CertificateTypeCreateView(LoginRequiredMixin, CreateView):
    model = CertificateType
    form_class = CertificateTypeForm
    template_name = 'certificates/certificate_type_form.html'
    
    def get_success_url(self):
        return reverse('certificates:certificate_type_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create Certificate Type')
        return context
    
    def form_valid(self, form):
        # Associate with school
        school_slug = self.kwargs.get('school_slug')
        try:
            school = School.objects.get(slug=school_slug)
            form.instance.school = school
        except School.DoesNotExist:
            pass
        
        messages.success(self.request, _('Certificate type created successfully'))
        return super().form_valid(form)


class CertificateTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = CertificateType
    form_class = CertificateTypeForm
    template_name = 'certificates/certificate_type_form.html'
    
    def get_success_url(self):
        return reverse('certificates:certificate_type_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Certificate Type')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Certificate type updated successfully'))
        return super().form_valid(form)


class CertificateTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = CertificateType
    template_name = 'certificates/confirm_delete.html'
    
    def get_success_url(self):
        return reverse('certificates:certificate_type_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Certificate Type')
        context['message'] = _('Are you sure you want to delete this certificate type?')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Certificate type deleted successfully'))
        return super().form_valid(form)


# Certificate Views
class CertificateListView(LoginRequiredMixin, ListView):
    model = Certificate
    template_name = 'certificates/certificate_list.html'
    context_object_name = 'certificates'
    
    def get_queryset(self):
        return Certificate.objects.filter(is_active=True).select_related('student', 'certificate_type')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class CertificateCreateView(LoginRequiredMixin, CreateView):
    model = Certificate
    form_class = CertificateForm
    template_name = 'certificates/certificate_form.html'
    
    def get_success_url(self):
        return reverse('certificates:list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Issue Certificate')
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the school to the form
        school_slug = self.kwargs.get('school_slug')
        if school_slug:
            from tenants.models import School
            try:
                kwargs['school'] = School.objects.get(slug=school_slug)
            except School.DoesNotExist:
                pass
        return kwargs
        
    def form_valid(self, form):
        # Set the creator
        form.instance.created_by = self.request.user
        
        # Set the school if not already set
        if not hasattr(form.instance, 'school') or not form.instance.school:
            school_slug = self.kwargs.get('school_slug')
            if school_slug:
                from tenants.models import School
                try:
                    form.instance.school = School.objects.get(slug=school_slug)
                except School.DoesNotExist:
                    pass
        
        # Create certificate
        response = super().form_valid(form)
        
        # Generate certificate file (this would typically be implemented with a PDF generation library)
        # For now, just a placeholder
        
        messages.success(self.request, _('Certificate issued successfully'))
        return response


class CertificateDetailView(LoginRequiredMixin, DetailView):
    model = Certificate
    template_name = 'certificates/certificate_detail.html'
    context_object_name = 'certificate'


class CertificateDownloadView(LoginRequiredMixin, View):
    """Download certificate as PDF using ReportLab"""
    
    def get(self, request, *args, **kwargs):
        certificate = get_object_or_404(Certificate, pk=kwargs.get('pk'))
        school = get_object_or_404(School, slug=kwargs.get('school_slug'))
        
        try:
            # Create a buffer for the PDF
            buffer = BytesIO()
            
            # Create the PDF document in landscape orientation
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Custom styles for certificate
            title_style = ParagraphStyle(
                'CertificateTitle',
                parent=styles['Heading1'],
                fontSize=36,
                spaceAfter=30,
                textColor=colors.HexColor('#1E3A5F'),
                alignment=TA_CENTER,
                borderWidth=2,
                borderColor=colors.HexColor('#4DD0E1'),
                borderPadding=10
            )
            
            subtitle_style = ParagraphStyle(
                'CertificateSubtitle',
                parent=styles['Heading2'],
                fontSize=24,
                spaceAfter=20,
                textColor=colors.HexColor('#1E3A5F'),
                alignment=TA_CENTER
            )
            
            body_style = ParagraphStyle(
                'CertificateBody',
                parent=styles['Normal'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.black,
                alignment=TA_CENTER
            )
            
            left_style = ParagraphStyle(
                'CertificateLeft',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=8,
                textColor=colors.black,
                alignment=TA_LEFT
            )
            
            # Build the story (content)
            story = []
            
            # Add decorative border
            border_data = [[
                Paragraph('<b><font color="#1E3A5F">Certificate of Completion</font></b>', title_style)
            ]]
            border_table = Table(border_data, colWidths=[20*inch])
            border_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 3, colors.HexColor('#4DD0E1')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 40),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 40),
            ]))
            story.append(border_table)
            story.append(Spacer(1, 20))
            
            # School name
            story.append(Paragraph(f"<b>{school.name}</b>", subtitle_style))
            story.append(Spacer(1, 10))
            
            # Certificate text
            story.append(Paragraph("This is to certify that", body_style))
            story.append(Spacer(1, 10))
            
            # Student name (prominent)
            student_name = certificate.student.get_full_name() or certificate.student.user.get_full_name()
            story.append(Paragraph(f"<b><font size=18>{student_name}</font></b>", title_style))
            story.append(Spacer(1, 10))
            
            # Certificate type description
            story.append(Paragraph(f"has successfully completed the requirements for", body_style))
            story.append(Spacer(1, 10))
            
            # Certificate type
            story.append(Paragraph(f"<b><font size=16>{certificate.certificate_type.name}</font></b>", subtitle_style))
            story.append(Spacer(1, 10))
            
            # Additional details
            if certificate.certificate_type.description:
                story.append(Paragraph(certificate.certificate_type.description, body_style))
                story.append(Spacer(1, 15))
            
            # Date information
            issue_date = certificate.issue_date.strftime("%B %d, %Y") if certificate.issue_date else timezone.now().strftime("%B %d, %Y")
            story.append(Paragraph(f"Issued on: <b>{issue_date}</b>", body_style))
            story.append(Spacer(1, 20))
            
            # Certificate details table
            details_data = [
                ['Certificate Number:', certificate.certificate_number],
                ['Student ID:', certificate.student.admission_number or 'N/A'],
                ['Class/Grade:', certificate.student.current_class.name if certificate.student.current_class else 'N/A'],
                ['Academic Year:', certificate.academic_year or 'N/A'],
            ]
            
            details_table = Table(details_data, colWidths=[3*inch, 4*inch])
            details_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E1E8ED')),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
            ]))
            story.append(details_table)
            story.append(Spacer(1, 30))
            
            # Signature section
            signature_data = [
                ['', ''],
                [Paragraph('<b>_________________________</b>', left_style), Paragraph('<b>_________________________</b>', left_style)],
                [Paragraph('<b>Principal Signature</b>', left_style), Paragraph('<b>HOD Signature</b>', left_style)],
                [Paragraph(school.name, left_style), Paragraph(school.name, left_style)],
            ]
            
            signature_table = Table(signature_data, colWidths=[4*inch, 4*inch])
            signature_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(signature_table)
            story.append(Spacer(1, 20))
            
            # Verification code
            if certificate.verification_code:
                story.append(Paragraph(f"Verification Code: <b>{certificate.verification_code}</b>", left_style))
                story.append(Paragraph("Verify this certificate at: " + request.build_absolute_uri(reverse('certificates:verify', kwargs={'code': certificate.verification_code})), left_style))
            
            # Footer
            story.append(Spacer(1, 30))
            story.append(Paragraph(f"© {timezone.now().year} {school.name}. All rights reserved.", left_style))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF value
            pdf_value = buffer.getvalue()
            buffer.close()
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf_value, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{certificate.certificate_number}.pdf"'
            return response
            
        except ImportError as e:
            # Fallback to HTML-based certificate if ReportLab is not available
            return self.generate_html_certificate(request, certificate, school, str(e))
        except Exception as e:
            return HttpResponse(f'Error generating certificate: {str(e)}', status=500)
    
    def generate_html_certificate(self, request, certificate, school, error_msg):
        """Fallback method using HTML to certificate conversion"""
        try:
            context = {
                'certificate': certificate,
                'school': school,
                'request': request,
                'error_msg': error_msg
            }
            
            # Render the HTML template
            html_string = render_to_string('certificates/certificate_pdf_simple.html', context)
            
            # Create a simple HTML response that can be saved as PDF from browser
            response = HttpResponse(html_string, content_type='text/html')
            response['Content-Disposition'] = f'filename="{certificate.certificate_number}.html"'
            response['X-PDF-Warning'] = f'Certificate generation error: {error_msg}. Please save this HTML file and convert to PDF using your browser.'
            return response
            
        except Exception as e:
            return HttpResponse(f'Error generating certificate: {str(e)}', status=500)


class CertificateUpdateView(LoginRequiredMixin, UpdateView):
    model = Certificate
    form_class = CertificateForm
    template_name = 'certificates/certificate_form.html'
    
    def get_success_url(self):
        return reverse('certificates:list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update Certificate')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Certificate updated successfully'))
        return super().form_valid(form)


class CertificateDeleteView(LoginRequiredMixin, DeleteView):
    model = Certificate
    template_name = 'certificates/confirm_delete.html'
    
    def get_success_url(self):
        return reverse('certificates:list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete Certificate')
        context['message'] = _('Are you sure you want to delete this certificate?')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Certificate deleted successfully'))
        return super().form_valid(form)


class CertificateRevokeView(LoginRequiredMixin, UpdateView):
    model = Certificate
    template_name = 'certificates/certificate_revoke.html'
    fields = ['revocation_reason']
    
    def get_success_url(self):
        return reverse('certificates:list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Revoke Certificate')
        return context
    
    def form_valid(self, form):
        # Mark certificate as revoked
        form.instance.is_revoked = True
        form.instance.revoked_at = timezone.now()
        
        messages.success(self.request, _('Certificate revoked successfully'))
        return super().form_valid(form)


class CertificateVerifyView(FormView):
    form_class = CertificateVerifyForm
    template_name = 'certificates/certificate_verify.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verification_code'] = self.kwargs.get('code', None)
        return context
    
    def get(self, request, *args, **kwargs):
        # Check if verification code is in URL
        code = self.kwargs.get('code', None)
        if code:
            return self.verify_certificate(code)
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        verification_code = form.cleaned_data['verification_code']
        return self.verify_certificate(verification_code)
    
    def verify_certificate(self, code):
        try:
            certificate = Certificate.objects.get(verification_code=code, is_active=True)
            
            # Log verification
            CertificateVerification.objects.create(
                certificate=certificate,
                verification_code=code,
                verified_by_ip=self.request.META.get('REMOTE_ADDR'),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                is_valid=not certificate.is_revoked,
                verification_message='Valid certificate' if not certificate.is_revoked else 'Certificate revoked'
            )
            
            return render(self.request, 'certificates/certificate_verify_result.html', {
                'certificate': certificate,
                'is_valid': not certificate.is_revoked,
                'verification_date': timezone.now()
            })
            
        except Certificate.DoesNotExist:
            # Log failed verification attempt
            return render(self.request, 'certificates/certificate_verify_result.html', {
                'certificate': None,
                'is_valid': False,
                'error': _('Certificate not found or invalid verification code'),
                'verification_date': timezone.now()
            })


class PrintBatchCertificatesView(LoginRequiredMixin, FormView):
    template_name = 'certificates/print_batch_certificates.html'
    form_class = CertificateForm  # You might want to create a specific form for batch printing
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Print Batch Certificates')
        return context
    
    def form_valid(self, form):
        # Get selected certificates for batch printing
        certificate_ids = self.request.POST.getlist('certificates')
        certificates = Certificate.objects.filter(id__in=certificate_ids)
        school = get_object_or_404(School, slug=self.kwargs.get('school_slug'))
        
        try:
            # Create a buffer for the PDF
            buffer = BytesIO()
            
            # Create the PDF document in landscape orientation
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Custom styles for certificate
            title_style = ParagraphStyle(
                'CertificateTitle',
                parent=styles['Heading1'],
                fontSize=28,
                spaceAfter=20,
                textColor=colors.HexColor('#1E3A5F'),
                alignment=TA_CENTER
            )
            
            body_style = ParagraphStyle(
                'CertificateBody',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=8,
                textColor=colors.black,
                alignment=TA_CENTER
            )
            
            # Build the story (content)
            story = []
            
            # Add each certificate to the PDF
            for i, certificate in enumerate(certificates):
                # Certificate title
                story.append(Paragraph(f"<b>Certificate of Completion</b>", title_style))
                story.append(Spacer(1, 10))
                
                # School name
                story.append(Paragraph(f"<b>{school.name}</b>", body_style))
                story.append(Spacer(1, 8))
                
                # Certificate text
                story.append(Paragraph("This is to certify that", body_style))
                story.append(Spacer(1, 5))
                
                # Student name
                student_name = certificate.student.get_full_name() or certificate.student.user.get_full_name()
                story.append(Paragraph(f"<b><font size=16>{student_name}</font></b>", title_style))
                story.append(Spacer(1, 5))
                
                # Certificate type
                story.append(Paragraph(f"has successfully completed the requirements for", body_style))
                story.append(Paragraph(f"<b>{certificate.certificate_type.name}</b>", body_style))
                story.append(Spacer(1, 8))
                
                # Certificate details
                issue_date = certificate.issue_date.strftime("%B %d, %Y") if certificate.issue_date else timezone.now().strftime("%B %d, %Y")
                story.append(Paragraph(f"Issued on: <b>{issue_date}</b>", body_style))
                story.append(Spacer(1, 10))
                
                # Certificate number
                story.append(Paragraph(f"Certificate Number: <b>{certificate.certificate_number}</b>", body_style))
                
                # Add page break except for last certificate
                if i < len(certificates) - 1:
                    story.append(Spacer(1, 30))
                    story.append(Paragraph("=" * 50, body_style))
                    story.append(Spacer(1, 30))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF value
            pdf_value = buffer.getvalue()
            buffer.close()
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf_value, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="batch_certificates_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            return response
            
        except ImportError as e:
            # Fallback to HTML-based certificates if ReportLab is not available
            messages.error(self.request, f'PDF generation not available: {str(e)}. Please install ReportLab.')
            return super().form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error generating batch certificates: {str(e)}')
            return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('certificates:list', kwargs={'school_slug': self.kwargs['school_slug']})


# ID Card Template Views
class IDCardTemplateListView(LoginRequiredMixin, ListView):
    model = IDCardTemplate
    template_name = 'certificates/idcard_template_list.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        return IDCardTemplate.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class IDCardTemplateCreateView(LoginRequiredMixin, CreateView):
    model = IDCardTemplate
    form_class = IDCardTemplateForm
    template_name = 'certificates/idcard_template_form.html'
    
    def get_success_url(self):
        return reverse('certificates:idcard_template_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create ID Card Template')
        return context
    
    def form_valid(self, form):
        # Associate with school
        school_slug = self.kwargs.get('school_slug')
        try:
            school = School.objects.get(slug=school_slug)
            form.instance.school = school
        except School.DoesNotExist:
            pass
        
        messages.success(self.request, _('ID Card template created successfully'))
        return super().form_valid(form)


class IDCardTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = IDCardTemplate
    form_class = IDCardTemplateForm
    template_name = 'certificates/idcard_template_form.html'
    
    def get_success_url(self):
        return reverse('certificates:idcard_template_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update ID Card Template')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('ID Card template updated successfully'))
        return super().form_valid(form)


class IDCardTemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = IDCardTemplate
    template_name = 'certificates/confirm_delete.html'
    
    def get_success_url(self):
        return reverse('certificates:idcard_template_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Delete ID Card Template')
        context['message'] = _('Are you sure you want to delete this ID card template?')
        return context


# ID Card Views
class IDCardListView(LoginRequiredMixin, ListView):
    model = IDCard
    template_name = 'certificates/idcard_list.html'
    context_object_name = 'idcards'
    
    def get_queryset(self):
        return IDCard.objects.filter(is_active=True).select_related('student', 'card_template')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class IDCardCreateView(LoginRequiredMixin, CreateView):
    model = IDCard
    form_class = IDCardForm
    template_name = 'certificates/idcard_form.html'
    
    def get_success_url(self):
        return reverse('certificates:idcard_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Issue ID Card')
        return context
    
    def form_valid(self, form):
        # Set creator
        form.instance.created_by = self.request.user
        
        # Associate with school
        school_slug = self.kwargs.get('school_slug')
        try:
            school = School.objects.get(slug=school_slug)
            form.instance.school = school
        except School.DoesNotExist:
            pass
        
        # Save the card
        response = super().form_valid(form)
        
        # Generate card images
        self.object.generate_card_images()
        
        messages.success(self.request, _('ID Card issued successfully'))
        return response


class IDCardDetailView(LoginRequiredMixin, DetailView):
    model = IDCard
    template_name = 'certificates/idcard_detail.html'
    context_object_name = 'idcard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context


class IDCardUpdateView(LoginRequiredMixin, UpdateView):
    model = IDCard
    form_class = IDCardForm
    template_name = 'certificates/idcard_form.html'
    
    def get_success_url(self):
        return reverse('certificates:idcard_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Update ID Card')
        return context
    
    def form_valid(self, form):
        # Regenerate card images if template changed
        old_instance = self.get_object()
        if old_instance.card_template != form.cleaned_data['card_template']:
            response = super().form_valid(form)
            self.object.generate_card_images()
        else:
            response = super().form_valid(form)
        
        messages.success(self.request, _('ID Card updated successfully'))
        return response


class BulkIDCardCreateView(LoginRequiredMixin, FormView):
    form_class = BulkIDCardForm
    template_name = 'certificates/bulk_idcard_form.html'
    
    def get_success_url(self):
        return reverse('certificates:idcard_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Create Bulk ID Cards')
        return context
    
    def form_valid(self, form):
        students = form.cleaned_data['students']
        class_name = form.cleaned_data['class_name']
        card_template = form.cleaned_data['card_template']
        academic_year = form.cleaned_data['academic_year']
        issue_date = form.cleaned_data['issue_date']
        valid_from = form.cleaned_data['valid_from']
        valid_until = form.cleaned_data['valid_until']
        
        # If class is selected, get all students from that class
        if class_name and not students:
            students = Student.objects.filter(current_class=class_name, is_active=True)
        
        # Get school
        school_slug = self.kwargs.get('school_slug')
        try:
            school = School.objects.get(slug=school_slug)
        except School.DoesNotExist:
            school = None
        
        # Create ID cards for each student
        created_count = 0
        for student in students:
            id_card = IDCard(
                student=student,
                card_template=card_template,
                academic_year=academic_year,
                issue_date=issue_date,
                valid_from=valid_from,
                valid_until=valid_until,
                school=school,
                created_by=self.request.user
            )
            id_card.save()
            id_card.generate_card_images()
            created_count += 1
        
        messages.success(self.request, _(f'{created_count} ID Cards created successfully'))
        return super().form_valid(form)


class MarkIDCardLostView(LoginRequiredMixin, UpdateView):
    model = IDCard
    fields = ['lost_date']
    template_name = 'certificates/idcard_mark_lost.html'
    
    def get_initial(self):
        return {'lost_date': timezone.now().date()}
    
    def get_success_url(self):
        return reverse('certificates:idcard_list', kwargs={'school_slug': self.kwargs['school_slug']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['title'] = _('Mark ID Card as Lost')
        return context
    
    def form_valid(self, form):
        form.instance.is_lost = True
        messages.success(self.request, _('ID Card marked as lost'))
        return super().form_valid(form)


class PrintIDCardView(LoginRequiredMixin, DetailView):
    model = IDCard
    template_name = 'certificates/idcard_print.html'
    context_object_name = 'idcard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
