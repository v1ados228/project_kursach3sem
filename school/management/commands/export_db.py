from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Экспортирует базу в читаемый JSON-файл."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="db_dump.json",
            help="Путь для JSON-файла экспорта.",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"]).resolve()
        with open(output_path, "w", encoding="utf-8") as file_obj:
            call_command("dumpdata", indent=2, stdout=file_obj)
        self.stdout.write(self.style.SUCCESS(f"Экспортировано в {output_path}"))
