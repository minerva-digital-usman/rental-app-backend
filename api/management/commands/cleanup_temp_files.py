from django.conf import settings
from django.core.files.storage import default_storage
import os
import time
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Deletes temp driver license files older than 24 hours'

    def handle(self, *args, **kwargs):
        # Define the path to your temp directory (adjust if necessary)
        temp_dir = 'temp_driver_licenses/'

        # Get the current time
        current_time = time.time()

        # List files in the temp directory
        for file_name in default_storage.listdir(temp_dir)[1]:
            file_path = os.path.join(temp_dir, file_name)
            full_path = default_storage.path(file_path)

            if os.path.exists(full_path):
                # Get the file's last modified time
                file_mtime = os.path.getmtime(full_path)

                # If the file is older than 24 hours, delete it
                if current_time - file_mtime > 86400:  # 86400 seconds = 24 hours
                    default_storage.delete(file_path)
                    self.stdout.write(self.style.SUCCESS(f'Deleted file: {file_path}'))
            else:
                self.stdout.write(self.style.WARNING(f'File not found: {file_path}'))
