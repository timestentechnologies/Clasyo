from django.urls import path
from . import views

app_name = 'fees'

urlpatterns = [
    path('', views.FeeStructureView.as_view(), name='fee_structure'),
    path('collect/', views.CollectFeesView.as_view(), name='collect_fees'),
    path('transactions/', views.FeeTransactionView.as_view(), name='transactions'),
    path('wallet/', views.WalletView.as_view(), name='wallet'),
]
