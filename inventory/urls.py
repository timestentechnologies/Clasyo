from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Inventory Management
    path('', views.InventoryListView.as_view(), name='inventory_list'),
    
    # Suppliers
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    
    # Purchase Orders
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/<int:pk>/print/', views.PurchaseOrderPrintView.as_view(), name='print_purchase_order'),
    
    # Item Distribution
    path('distributions/', views.ItemDistributionView.as_view(), name='distribution_list'),
    
    # Expenses
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    
    # Staff Payments
    path('payments/', views.StaffPaymentView.as_view(), name='staff_payment_list'),
    path('payments/<int:pk>/print/', views.PaymentReceiptPrintView.as_view(), name='print_payment_receipt'),
]
