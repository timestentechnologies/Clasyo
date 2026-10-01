from django.core.management.base import BaseCommand, CommandError

from tenants.school_sync import sync_tenant_school_record
from tenants.tenant_ops import (
    describe_tenant_backend,
    iter_provisioned_tenant_schools,
    registered_tenant_schools,
    tenant_database_is_provisioned,
)


class Command(BaseCommand):
    help = (
        "Repair tenant databases by synchronizing master School records into each "
        "provisioned tenant (idempotent; preserves primary keys)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            default=None,
            help='Sync only this school slug.',
        )
        parser.add_argument(
            '--include-unprovisioned',
            action='store_true',
            help='Include registered schools even when the physical tenant database is missing.',
        )

    def handle(self, *args, **options):
        slug = options.get('slug')
        skip_missing = not options.get('include_unprovisioned')

        if slug and not registered_tenant_schools(slug=slug).exists():
            raise CommandError(f"No School registered on master with slug '{slug}'.")

        self.stdout.write(f"Tenant backend: {describe_tenant_backend()}")

        summary = {'created': 0, 'updated': 0, 'unchanged': 0}
        failures: list[str] = []

        if skip_missing:
            school_iter = iter_provisioned_tenant_schools(slug=slug, skip_missing_database=True)
        else:
            school_iter = registered_tenant_schools(slug=slug)

        count = 0
        for school in school_iter:
            db_alias = school.slug
            if skip_missing and not tenant_database_is_provisioned(db_alias):
                self.stdout.write(self.style.WARNING(f"Skipping '{db_alias}' (tenant storage not provisioned)."))
                continue

            count += 1
            self.stdout.write(f"Syncing School pk={school.pk} into '{db_alias}'...")
            try:
                result = sync_tenant_school_record(school, db_alias=db_alias)
                summary[result] += 1
            except Exception as exc:
                failures.append(f"{db_alias}: {exc}")
                self.stderr.write(self.style.ERROR(f"  failed: {exc}"))

        if count == 0:
            self.stdout.write(self.style.WARNING("No provisioned tenant databases matched the filter."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"School sync complete: created={summary['created']}, "
                f"updated={summary['updated']}, unchanged={summary['unchanged']}, "
                f"failures={len(failures)}."
            )
        )

        if failures:
            for line in failures:
                self.stderr.write(self.style.ERROR(line))
            raise CommandError("One or more tenant school sync operations failed.")
