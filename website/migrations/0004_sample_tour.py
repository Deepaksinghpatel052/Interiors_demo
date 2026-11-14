"""Load the sample “Aangan Residence” 360° tour (photos are copied into MEDIA_ROOT/tours/).

The tour only appears on the website once the 360° house tour extra feature is switched on.
"""
from django.db import migrations


def load(apps, schema_editor):
    from website.tour360 import seed_sample_tour
    seed_sample_tour(apps.get_model("website", "Tour"), apps.get_model("website", "TourRoom"),
                     apps.get_model("website", "TourHotspot"))


class Migration(migrations.Migration):
    dependencies = [("website", "0003_tour_tourroom_tourhotspot")]
    operations = [migrations.RunPython(load, migrations.RunPython.noop)]
