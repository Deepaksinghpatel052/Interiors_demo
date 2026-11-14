"""Sample tour: replace the loft kitchen with the rendered modular kitchen (only if the sample is unchanged)."""
from django.db import migrations


def swap(apps, schema_editor):
    from website.tour360 import replace_sample_room
    replace_sample_room(apps.get_model("website", "Tour"), apps.get_model("website", "TourRoom"),
                        apps.get_model("website", "TourHotspot"), "kitchen", "kitchen-360.jpg")


class Migration(migrations.Migration):
    dependencies = [("website", "0004_sample_tour")]
    operations = [migrations.RunPython(swap, migrations.RunPython.noop)]
