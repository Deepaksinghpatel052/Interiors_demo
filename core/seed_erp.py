"""ERP demo data: leads across all stages, projects with milestones, tasks, designs and site updates."""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone

from core.demo_images import room_image, to_jpeg_bytes, to_thumb
from crm.models import Lead, LeadActivity
from studio.models import (ClientProject, DesignProposal, Milestone, ProjectSpace, ProposalComment, ProposalImage,
                           SiteUpdate, SiteUpdatePhoto, Task)

# name, mobile, city, source, stage, property, budget, style, note, days_ago
EXTRA_LEADS = [
    ("Rahul Verma", "9827098270", "Vijay Nagar, Indore", "referral", "won", "3bhk", "10_20", "modern", "Referred by the Agrawals. 3BHK in Vijay Nagar.", 75),
    ("Shalini Dubey", "9893312345", "Arera Colony, Bhopal", "instagram", "won", "villa", "20_40", "traditional", "Villa interiors, loves our jharokha work.", 120),
    ("Karan Mehra", "9425567890", "Scheme 54, Indore", "website", "won", "office", "20_40", "contemporary", "Office for 40 people.", 95),
    ("Ayesha Siddiqui", "9752245678", "MP Nagar, Bhopal", "walk_in", "won", "2bhk", "5_10", "minimal", "Minimal 2BHK, rented out later.", 140),
    ("Deepika Tomar", "9009112233", "City Centre, Gwalior", "referral", "won", "4bhk", "20_40", "luxury", "Luxury 4BHK duplex.", 160),
    ("Gaurav Bansal", "9584412345", "Nipania, Indore", "website", "won", "3bhk", "10_20", "contemporary", "Wants handover before Diwali.", 200),
    ("Tanvi Joshi", "9301234567", "Bhawarkuan, Indore", "instagram", "new", "1bhk", "under_5", "minimal", "Saw the Ivory Calm Bedroom reel.", 1),
    ("Mohit Sahu", "9977456123", "Kolar Road, Bhopal", "website", "new", "2bhk", "5_10", "", "Possession in 2 months.", 4),
    ("Fatima Ansari", "9826633221", "Khajrana, Indore", "ai_assistant", "new", "2bhk", "5_10", "modern", "Asked the assistant about kitchen timelines.", 0),
    ("Prakash Yadav", "9893776655", "Rau, Indore", "cost_estimator", "new", "3bhk", "10_20", "", "Estimator: 3 BHK, premium finish.", 2),
    ("Nidhi Kulkarni", "9424001122", "Shahpura, Bhopal", "instagram", "contacted", "3bhk", "10_20", "contemporary", "Wants a call after 6 PM.", 6),
    ("Harsh Vardhan", "9669001234", "Thatipur, Gwalior", "referral", "contacted", "villa", "above_40", "luxury", "Large villa, very particular about lighting.", 9),
    ("Sana Khan", "9755123987", "Palasia, Indore", "website", "proposal", "2bhk", "5_10", "modern", "Proposal sent for living + kitchen.", 14),
    ("Rajeev Nair", "9827654321", "Saket Nagar, Indore", "cost_estimator", "proposal", "3bhk", "10_20", "minimal", "Comparing two studios.", 18),
    ("Pallavi Singh", "9893456781", "Hoshangabad Road, Bhopal", "instagram", "lost", "2bhk", "under_5", "", "Went with a local carpenter on price.", 40),
    ("Vivek Pandey", "9425123459", "Morar, Gwalior", "website", "lost", "1bhk", "under_5", "", "Postponed the project.", 55),
    ("Meera Chawla", "9009345678", "Vijay Nagar, Indore", "ai_assistant", "contacted", "3bhk", "10_20", "traditional", "Chatted about pooja room designs.", 3),
    ("Arvind Goyal", "9584987654", "Sudama Nagar, Indore", "walk_in", "proposal", "retail", "10_20", "contemporary", "Jewellery showroom, 900 sq ft.", 21),
]

# lead name -> project definition
PROJECTS = {
    "Rahul Verma": dict(name="Verma Residence, Vijay Nagar", stage="approval", property_type="3bhk", area=1450,
                        budget=1650000, spent=210000, start=-60, target=60, style="modern",
                        spaces=[("Living & dining", 420, "TV wall, crockery unit, false ceiling"),
                                ("Master bedroom", 190, "Wardrobe, bed back panel, study table"),
                                ("Kitchen", 110, "L-shaped modular kitchen, tall unit"),
                                ("Kids' room", 140, "Bunk bed, study, toy storage")]),
    "Shalini Dubey": dict(name="Dubey Villa, Arera Colony", stage="execution", property_type="villa", area=3100,
                          budget=3400000, spent=1950000, start=-110, target=40, style="traditional"),
    "Karan Mehra": dict(name="Studio North Office", stage="ordering", property_type="office", area=3200,
                        budget=2800000, spent=600000, start=-80, target=50, style="contemporary"),
    "Ayesha Siddiqui": dict(name="Siddiqui 2BHK, MP Nagar", stage="design", property_type="2bhk", area=900,
                            budget=780000, spent=0, start=-12, target=75, style="minimal"),
    "Deepika Tomar": dict(name="Tomar Duplex, City Centre", stage="handover", property_type="4bhk", area=2600,
                          budget=4200000, spent=4050000, start=-150, target=5, style="luxury"),
    "Gaurav Bansal": dict(name="Bansal Home, Nipania", stage="completed", property_type="3bhk", area=1500,
                          budget=1500000, spent=1462000, start=-190, target=-20, style="contemporary"),
}

STAGE_PROGRESS = {"design": 0, "approval": 1, "ordering": 2, "execution": 3, "handover": 4, "completed": 5}
MILESTONES = [("Design & 3D", 14), ("Design approval", 21), ("Material ordering", 30), ("Execution", 75), ("Handover", 85)]


def _img(field, name, style, room, seed):
    field.save(name, ContentFile(to_jpeg_bytes(to_thumb(room_image(style, room, seed), 1000))), save=False)


def seed_erp(stdout):
    if ClientProject.objects.exists():
        return
    rnd = random.Random(11)
    now = timezone.now()
    today = timezone.localdate()
    owner = User.objects.get(username="owner")
    designer = User.objects.get(username="designer")
    client_user = User.objects.get(username="client")

    leads = {}
    for i, (name, mobile, city, source, stage, prop, budget, style, note, ago) in enumerate(EXTRA_LEADS):
        lead = Lead.objects.create(
            name=name, mobile=mobile, city=city, source=source, stage=stage, property_type=prop, budget_band=budget,
            style_preference=style, message=note, assigned_to=owner if i % 3 else designer,
            follow_up_date=(today + timedelta(days=rnd.randint(-3, 5))) if stage in ("contacted", "proposal") else None)
        created = now - timedelta(days=ago, hours=rnd.randint(1, 9))
        Lead.objects.filter(pk=lead.pk).update(created_at=created, updated_at=created + timedelta(hours=2))
        act = LeadActivity.objects.create(lead=lead, text=f"Enquiry received via {lead.get_source_display()}")
        LeadActivity.objects.filter(pk=act.pk).update(created_at=created)
        if stage not in ("new",):
            a2 = LeadActivity.objects.create(lead=lead, user=lead.assigned_to, text="Called and discussed requirements")
            LeadActivity.objects.filter(pk=a2.pk).update(created_at=created + timedelta(days=1))
        if stage == "lost":
            LeadActivity.objects.create(lead=lead, user=owner, text=note)
        leads[name] = lead
    # Spread the booking leads' creation dates over the last weeks too.
    for lead in Lead.objects.exclude(pk__in=[x.pk for x in leads.values()]):
        created = now - timedelta(days=rnd.randint(2, 20), hours=rnd.randint(1, 9))
        Lead.objects.filter(pk=lead.pk).update(created_at=created)
    stdout.write(f"Leads: {Lead.objects.count()}")

    for lead_name, p in PROJECTS.items():
        lead = leads[lead_name]
        start = today + timedelta(days=p["start"])
        project = ClientProject.objects.create(
            name=p["name"], lead=lead, client=client_user if lead_name == "Rahul Verma" else None,
            client_name=lead.name, client_mobile=lead.mobile, client_email=f"{lead.name.split()[0].lower()}@example.com",
            designer=designer if lead_name in ("Rahul Verma", "Ayesha Siddiqui", "Gaurav Bansal") else owner,
            stage=p["stage"], property_type=p["property_type"], site_address=lead.city, area_sqft=p["area"],
            start_date=start, target_date=today + timedelta(days=p["target"]),
            budget=Decimal(p["budget"]), actual_cost=Decimal(p["spent"]), notes=lead.message)
        done = STAGE_PROGRESS[p["stage"]]
        target = project.target_date
        for k, (title, _days) in enumerate(MILESTONES):
            # Finished milestones are spread between start and today; the current one is due soon,
            # later ones are spread up to the target date — so only a couple show as overdue.
            if k < done:
                status, due = "done", start + (today - start) * (k + 1) / (done + 1)
            elif k == done:
                status, due = "in_progress", today + timedelta(days=4 if k != 1 else -2)
            else:
                status = "pending"
                due = today + timedelta(days=4) + (target - today - timedelta(days=4)) * (k - done) / max(1, 5 - done)
            Milestone.objects.create(project=project, title=title, due_date=due, order=k, status=status,
                                     completed_on=due if status == "done" else None)
        for k, (n, area, scope) in enumerate(p.get("spaces", [])):
            ProjectSpace.objects.create(project=project, name=n, area_sqft=area, scope=scope, order=k)
        _seed_tasks(project, owner, designer, today, rnd)
        if p["stage"] in ("execution", "handover", "completed", "ordering"):
            _seed_updates(project, p["style"], owner, designer, rnd)
        stdout.write(f"  · {project.code} {project.name} ({project.get_stage_display()})")

    _seed_verma_designs(ClientProject.objects.get(lead=leads["Rahul Verma"]), designer, client_user)
    for p in ClientProject.objects.exclude(lead=leads["Rahul Verma"]).exclude(stage="design"):
        _seed_approved_design(p, PROJECTS[p.lead.name]["style"], designer)
    stdout.write(f"Projects: {ClientProject.objects.count()}, tasks: {Task.objects.count()}")


TASKS = [
    ("Final measurements of kitchen", -3, "done"), ("Share revised 3D of living room", -1, "todo"),
    ("Confirm laminate shades with client", 0, "doing"), ("Order hardware from Hettich dealer", 2, "todo"),
    ("Electrician site visit for points", 3, "todo"), ("Update site photos in portal", 1, "todo"),
    ("Check false ceiling levels", -2, "done"), ("Collect 40% design-approval payment", 4, "todo"),
    ("Get quartz countertop samples", 5, "todo"), ("Plumber visit for kitchen sink", 6, "todo"),
    ("Approve wardrobe internal layout", 2, "doing"), ("Book painter for second coat", 8, "todo"),
    ("Snag list walkthrough with client", 7, "todo"), ("Send lighting fixture options", 1, "done"),
]


def _seed_tasks(project, owner, designer, today, rnd):
    for title, offset, status in rnd.sample(TASKS, 4):
        offset = offset if offset >= 0 or status == "done" else rnd.choice([offset, 2])
        if project.stage == "completed":
            status = "done"
        Task.objects.create(project=project, title=title, due_date=today + timedelta(days=offset + rnd.randint(0, 1)),
                            assigned_to=rnd.choice([owner, designer]), status=status,
                            priority="high" if "payment" in title.lower() else "normal", created_by=owner,
                            completed_at=timezone.now() if status == "done" else None)


UPDATE_TEXTS = [
    "Carpentry started in the master bedroom. Wardrobe carcass is up.",
    "False ceiling framing done in the living room; electrical points marked.",
    "Laminates delivered and checked against the approved shades.",
    "Kitchen base units installed. Countertop measurement scheduled.",
]


def _seed_updates(project, style, owner, designer, rnd):
    rooms = ["living", "bedroom", "kitchen"] if project.property_type != "office" else ["office", "office", "office"]
    for k, text in enumerate(rnd.sample(UPDATE_TEXTS, 2)):
        u = SiteUpdate.objects.create(project=project, author=rnd.choice([owner, designer]), message=text,
                                      created_at=timezone.now() - timedelta(days=3 + k * 6))
        ph = SiteUpdatePhoto(update=u)
        _img(ph.image, f"site-{project.pk}-{k}.jpg", style, rooms[k % len(rooms)], 500 + project.pk * 7 + k)
        ph.save()


def _seed_verma_designs(project, designer, client_user):
    now = timezone.now()
    v1 = DesignProposal.objects.create(
        project=project, version=1, title="Living, dining & master bedroom — first concept", created_by=designer,
        notes="Two-tone TV wall in teal and oak, cove lighting, and a fluted wardrobe for the master bedroom.",
        status=DesignProposal.Status.CHANGES, shared_at=now - timedelta(days=12), decided_at=now - timedelta(days=10),
        decision_comment="We love the TV wall, but the teal feels a bit dark for our living room. Can we try a lighter shade? "
                         "Also please add a small pooja unit near the dining area.")
    imgs = []
    for k, (room, cap) in enumerate([("living", "Living room — TV wall"), ("living", "Dining corner"),
                                      ("bedroom", "Master bedroom")]):
        im = ProposalImage(proposal=v1, caption=cap, order=k)
        _img(im.image, f"verma-v1-{k}.jpg", "modern", room, 900 + k)
        im.save()
        imgs.append(im)
    c = ProposalComment.objects.create(proposal=v1, image=imgs[2], author=client_user,
                                       text="Can the wardrobe have a mirror on one shutter?")
    ProposalComment.objects.filter(pk=c.pk).update(created_at=now - timedelta(days=10, hours=2))
    c = ProposalComment.objects.create(proposal=v1, author=designer,
                                       text="Noted — v2 will use a lighter sage-teal and add a backlit pooja unit.")
    ProposalComment.objects.filter(pk=c.pk).update(created_at=now - timedelta(days=9))

    v2 = DesignProposal.objects.create(
        project=project, version=2, title="Living, dining & master bedroom — revised", created_by=designer,
        notes="Lighter sage-teal on the TV wall, backlit jaali pooja unit near dining, mirror shutter on the wardrobe.",
        status=DesignProposal.Status.SHARED, shared_at=now - timedelta(days=2))
    for k, (room, cap, style) in enumerate([("living", "Living room — lighter TV wall", "contemporary"),
                                             ("living", "Dining with pooja unit", "traditional"),
                                             ("bedroom", "Master bedroom with mirror shutter", "contemporary")]):
        im = ProposalImage(proposal=v2, caption=cap, order=k)
        _img(im.image, f"verma-v2-{k}.jpg", style, room, 950 + k)
        im.save()


def _seed_approved_design(project, style, designer):
    room = "office" if project.property_type == "office" else "living"
    p = DesignProposal.objects.create(
        project=project, version=1, title="Concept design", created_by=designer, notes="Layouts, mood board and 3D views.",
        status=DesignProposal.Status.APPROVED, shared_at=timezone.now() - timedelta(days=40),
        decided_at=timezone.now() - timedelta(days=37), decision_comment="Looks perfect, please go ahead.")
    for k in range(2):
        im = ProposalImage(proposal=p, caption=f"View {k + 1}", order=k)
        _img(im.image, f"design-{project.pk}-{k}.jpg", style, room if k == 0 else "bedroom", 700 + project.pk * 5 + k)
        im.save()
