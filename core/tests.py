import io
import json

from django.test import TestCase
from PIL import Image

from core import photos


class DemoPhotoTests(TestCase):
    def test_manifest_is_commercial_friendly(self):
        items = photos.manifest()
        self.assertGreater(len(items), 50)
        self.assertTrue(all(p["license"] in {"cc0", "pdm", "by", "by-sa"} for p in items))
        keys = {p["key"] for p in items}
        for spec in photos.PROJECT_PHOTOS.values():
            for key in [spec["cover"], *([spec["before"]] if spec.get("before") else []), *spec["gallery"]]:
                self.assertIn(key, keys)

    def test_clean_jpeg_rejects_non_images(self):
        with self.assertRaises(Exception):
            photos._clean_jpeg(b"<html><script>alert(1)</script></html>")

    def test_clean_jpeg_resizes_and_reencodes(self):
        buf = io.BytesIO()
        Image.new("RGBA", (3200, 1600), (10, 20, 30, 255)).save(buf, "PNG")
        out = Image.open(io.BytesIO(photos._clean_jpeg(buf.getvalue())))
        self.assertEqual((out.format, out.width, out.mode), ("JPEG", photos.MAX_WIDTH, "RGB"))

    def test_apply_without_downloads_keeps_records(self):
        # In tests MEDIA_ROOT is empty, so nothing is available and nothing breaks.
        self.assertEqual(photos.apply(), 0)
