from pathlib import Path
from datetime import datetime

import pandas as pd
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Export model data from the school app to an Excel (.xlsx) file."

    def add_arguments(self, parser):
        parser.add_argument("model", type=str, help="Model name from the school app (e.g. Course)")
        parser.add_argument(
            "--fields",
            type=str,
            default="",
            help="Comma-separated list of fields to export (e.g. title,price,start_date)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Export all concrete fields from the model.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Output .xlsx path (default: <model>.xlsx)",
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        model = apps.get_model("school", model_name)
        if model is None:
            raise CommandError(f"Model '{model_name}' not found in app 'school'.")

        fields_arg = options["fields"].strip()
        export_all = options["all"]
        output_path = options["output"].strip()

        if export_all and fields_arg:
            raise CommandError("Use either --all or --fields, not both.")

        if export_all:
            fields = [f.name for f in model._meta.fields]
        elif fields_arg:
            fields = [f.strip() for f in fields_arg.split(",") if f.strip()]
        else:
            raise CommandError("Specify --all or --fields to select export columns.")

        model_field_names = {f.name for f in model._meta.fields}
        invalid = [f for f in fields if f not in model_field_names]
        if invalid:
            raise CommandError(f"Unknown field(s) for {model_name}: {', '.join(invalid)}")

        queryset = model.objects.all().values(*fields)
        rows = list(queryset)
        for row in rows:
            for key, value in row.items():
                if isinstance(value, datetime) and timezone.is_aware(value):
                    row[key] = timezone.make_naive(value)
        df = pd.DataFrame(rows)

        if not output_path:
            output_path = f"{model_name.lower()}.xlsx"
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        df.to_excel(output, index=False)
        self.stdout.write(self.style.SUCCESS(f"Exported {model_name} to {output}"))
