"""
Management command to load default issue types and statuses.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.issues.models import IssueType, Status


class Command(BaseCommand):
    """Load default issue types and statuses."""

    help = "Load default issue types and statuses for CTrack"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reload even if data already exists",
        )

    def handle(self, *args, **options):
        force = options["force"]

        # Check if defaults already exist
        has_types = IssueType.objects.filter(project__isnull=True).exists()
        has_statuses = Status.objects.filter(project__isnull=True).exists()

        if has_types and has_statuses and not force:
            self.stdout.write(
                self.style.WARNING(
                    "Default data already exists. Use --force to reload."
                )
            )
            return

        # Load fixtures
        self.stdout.write("Loading default issue types and statuses...")

        call_command(
            "loaddata",
            "default_data.json",
            verbosity=0,
        )

        # Report results
        type_count = IssueType.objects.filter(project__isnull=True).count()
        status_count = Status.objects.filter(project__isnull=True).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {type_count} issue types and {status_count} statuses"
            )
        )
