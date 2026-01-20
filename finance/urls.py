from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.FinanceDashboardView.as_view(), name='dashboard'),
    path('donations/', views.ReceiveDonationView.as_view(), name='donations'),
    path('accounts/', views.ChartOfAccountsView.as_view(), name='accounts'),
    path('ledger/', views.GeneralLedgerView.as_view(), name='ledger'),
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('reclassify/', views.ReclassifyDepositsView.as_view(), name='reclassify'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/update/', views.AccountUpdateView.as_view(), name='account_update'),
]
