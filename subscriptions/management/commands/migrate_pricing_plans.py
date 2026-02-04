from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
try:
    from frontend.models import PricingPlan as LegacyPricingPlan  # May not exist anymore
except Exception:
    LegacyPricingPlan = None
from subscriptions.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Migrate frontend.PricingPlan data to subscriptions.SubscriptionPlan and remove old table'

    def handle(self, *args, **options):
        self.stdout.write("Starting migration of PricingPlan to SubscriptionPlan...")
        if LegacyPricingPlan is None:
            self.stdout.write("Legacy PricingPlan model not found. Nothing to migrate.")
            return
        
        # Map old plan names to new plan types
        PLAN_TYPE_MAP = {
            'basic': 'basic',
            'standard': 'standard',
            'premium': 'premium',
            'enterprise': 'enterprise',
            # No dedicated free_trial plan type anymore; map to basic
            'trial': 'basic'
        }
        
        # Map old durations to billing cycles
        DURATION_MAP = {
            'month': 'monthly',
            'year': 'yearly',
            'quarter': 'quarterly',
            'half_year': 'half_yearly',
            'one_time': 'yearly'  # Default one-time to yearly
        }
        
        migrated_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for plan in LegacyPricingPlan.objects.all():
                # Skip if a plan with this name already exists
                if SubscriptionPlan.objects.filter(name__iexact=plan.name).exists():
                    self.stdout.write(self.style.WARNING(f'Skipping duplicate plan: {plan.name}'))
                    skipped_count += 1
                    continue
                
                # Determine plan type
                plan_type = 'standard'  # default
                for key, value in PLAN_TYPE_MAP.items():
                    if key in plan.name.lower():
                        plan_type = value
                        break
                
                # Determine billing cycle
                duration = plan.duration.lower() if plan.duration else 'month'
                billing_cycle = DURATION_MAP.get(duration, 'monthly')
                
                # Derive features list and boolean flags from the legacy text field
                if hasattr(plan, "get_features_list"):
                    features_list = plan.get_features_list()
                else:
                    features_list = [
                        f.strip() for f in (plan.features or "").split("\n") if f.strip()
                    ]

                features_text = " ".join(f.lower() for f in features_list)

                enable_online_exam = "exam" in features_text
                enable_online_payment = "payment" in features_text or "gateway" in features_text
                enable_chat = "chat" in features_text or "message" in features_text
                enable_sms = "sms" in features_text or "text" in features_text
                enable_library = "library" in features_text
                enable_transport = "transport" in features_text or "bus" in features_text
                enable_dormitory = "dorm" in features_text or "hostel" in features_text
                enable_inventory = "inventory" in features_text or "stock" in features_text
                enable_hr = "hr" in features_text or "human resource" in features_text
                enable_reports = "report" in features_text or "analytics" in features_text

                # Create new SubscriptionPlan
                new_plan = SubscriptionPlan(
                    name=plan.name,
                    slug=slugify(plan.name),
                    plan_type=plan_type,
                    description=f"{plan.name} - {plan.duration} plan" if plan.duration else f"{plan.name} plan",
                    price=plan.price,
                    billing_cycle=billing_cycle,
                    trial_days=7 if 'trial' in plan.name.lower() else 0,
                    max_students=plan.max_students or 0,
                    max_branches=1,
                    storage_limit_gb=10,
                    features=features_list,
                    enable_online_exam=enable_online_exam,
                    enable_online_payment=enable_online_payment,
                    enable_chat=enable_chat,
                    enable_sms=enable_sms,
                    enable_library=enable_library,
                    enable_transport=enable_transport,
                    enable_dormitory=enable_dormitory,
                    enable_inventory=enable_inventory,
                    enable_hr=enable_hr,
                    enable_reports=enable_reports,
                    is_active=plan.is_active,
                    is_popular=plan.is_popular,
                    display_order=plan.order or 0,
                )
                
                new_plan.save()
                migrated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Migrated plan: {plan.name}'))
            
            # Drop the old table (if we have any migrations to apply)
            # This is a destructive operation, so we'll just print the SQL for now
            # Uncomment the actual deletion after reviewing the plan
            self.stdout.write("\n" + "="*80)
            self.stdout.write("Migration complete!")
            self.stdout.write(f"Migrated {migrated_count} plans")
            self.stdout.write(f"Skipped {skipped_count} duplicate plans")
            
            if migrated_count > 0:
                self.stdout.write("\nTo complete the migration, run these steps:")
                self.stdout.write("1. Review the migrated plans in the admin interface")
                self.stdout.write("2. Run this command to generate the migration to remove the old table:")
                self.stdout.write("   python manage.py makemigrations frontend --empty -n remove_pricingplan_model")
                self.stdout.write("3. Edit the generated migration to add the following operation:")
                self.stdout.write("""
    operations = [
        migrations.DeleteModel(
            name='PricingPlan',
        ),
    ]
                """)
                self.stdout.write("4. Run: python manage.py migrate frontend")
            else:
                self.stdout.write("No plans needed migration. You can safely remove the frontend.PricingPlan model.")
            
            self.stdout.write("="*80)
