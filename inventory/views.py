from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Q, F
from datetime import datetime, date
from decimal import Decimal
from .models import (
    Item, ItemCategory, Supplier, PurchaseOrder, PurchaseOrderItem,
    ItemDistribution, Expense, StaffPayment
)


# ============= INVENTORY MANAGEMENT =============

@method_decorator(csrf_exempt, name='dispatch')
class InventoryListView(LoginRequiredMixin, ListView):
    model = Item
    template_name = 'inventory/inventory_list.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        return Item.objects.filter(is_active=True).select_related('category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['categories'] = ItemCategory.objects.filter(is_active=True)
        context['low_stock_items'] = Item.objects.filter(
            quantity_in_stock__lte=F('reorder_level'),
            is_active=True
        )
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            action = request.POST.get('action')
            
            if action == 'add_item':
                item = Item.objects.create(
                    name=request.POST.get('name'),
                    code=request.POST.get('code'),
                    category_id=request.POST.get('category'),
                    description=request.POST.get('description', ''),
                    unit=request.POST.get('unit', 'piece'),
                    unit_price=request.POST.get('unit_price'),
                    quantity_in_stock=request.POST.get('quantity_in_stock', 0),
                    reorder_level=request.POST.get('reorder_level', 10)
                )
                return JsonResponse({'success': True, 'message': 'Item added successfully'})
            
            elif action == 'update_stock':
                item = Item.objects.get(id=request.POST.get('item_id'))
                new_quantity = Decimal(request.POST.get('quantity'))
                item.quantity_in_stock = new_quantity
                item.save()
                return JsonResponse({'success': True, 'message': 'Stock updated successfully'})
            
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ============= SUPPLIER MANAGEMENT =============

@method_decorator(csrf_exempt, name='dispatch')
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'inventory/supplier_list.html'
    context_object_name = 'suppliers'
    
    def get_queryset(self):
        return Supplier.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            Supplier.objects.create(
                name=request.POST.get('name'),
                contact_person=request.POST.get('contact_person', ''),
                email=request.POST.get('email', ''),
                phone=request.POST.get('phone'),
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                tax_id=request.POST.get('tax_id', ''),
                payment_terms=request.POST.get('payment_terms', 'Net 30'),
                notes=request.POST.get('notes', '')
            )
            return JsonResponse({'success': True, 'message': 'Supplier added successfully'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ============= PURCHASE ORDER MANAGEMENT =============

@method_decorator(csrf_exempt, name='dispatch')
class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    
    def get_queryset(self):
        return PurchaseOrder.objects.all().select_related('supplier', 'created_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['suppliers'] = Supplier.objects.filter(is_active=True)
        context['items'] = Item.objects.filter(is_active=True)
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            action = request.POST.get('action')
            
            if action == 'create_po':
                # Generate PO number
                last_po = PurchaseOrder.objects.order_by('-po_number').first()
                if last_po and last_po.po_number.startswith('PO-'):
                    try:
                        last_num = int(last_po.po_number.split('-')[1])
                        po_number = f"PO-{last_num + 1:05d}"
                    except:
                        po_number = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                else:
                    po_number = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                po = PurchaseOrder.objects.create(
                    po_number=po_number,
                    supplier_id=request.POST.get('supplier_id'),
                    order_date=request.POST.get('order_date'),
                    expected_delivery_date=request.POST.get('expected_delivery_date'),
                    notes=request.POST.get('notes', ''),
                    created_by=request.user
                )
                return JsonResponse({
                    'success': True,
                    'message': 'Purchase order created',
                    'po_id': po.id,
                    'po_number': po.po_number
                })
            
            elif action == 'add_po_item':
                po = PurchaseOrder.objects.get(id=request.POST.get('po_id'))
                item = Item.objects.get(id=request.POST.get('item_id'))
                quantity = Decimal(request.POST.get('quantity'))
                unit_price = Decimal(request.POST.get('unit_price', item.unit_price))
                
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    item=item,
                    quantity=quantity,
                    unit_price=unit_price,
                    total=quantity * unit_price
                )
                po.calculate_totals()
                return JsonResponse({'success': True, 'message': 'Item added to purchase order'})
            
            elif action == 'approve_po':
                po = PurchaseOrder.objects.get(id=request.POST.get('po_id'))
                po.status = 'approved'
                po.approved_by = request.user
                po.save()
                return JsonResponse({'success': True, 'message': 'Purchase order approved'})
            
            elif action == 'receive_po':
                po = PurchaseOrder.objects.get(id=request.POST.get('po_id'))
                po.status = 'received'
                po.actual_delivery_date = date.today()
                po.save()
                
                # Update inventory
                for po_item in po.items.all():
                    po_item.item.quantity_in_stock += po_item.quantity
                    po_item.item.save()
                    po_item.received_quantity = po_item.quantity
                    po_item.save()
                
                # Create expense record
                expense_number = f"EXP-{po.po_number}"
                Expense.objects.create(
                    expense_number=expense_number,
                    expense_type='purchase',
                    description=f"Purchase from {po.supplier.name}",
                    amount=po.total_amount,
                    expense_date=date.today(),
                    payment_method=request.POST.get('payment_method', 'bank_transfer'),
                    reference_number=po.po_number,
                    purchase_order=po,
                    payee_name=po.supplier.name,
                    created_by=request.user
                )
                
                return JsonResponse({'success': True, 'message': 'Purchase order received and inventory updated'})
            
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


# ============= ITEM DISTRIBUTION =============

@method_decorator(csrf_exempt, name='dispatch')
class ItemDistributionView(LoginRequiredMixin, ListView):
    model = ItemDistribution
    template_name = 'inventory/distribution_list.html'
    context_object_name = 'distributions'
    
    def get_queryset(self):
        return ItemDistribution.objects.all().select_related('item', 'distributed_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['items'] = Item.objects.filter(is_active=True)
        
        # Import models for recipient selection
        from human_resource.models import Teacher, Staff
        from students.models import Student
        
        context['teachers'] = Teacher.objects.filter(is_active=True)
        context['staff'] = Staff.objects.filter(is_active=True)
        context['students'] = Student.objects.all()[:100]  # Limit for performance
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            item = Item.objects.get(id=request.POST.get('item_id'))
            quantity = Decimal(request.POST.get('quantity'))
            
            # Check stock availability
            if item.quantity_in_stock < quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Insufficient stock. Available: {item.quantity_in_stock}'
                })
            
            # Create distribution record
            ItemDistribution.objects.create(
                item=item,
                quantity=quantity,
                recipient_type=request.POST.get('recipient_type'),
                recipient_id=request.POST.get('recipient_id'),
                recipient_name=request.POST.get('recipient_name'),
                distribution_date=request.POST.get('distribution_date', date.today()),
                purpose=request.POST.get('purpose', ''),
                notes=request.POST.get('notes', ''),
                distributed_by=request.user
            )
            
            # Update stock
            item.quantity_in_stock -= quantity
            item.save()
            
            return JsonResponse({'success': True, 'message': 'Item distributed successfully'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ============= EXPENSE TRACKING =============

@method_decorator(csrf_exempt, name='dispatch')
class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'inventory/expense_list.html'
    context_object_name = 'expenses'
    
    def get_queryset(self):
        return Expense.objects.all().select_related('created_by', 'purchase_order')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Calculate totals by expense type
        expense_summary = Expense.objects.values('expense_type').annotate(
            total=Sum('amount')
        )
        context['expense_summary'] = expense_summary
        context['total_expenses'] = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            # Generate expense number
            last_expense = Expense.objects.order_by('-expense_number').first()
            if last_expense and last_expense.expense_number.startswith('EXP-'):
                try:
                    last_num = int(last_expense.expense_number.split('-')[1])
                    expense_number = f"EXP-{last_num + 1:05d}"
                except:
                    expense_number = f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            else:
                expense_number = f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            Expense.objects.create(
                expense_number=expense_number,
                expense_type=request.POST.get('expense_type'),
                description=request.POST.get('description'),
                amount=request.POST.get('amount'),
                expense_date=request.POST.get('expense_date'),
                payment_method=request.POST.get('payment_method'),
                reference_number=request.POST.get('reference_number', ''),
                payee_name=request.POST.get('payee_name'),
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            return JsonResponse({'success': True, 'message': 'Expense recorded successfully'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ============= STAFF PAYMENT MANAGEMENT =============

@method_decorator(csrf_exempt, name='dispatch')
class StaffPaymentView(LoginRequiredMixin, ListView):
    model = StaffPayment
    template_name = 'inventory/staff_payment_list.html'
    context_object_name = 'payments'
    
    def get_queryset(self):
        return StaffPayment.objects.all().select_related('created_by', 'expense')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Import models
        from human_resource.models import Teacher, Staff
        import json
        
        # Fetch teachers and staff with salary data
        teachers = Teacher.objects.filter(is_active=True).values(
            'id', 'first_name', 'last_name', 'basic_salary', 'allowances', 'employee_id'
        )
        staff_members = Staff.objects.filter(is_active=True).values(
            'id', 'first_name', 'last_name', 'basic_salary', 'allowances', 'employee_id'
        )
        
        # Convert to list and serialize for JavaScript
        context['teachers_json'] = json.dumps(list(teachers))
        context['staff_json'] = json.dumps(list(staff_members))
        context['teachers'] = Teacher.objects.filter(is_active=True)
        context['staff_members'] = Staff.objects.filter(is_active=True)
        
        # Calculate totals
        context['total_payments'] = StaffPayment.objects.filter(
            status='paid'
        ).aggregate(Sum('net_salary'))['net_salary__sum'] or 0
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            # Generate payment number
            last_payment = StaffPayment.objects.order_by('-payment_number').first()
            if last_payment and last_payment.payment_number.startswith('PAY-'):
                try:
                    last_num = int(last_payment.payment_number.split('-')[1])
                    payment_number = f"PAY-{last_num + 1:05d}"
                except:
                    payment_number = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            else:
                payment_number = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            payment = StaffPayment.objects.create(
                payment_number=payment_number,
                staff_type=request.POST.get('staff_type'),
                staff_id=request.POST.get('staff_id'),
                staff_name=request.POST.get('staff_name'),
                payment_month=request.POST.get('payment_month'),
                basic_salary=request.POST.get('basic_salary'),
                allowances=request.POST.get('allowances', 0),
                deductions=request.POST.get('deductions', 0),
                payment_date=request.POST.get('payment_date'),
                payment_method=request.POST.get('payment_method'),
                reference_number=request.POST.get('reference_number', ''),
                status=request.POST.get('status', 'pending'),
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            return JsonResponse({
                'success': True,
                'message': 'Payment recorded successfully',
                'payment_id': payment.id
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})


# ============= PRINT VIEWS =============

class PurchaseOrderPrintView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'inventory/print_purchase_order.html'
    context_object_name = 'purchase_order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['po_items'] = self.object.items.all()
        return context


class PaymentReceiptPrintView(LoginRequiredMixin, DetailView):
    model = StaffPayment
    template_name = 'inventory/print_payment_receipt.html'
    context_object_name = 'payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
