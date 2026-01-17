from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Q, F
from datetime import datetime, date
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import (
    Item, ItemCategory, Supplier, PurchaseOrder, PurchaseOrderItem,
    ItemDistribution, Expense, StaffPayment
)
from core.utils import get_current_school


# ============= INVENTORY MANAGEMENT =============

@method_decorator(csrf_exempt, name='dispatch')
class InventoryListView(LoginRequiredMixin, ListView):
    model = Item
    template_name = 'inventory/inventory_list.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = Item.objects.filter(is_active=True).select_related('category')
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        # Ensure there are some default categories available
        categories_qs = ItemCategory.objects.filter(is_active=True)
        if school:
            categories_qs = categories_qs.filter(school=school)
        if not categories_qs.exists():
            default_categories = [
                ("Books", "stationery"),
                ("Stationery", "stationery"),
                ("Food Supplies", "food"),
                ("Equipment", "equipment"),
                ("Furniture", "furniture"),
                ("Supplies", "supplies"),
                ("Other", "other"),
            ]
            for name, cat_type in default_categories:
                ItemCategory.objects.get_or_create(
                    name=name,
                    defaults={"category_type": cat_type, "is_active": True, "school": school},
                )
            categories_qs = ItemCategory.objects.filter(is_active=True)
            if school:
                categories_qs = categories_qs.filter(school=school)

        context['categories'] = categories_qs
        low_stock_qs = Item.objects.filter(quantity_in_stock__lte=F('reorder_level'), is_active=True)
        if school:
            low_stock_qs = low_stock_qs.filter(school=school)
        context['low_stock_items'] = low_stock_qs
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})

            school = get_current_school(request)
            
            action = request.POST.get('action')
            
            if action == 'add_item':
                item = Item.objects.create(
                    school=school,
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

            elif action == 'edit_item':
                item_qs = Item.objects.all()
                if school:
                    item_qs = item_qs.filter(school=school)
                item = item_qs.get(id=request.POST.get('item_id'))
                item.name = request.POST.get('name')
                item.code = request.POST.get('code')
                item.category_id = request.POST.get('category') or None
                item.description = request.POST.get('description', '')
                item.unit = request.POST.get('unit', 'piece')
                item.unit_price = request.POST.get('unit_price')
                item.reorder_level = request.POST.get('reorder_level', 10)
                item.save()
                return JsonResponse({'success': True, 'message': 'Item updated successfully'})
            
            elif action == 'update_stock':
                item_qs = Item.objects.all()
                if school:
                    item_qs = item_qs.filter(school=school)
                item = item_qs.get(id=request.POST.get('item_id'))
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
        school = get_current_school(self.request)
        qs = Supplier.objects.filter(is_active=True)
        if school:
            qs = qs.filter(school=school)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})

            school = get_current_school(request)
            
            Supplier.objects.create(
                school=school,
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
        school = get_current_school(self.request)
        qs = PurchaseOrder.objects.all().select_related('supplier', 'created_by')
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        suppliers_qs = Supplier.objects.filter(is_active=True)
        items_qs = Item.objects.filter(is_active=True)
        if school:
            suppliers_qs = suppliers_qs.filter(school=school)
            items_qs = items_qs.filter(school=school)
        context['suppliers'] = suppliers_qs
        context['items'] = items_qs
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})

            school = get_current_school(request)
            
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
                    school=school,
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
                po_qs = PurchaseOrder.objects.all()
                item_qs = Item.objects.all()
                if school:
                    po_qs = po_qs.filter(school=school)
                    item_qs = item_qs.filter(school=school)
                po = po_qs.get(id=request.POST.get('po_id'))
                item = item_qs.get(id=request.POST.get('item_id'))
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
                po_qs = PurchaseOrder.objects.all()
                if school:
                    po_qs = po_qs.filter(school=school)
                po = po_qs.get(id=request.POST.get('po_id'))
                po.status = 'approved'
                po.approved_by = request.user
                po.save()
                return JsonResponse({'success': True, 'message': 'Purchase order approved'})
            
            elif action == 'receive_po':
                po_qs = PurchaseOrder.objects.all()
                if school:
                    po_qs = po_qs.filter(school=school)
                po = po_qs.get(id=request.POST.get('po_id'))
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
                    school=school,
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
        school = get_current_school(self.request)
        qs = ItemDistribution.objects.all().select_related('item', 'distributed_by')
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        items_qs = Item.objects.filter(is_active=True).select_related('category')
        categories_qs = ItemCategory.objects.filter(is_active=True)
        if school:
            items_qs = items_qs.filter(school=school)
            categories_qs = categories_qs.filter(school=school)
        context['items'] = items_qs
        context['categories'] = categories_qs
        
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

            school = get_current_school(request)
            
            action = request.POST.get('action')
            
            if action == 'edit_distribution':
                distribution_qs = ItemDistribution.objects.all()
                if school:
                    distribution_qs = distribution_qs.filter(school=school)
                distribution = distribution_qs.get(id=request.POST.get('distribution_id'))
                old_quantity = distribution.quantity
                
                # Update fields
                distribution.item_id = request.POST.get('item_id')
                distribution.quantity = Decimal(request.POST.get('quantity'))
                distribution.recipient_type = request.POST.get('recipient_type')
                distribution.recipient_id = request.POST.get('recipient_id')
                distribution.recipient_name = request.POST.get('recipient_name')
                distribution.distribution_date = request.POST.get('distribution_date', date.today())
                distribution.purpose = request.POST.get('purpose', '')
                distribution.notes = request.POST.get('notes', '')
                distribution.save()
                
                # Adjust stock based on quantity change
                item = distribution.item
                if distribution.quantity > old_quantity:
                    # Additional quantity taken from stock
                    item.quantity_in_stock -= (distribution.quantity - old_quantity)
                elif distribution.quantity < old_quantity:
                    # Some quantity returned to stock
                    item.quantity_in_stock += (old_quantity - distribution.quantity)
                item.save()
                
                return JsonResponse({'success': True, 'message': 'Distribution updated successfully'})
            
            # Original distribution logic
            item_qs = Item.objects.all()
            if school:
                item_qs = item_qs.filter(school=school)
            item = item_qs.get(id=request.POST.get('item_id'))
            quantity = Decimal(request.POST.get('quantity'))
            
            # Check stock availability
            if item.quantity_in_stock < quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Insufficient stock. Available: {item.quantity_in_stock}'
                })
            
            # Create distribution record
            ItemDistribution.objects.create(
                school=school,
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
        school = get_current_school(self.request)
        qs = Expense.objects.all().select_related('created_by', 'purchase_order')
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        school = get_current_school(self.request)
        
        # Calculate totals by expense type
        expense_summary_qs = Expense.objects.all()
        if school:
            expense_summary_qs = expense_summary_qs.filter(school=school)
        expense_summary = expense_summary_qs.values('expense_type').annotate(
            total=Sum('amount')
        )
        context['expense_summary'] = expense_summary
        context['total_expenses'] = expense_summary_qs.aggregate(Sum('amount'))['amount__sum'] or 0
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})
            
            # Current school for multi-tenant scoping
            school = get_current_school(request)

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
                school=school,
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
        school = get_current_school(self.request)
        qs = StaffPayment.objects.all().select_related('created_by', 'expense')
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        
        # Import models
        from human_resource.models import Teacher, Staff
        from accounts.models import User
        
        # Initialize empty lists
        teachers = []
        staff_members = []
        
        try:
            # Get the current tenant (school) from the request
            current_tenant = getattr(self.request, 'tenant', None)
            print(f"Current tenant: {current_tenant}")
            current_school = get_current_school(self.request)
            
            if current_tenant:
                # Get all active users in the current tenant
                school_users = User.objects.filter(is_active=True)
                if current_school:
                    school_users = school_users.filter(school=current_school)
                print(f"Active users in tenant: {school_users.count()}")
                
                if school_users.exists():
                    # Print all users and their roles for debugging
                    print("All users and their roles:")
                    for user in school_users:
                        print(f"- {user.get_full_name()} (ID: {user.id}): Role={getattr(user, 'role', 'N/A')}, is_staff={user.is_staff}, is_superuser={user.is_superuser}")
                    
                    # Get all active users with teacher or staff role
                    teachers = []
                    staff_members = []
                    
                    # Try different role field names that might be used
                    possible_teacher_roles = ['teacher', 'staff', 'is_teacher', 'is_staff']
                    possible_staff_roles = ['staff', 'employee', 'is_staff', 'is_employee']
                    
                    # Check which role fields exist on the User model
                    user_fields = [f.name for f in school_users.model._meta.get_fields()]
                    print(f"Available user fields: {user_fields}")
                    
                    # Find which role field to use
                    role_field = None
                    for field in ['role', 'user_type', 'type']:
                        if field in user_fields:
                            role_field = field
                            break
                    
                    if role_field:
                        print(f"Using role field: {role_field}")
                        # Get users with teacher role
                        teacher_users = school_users.filter(**{f"{role_field}__in": ['teacher', 'is_teacher']})
                        # Get users with staff role (excluding teachers)
                        staff_users = school_users.filter(**{f"{role_field}__in": ['staff', 'is_staff', 'employee']})
                    else:
                        print("No explicit role field found, falling back to is_staff")
                        teacher_users = school_users.filter(is_staff=True)
                        staff_users = school_users.filter(is_staff=True)  # Same as teachers for now
                    
                    print(f"Found {teacher_users.count()} teachers and {staff_users.count()} staff users")
                    
                    # Format teacher data
                    for user in teacher_users:
                        teachers.append({
                            'id': user.id,
                            'first_name': user.first_name,
                            'last_name': user.last_name or '',
                            'basic_salary': '0',  # Default value
                            'allowances': '0',    # Default value
                            'employee_id': getattr(user, 'employee_id', f'TEACH-{user.id}'),
                            'user_id': user.id
                        })
                    
                    # Format staff data
                    for user in staff_users:
                        # Skip if already in teachers to avoid duplicates
                        if user.id not in [t['user_id'] for t in teachers]:
                            staff_members.append({
                                'id': user.id,
                                'first_name': user.first_name,
                                'last_name': user.last_name or '',
                                'basic_salary': '0',  # Default value
                                'allowances': '0',    # Default value
                                'employee_id': getattr(user, 'employee_id', f'STAFF-{user.id}'),
                                'user_id': user.id
                            })
                    
                    print(f"Found {len(teachers)} teachers and {len(staff_members)} staff in tenant")
                else:
                    print("No active users found in the current tenant")
            else:
                print("No tenant found in the request")
                
        except Exception as e:
            import traceback
            print("Error in get_context_data:")
            print(str(e))
            print(traceback.format_exc())
        
        # Don't convert to JSON string here - the json_script template filter will handle it
        context['teachers_json'] = teachers
        context['staff_json'] = staff_members
        
        # Debug output
        print("Teachers data being sent to template:", teachers)
        print("Staff data being sent to template:", staff_members)
        
        # Add debug info to template
        context['debug_info'] = {
            'teachers_count': len(teachers),
            'staff_count': len(staff_members),
            'school': str(current_tenant) if current_tenant else 'None'
        }
        
        # Calculate totals for the current school regardless of tenant middleware
        context['total_payments'] = 0  # Default value
        try:
            payments_qs = StaffPayment.objects.all()
            if current_school:
                payments_qs = payments_qs.filter(school=current_school)
            # Case-insensitive match for 'paid' to handle inconsistent casing
            payments_qs = payments_qs.filter(status__iexact='paid')
            context['total_payments'] = payments_qs.aggregate(Sum('net_salary'))['net_salary__sum'] or 0
            # Fallback: if aggregation returns 0 but there are visible paid rows, sum them from the context list
            if not context['total_payments'] and 'payments' in context:
                from decimal import Decimal as _D
                visible_total = _D('0')
                for p in context['payments']:
                    try:
                        if getattr(p, 'status', '').lower() == 'paid' and getattr(p, 'net_salary', None) is not None:
                            visible_total += _D(str(p.net_salary))
                    except Exception:
                        continue
                if visible_total:
                    context['total_payments'] = visible_total
        except Exception as e:
            print(f"Error calculating total payments: {e}")
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'Not authenticated'})

            school = get_current_school(request)
            
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
            
            # Convert string values to Decimal for calculations
            basic_salary = Decimal(request.POST.get('basic_salary', 0) or 0)
            allowances = Decimal(request.POST.get('allowances', 0) or 0)
            deductions = Decimal(request.POST.get('deductions', 0) or 0)
            
            # Format payment_month to ensure it's a valid date (YYYY-MM-DD)
            payment_month = request.POST.get('payment_month')
            if payment_month and len(payment_month) == 7 and payment_month[4] == '-':  # Format: YYYY-MM
                payment_month = f"{payment_month}-01"  # Convert to YYYY-MM-01
            
            payment = StaffPayment.objects.create(
                school=school,
                payment_number=payment_number,
                staff_type=request.POST.get('staff_type'),
                staff_id=request.POST.get('staff_id'),
                staff_name=request.POST.get('staff_name'),
                payment_month=payment_month,
                basic_salary=basic_salary,
                allowances=allowances,
                deductions=deductions,
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
    
    def get_queryset(self):
        school = get_current_school(self.request)
        qs = super().get_queryset()
        if school:
            qs = qs.filter(school=school)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        context['po_items'] = self.object.items.all()
        return context


class PaymentReceiptPrintView(LoginRequiredMixin, DetailView):
    model = StaffPayment
    template_name = 'inventory/print_payment_receipt.html'
    context_object_name = 'payment'

    def get_queryset(self):
        school = get_current_school(self.request)
        qs = super().get_queryset()
        if school:
            qs = qs.filter(school=school)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.kwargs.get('school_slug', '')
        return context
