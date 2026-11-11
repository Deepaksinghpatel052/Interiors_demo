"""Client-portal demo content for the demo client's project (Verma Residence)."""
import io
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.template import Context, Template
from django.utils import timezone
from PIL import Image, ImageDraw
from xhtml2pdf import pisa

from core import photos
from core.models import StudioSettings
from studio.models import ClientProject, ClientRequest, ProjectDocument, SiteUpdate, SiteUpdatePhoto, Task

AGREEMENT = Template("""<html><head><meta charset="utf-8"><style>
@page { size: a4; margin: 2cm; }
body { font-family: Helvetica; font-size: 10pt; color: #111212; line-height: 1.5; }
h1 { font-size: 16pt; color: {{ s.accent_color }}; margin-bottom: 2pt; }
h2 { font-size: 11pt; margin: 12pt 0 4pt 0; }
.muted { color: #5B6470; }
</style></head><body>
<h1>Design &amp; Execution Agreement</h1>
<p class="muted">{{ s.legal_name }} · {{ s.address }} · GSTIN {{ s.gstin }}</p>
<p>This agreement is made on {{ date }} between <b>{{ s.legal_name }}</b> ("the Studio") and <b>{{ p.client_name }}</b> ("the Client")
for interior design and turnkey execution at <b>{{ p.site_address }}</b> (project {{ p.code }}).</p>
<h2>1. Scope</h2><p>Design, 3D views, material selection, carpentry, false ceiling, lighting, painting and soft furnishings as per the accepted quotation. Civil, plumbing and appliances are excluded unless listed.</p>
<h2>2. Timeline</h2><p>Target handover: {{ p.target_date }}. Dates depend on timely approvals and payments; the Studio will inform the Client of any change in advance.</p>
<h2>3. Payments</h2><p>As per the payment schedule in the accepted quotation. Each payment is acknowledged with a GST invoice.</p>
<h2>4. Approvals</h2><p>Designs are shared in the Client portal. Work on a room starts only after the Client approves its design there.</p>
<h2>5. Warranty</h2><p>1 year on workmanship and 5 years on modular furniture against manufacturing defects, from handover.</p>
<p style="margin-top:30pt">For {{ s.legal_name }} ____________________ &nbsp;&nbsp;&nbsp;&nbsp; Client ____________________</p>
<p class="muted" style="margin-top:20pt">Sample agreement for demonstration purposes.</p>
</body></html>""")


def _agreement_pdf(project):
    html = AGREEMENT.render(Context({"s": StudioSettings.load(), "p": project,
                                     "date": project.start_date.strftime("%d-%m-%Y")}))
    out = io.BytesIO()
    pisa.CreatePDF(html, dest=out)
    return out.getvalue()


def _floor_plan_png():
    """A simple furniture-layout drawing (illustrative) for the Documents tab."""
    W, H = 1400, 950
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    blue, ink, grey = (0, 129, 246), (17, 18, 18), (150, 160, 172)
    rooms = [("LIVING & DINING  22'0\" x 14'6\"", (60, 60, 760, 520)), ("KITCHEN  10'0\" x 9'0\"", (760, 60, 1100, 360)),
             ("MASTER BEDROOM  14'0\" x 12'0\"", (60, 520, 600, 890)), ("KIDS' ROOM  12'0\" x 11'0\"", (600, 520, 1100, 890)),
             ("BALCONY", (1100, 60, 1340, 360)), ("TOILET", (1100, 360, 1340, 620)), ("TOILET", (1100, 620, 1340, 890))]
    for label, box in rooms:
        d.rectangle(box, outline=ink, width=6)
        d.text((box[0] + 18, box[1] + 16), label, fill=ink)
    # furniture in blue
    d.rounded_rectangle((120, 380, 470, 470), radius=14, outline=blue, width=4)          # sofa
    d.rectangle((180, 250, 410, 330), outline=blue, width=3)                             # coffee table
    d.rectangle((90, 90, 110, 330), fill=blue)                                           # TV unit
    d.ellipse((560, 170, 720, 330), outline=blue, width=4)                               # dining
    d.rectangle((780, 80, 1080, 130), outline=blue, width=4)                             # kitchen counter
    d.rectangle((1030, 130, 1080, 340), outline=blue, width=4)
    d.rectangle((150, 620, 390, 860), outline=blue, width=4)                             # bed
    d.rectangle((80, 540, 580, 590), outline=blue, width=4)                              # wardrobe
    d.rectangle((640, 720, 820, 860), outline=blue, width=4)                             # kids bed
    d.rectangle((880, 540, 1080, 590), outline=blue, width=4)                            # kids wardrobe
    d.text((60, 905), "FURNITURE LAYOUT · VERMA RESIDENCE · NOT TO SCALE · ILLUSTRATIVE", fill=grey)
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return out.getvalue()


def seed_portal(stdout):
    project = ClientProject.objects.filter(client__username="client").first()
    if not project or project.documents.exists():
        return
    owner = User.objects.get(username="owner")
    designer = project.designer or owner
    client = project.client
    now = timezone.now()

    # Documents
    doc = ProjectDocument(project=project, title="Design & execution agreement", kind=ProjectDocument.Kind.AGREEMENT,
                          visible_to_client=True, uploaded_by=owner)
    doc.file.save("verma-agreement.pdf", ContentFile(_agreement_pdf(project)), save=False)
    doc.save()
    plan = ProjectDocument(project=project, title="Furniture layout — option B (approved)", kind=ProjectDocument.Kind.DRAWING,
                           visible_to_client=True, uploaded_by=designer)
    plan.file.save("verma-furniture-layout.png", ContentFile(_floor_plan_png()), save=False)
    plan.save()

    # Site updates (measurement + survey photos)
    for days, text, keys in [
        (40, "Site measurement done for all rooms. Electrical and plumbing points marked on the walls for your reference.", ["empty-04", "empty-09"]),
        (18, "Material board ready at the studio — laminate, quartz and fabric samples for your living room and kitchen.", ["kitchen-26", "living-43"]),
    ]:
        u = SiteUpdate.objects.create(project=project, author=designer, message=text, created_at=now - timedelta(days=days))
        for i, key in enumerate(keys):
            if photos.available(key):
                ph = SiteUpdatePhoto(update=u)
                ph.image.save(f"verma-update-{days}-{i}.jpg", photos.as_file(key, 1200), save=False)
                ph.save()

    # A request the client raised earlier, already resolved
    task = Task.objects.create(project=project, title="Client request: Add a shoe rack near the entrance",
                               notes="Space of about 3 ft next to the main door.", assigned_to=designer, from_client=True,
                               status=Task.Status.DONE, completed_at=now - timedelta(days=8), created_by=client)
    req = ClientRequest.objects.create(project=project, raised_by=client, title="Add a shoe rack near the entrance",
                                       description="Space of about 3 ft next to the main door.",
                                       status=ClientRequest.Status.RESOLVED, task=task)
    ClientRequest.objects.filter(pk=req.pk).update(created_at=now - timedelta(days=12))
    stdout.write("Client portal: agreement, layout drawing, 2 site updates, 1 resolved request")
