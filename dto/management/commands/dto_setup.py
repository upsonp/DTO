import os
from django.core.management import BaseCommand, call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Initialize database with migrations and load MPA data'

    def handle(self, *args, **options):
        self.stdout.write('Running migrations...')
        call_command('migrate')

        self.stdout.write('Loading MPA data...')
        scripts_dir = os.path.join(settings.BASE_DIR, 'scripts')
        # Add scripts directory to Python path
        import sys
        sys.path.append(scripts_dir)

        try:
            from setup import setup
            setup()
            self.stdout.write(self.style.SUCCESS('MPA data loaded successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading MPA data: {e}'))
            raise

        self.stdout.write(self.style.SUCCESS('Database initialization completed'))