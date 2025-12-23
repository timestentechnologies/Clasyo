from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Schools
    path('schools/', views.SchoolListView.as_view(), name='schools'),
    path('schools/create/', views.SchoolCreateView.as_view(), name='school_create'),
    path('schools/<int:pk>/', views.SchoolDetailView.as_view(), name='school_detail'),
    path('schools/<int:pk>/edit/', views.SchoolUpdateView.as_view(), name='school_edit'),
    path('schools/<int:pk>/delete/', views.SchoolDeleteView.as_view(), name='school_delete'),
    
    # School Admins
    path('admins/', views.AdminUserListView.as_view(), name='admins'),
    path('admins/create/', views.AdminUserCreateView.as_view(), name='admin_create'),
    path('admins/<int:pk>/edit/', views.AdminUserUpdateView.as_view(), name='admin_edit'),
    
    # Subscriptions
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscriptions'),
    path('subscriptions/edit/', views.SubscriptionEditView.as_view(), name='subscription_edit'),
    
    # Content Management
    path('content/pricing/', views.PricingManagementView.as_view(), name='pricing_management'),
    path('content/faq/', views.FAQManagementView.as_view(), name='faq_management'),
    path('content/pages/', views.PageContentManagementView.as_view(), name='page_content_management'),
    path('content/messages/', views.ContactMessagesView.as_view(), name='contact_messages'),
    
    # Impersonation
    path('impersonate/<int:user_id>/', views.ImpersonateUserView.as_view(), name='impersonate_user'),
    path('stop-impersonation/', views.StopImpersonationView.as_view(), name='stop_impersonation'),
    
    # Profile
    path('profile/', views.SuperAdminProfileView.as_view(), name='profile'),
    
    # Payment Configurations
    path('payment-config/', views.PaymentConfigurationListView.as_view(), name='payment_config_list'),
    path('payment-config/create/', views.PaymentConfigurationCreateView.as_view(), name='payment_config_create'),
    path('payment-config/<int:pk>/', views.PaymentConfigurationDetailView.as_view(), name='payment_config_detail'),
    path('payment-config/<int:pk>/edit/', views.PaymentConfigurationUpdateView.as_view(), name='payment_config_update'),
    path('payment-config/<int:pk>/delete/', views.PaymentConfigurationDeleteView.as_view(), name='payment_config_delete'),
    
    # Payment Approvals
    path('payments/approval/', views.PaymentApprovalListView.as_view(), name='payment_approval_list'),
    path('payments/<uuid:payment_id>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<uuid:payment_id>/verify/', views.PaymentVerifyView.as_view(), name='payment_verify'),
    path('payments/<uuid:payment_id>/approve/', views.PaymentApproveView.as_view(), name='payment_approve'),
    path('payments/<uuid:payment_id>/reject/', views.PaymentRejectView.as_view(), name='payment_reject'),
    path('payments/history/', views.PaymentHistoryListView.as_view(), name='payment_history'),
    
    # School Admin Payment Configurations
    path('school/<slug:school_slug>/payment-config/', views.SchoolPaymentConfigurationListView.as_view(), name='school_payment_config_list'),
    path('school/<slug:school_slug>/payment-config/create/', views.SchoolPaymentConfigurationCreateView.as_view(), name='school_payment_config_create'),
    path('school/<slug:school_slug>/payment-config/<int:pk>/', views.SchoolPaymentConfigurationDetailView.as_view(), name='school_payment_config_detail'),
    path('school/<slug:school_slug>/payment-config/<int:pk>/edit/', views.SchoolPaymentConfigurationUpdateView.as_view(), name='school_payment_config_update'),
    path('school/<slug:school_slug>/payment-config/<int:pk>/delete/', views.SchoolPaymentConfigurationDeleteView.as_view(), name='school_payment_config_delete'),
    
    # Global Settings
    path('settings/', views.GlobalSettingsView.as_view(), name='global_settings'),
    
    # SMS Configurations
    path('settings/sms/', views.GlobalSMSConfigurationListView.as_view(), name='sms_config_list'),
    path('settings/sms/create/', views.GlobalSMSConfigurationCreateView.as_view(), name='sms_config_create'),
    path('settings/sms/<int:pk>/edit/', views.GlobalSMSConfigurationUpdateView.as_view(), name='sms_config_update'),
    path('settings/sms/<int:pk>/delete/', views.GlobalSMSConfigurationDeleteView.as_view(), name='sms_config_delete'),
    
    # Email Configurations
    path('settings/email/', views.GlobalEmailConfigurationListView.as_view(), name='email_config_list'),
    path('settings/email/create/', views.GlobalEmailConfigurationCreateView.as_view(), name='email_config_create'),
    path('settings/email/<int:pk>/edit/', views.GlobalEmailConfigurationUpdateView.as_view(), name='email_config_update'),
    path('settings/email/<int:pk>/delete/', views.GlobalEmailConfigurationDeleteView.as_view(), name='email_config_delete'),
    
    # Database Configurations
    path('settings/database/', views.GlobalDatabaseConfigurationListView.as_view(), name='db_config_list'),
    path('settings/database/create/', views.GlobalDatabaseConfigurationCreateView.as_view(), name='db_config_create'),
    path('settings/database/<int:pk>/edit/', views.GlobalDatabaseConfigurationUpdateView.as_view(), name='db_config_update'),
    path('settings/database/<int:pk>/delete/', views.GlobalDatabaseConfigurationDeleteView.as_view(), name='db_config_delete'),
    
    # School SMS Configurations
    path('school/<slug:school_slug>/settings/sms/', views.SchoolSMSConfigurationListView.as_view(), name='school_sms_config_list'),
    path('school/<slug:school_slug>/settings/sms/create/', views.SchoolSMSConfigurationCreateView.as_view(), name='school_sms_config_create'),
    path('school/<slug:school_slug>/settings/sms/<int:pk>/edit/', views.SchoolSMSConfigurationUpdateView.as_view(), name='school_sms_config_update'),
    path('school/<slug:school_slug>/settings/sms/<int:pk>/delete/', views.SchoolSMSConfigurationDeleteView.as_view(), name='school_sms_config_delete'),
    
    # School Email Configurations
    path('school/<slug:school_slug>/settings/email/', views.SchoolEmailConfigurationListView.as_view(), name='school_email_config_list'),
    path('school/<slug:school_slug>/settings/email/create/', views.SchoolEmailConfigurationCreateView.as_view(), name='school_email_config_create'),
    path('school/<slug:school_slug>/settings/email/<int:pk>/edit/', views.SchoolEmailConfigurationUpdateView.as_view(), name='school_email_config_update'),
    path('school/<slug:school_slug>/settings/email/<int:pk>/delete/', views.SchoolEmailConfigurationDeleteView.as_view(), name='school_email_config_delete'),
]
