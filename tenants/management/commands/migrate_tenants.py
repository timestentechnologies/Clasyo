from django.core.management.base import BaseCommand, CommandError

from tenants.drivers import get_tenant_database_driver
from tenants.school_sync import sync_tenant_school_record
from tenants.tenant_ops import (
    describe_tenant_backend,
    iter_provisioned_tenant_schools,
    registered_tenant_schools,
    run_tenant_migrations,
    tenant_database_is_provisioned,
)


class Command(BaseCommand):
    help = (
        "Run Django migrations on every provisioned tenant database discovered from "
        "the master School registry. Master (default) DATABASE_URL is unchanged."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            default=None,
            help='Migrate only this school slug (tenant database name).',
        )
        parser.add_argument(
            '--include-unprovisioned',
            action='store_true',
            help=(
                'Include every registered school even if the physical tenant database '
                'does not exist yet (default: skip unprovisioned tenants).'
            ),
        )
        parser.add_argument(
            '--no-sync-school',
            action='store_true',
            help='Do not upsert master School rows into tenant databases after migrating.',
        )

    def handle(self, *args, **options):
        slug = options.get('slug')
        skip_missing = not options.get('include_unprovisioned')
        sync_school = not options.get('no_sync_school')
        verbosity = options.get('verbosity', 1)

        if slug and not registered_tenant_schools(slug=slug).exists():
            raise CommandError(f"No School registered on master with slug '{slug}'.")

        self.stdout.write(f"Tenant backend: {describe_tenant_backend()}")

        driver = get_tenant_database_driver()
        failures: list[str] = []
        migrated = 0
        skipped = 0
        sync_summary = {'created': 0, 'updated': 0, 'unchanged': 0}

        schools = list(
            registered_tenant_schools(slug=slug)
            if not skip_missing
            else iter_provisioned_tenant_schools(slug=slug, skip_missing_database=True)
        )

        if not schools and slug:
            if skip_missing and not driver.database_exists(slug):
                self.stdout.write(
                    self.style.WARNING(
                        f"School '{slug}' is registered but tenant database does not exist yet; skipped."
                    )
                )
                return
            raise CommandError(f"No tenant database to migrate for slug '{slug}'.")

        for school in schools:
            db_alias = school.slug
            if skip_missing and not tenant_database_is_provisioned(db_alias):
                skipped += 1
                self.stdout.write(f"Skipping '{db_alias}' (tenant storage not provisioned).")
                continue

            self.stdout.write(f"Migrating tenant database '{db_alias}' ({school.name})...")
            try:
                run_tenant_migrations(db_alias, verbosity=max(0, verbosity - 1))
                migrated += 1
            except Exception as exc:
                failures.append(f"{db_alias}: migrate failed — {exc}")
                self.stderr.write(self.style.ERROR(f"  migrate failed: {exc}"))
                continue

            if sync_school:
                try:
                    result = sync_tenant_school_record(school, db_alias=db_alias)
                    sync_summary[result] = sync_summary.get(result, 0) + 1
                except Exception as exc:
                    failures.append(f"{db_alias}: school sync failed — {exc}")
                    self.stderr.write(self.style.ERROR(f"  school sync failed: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Tenant migrations finished: {migrated} migrated, {skipped} skipped, "
                f"{len(failures)} failed."
            )
        )
        if sync_school:
            self.stdout.write(
                f"School sync: created={sync_summary['created']}, "
                f"updated={sync_summary['updated']}, unchanged={sync_summary['unchanged']}."
            )

        if failures:
            for line in failures:
                self.stderr.write(self.style.ERROR(line))
            raise CommandError("One or more tenant databases failed migration or school sync.")
