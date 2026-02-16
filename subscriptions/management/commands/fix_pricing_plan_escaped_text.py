from django.core.management.base import BaseCommand
from django.db import transaction

from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Fix pricing plan description text that was saved with literal unicode escape sequences (e.g. \\u002D)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print which plans would be changed without saving",
        )

    def _decode_escaped_text(self, value: str) -> str:
        if not value:
            return value

        try:
            text = str(value)
            if "\\u" not in text and "\\n" not in text and "\\r" not in text and "\\t" not in text and "\\\\" not in text:
                return text

            import re

            def _repl(match):
                try:
                    return chr(int(match.group(1), 16))
                except Exception:
                    return match.group(0)

            text = re.sub(r"\\u([0-9a-fA-F]{4})", _repl, text)
            text = text.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
            text = text.replace("\\\\", "\\")
            return text
        except Exception:
            return value

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        qs = SubscriptionPlan.objects.all().only("id", "name", "description")
        changed = 0

        for plan in qs:
            before = plan.description or ""
            after = self._decode_escaped_text(before)

            if before != after:
                changed += 1
                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] Would update plan id={plan.id} name={plan.name!r}: {before!r} -> {after!r}"
                    )
                else:
                    plan.description = after
                    plan.save(update_fields=["description"])
                    self.stdout.write(
                        f"Updated plan id={plan.id} name={plan.name!r}"
                    )

        if dry_run:
            self.stdout.write(f"\nDry run complete. Plans that would change: {changed}")
        else:
            self.stdout.write(f"\nDone. Plans updated: {changed}")
