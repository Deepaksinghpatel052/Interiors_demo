"""DEVNIXPLUS product landing page (the default home page in demo mode) + enquiry form."""
from django import forms
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from website.forms import clean_indian_mobile

from .models import ProductEnquiry
from .modules import MODULES
from .ratelimit import client_ip, hit

FAQS = [
    ("Do I need any technical knowledge?",
     "No. If you can use WhatsApp and Instagram, you can use this. We set everything up, load your content and train you "
     "and your team in a short session."),
    ("Can I start with only a website and add the rest later?",
     "Yes. Every module can be switched on later in the same system — the website, ERP, client portal, automation and "
     "AI assistant all share the same data, so nothing has to be rebuilt."),
    ("Will it show my studio’s name, logo and colours?",
     "Yes. Your name, logo and brand colours appear on the website, the studio dashboard, the client portal and every "
     "quotation and invoice PDF. Clients never see our name."),
    ("Does it work on a phone?",
     "Yes. The website, the owner dashboard and the client portal are designed for phones first, so you can check leads "
     "or record a payment from site."),
    ("Do my clients need to install an app?",
     "No. Clients open their private portal in the phone’s browser with their own login — no app download needed."),
    ("Are WhatsApp messages sent automatically?",
     "In this version every message is written for you and opens in your own WhatsApp with one tap. Fully automatic "
     "sending through the WhatsApp Business API is available as an add-on."),
    ("How does the AI assistant avoid wrong answers?",
     "It only answers from information you approve — your FAQs, services, policies and guides — and shows the source of "
     "every answer. If it does not know, it offers WhatsApp or a consultation instead of guessing."),
    ("Is my data private?",
     "Each studio has its own system. Team members and clients have separate logins, and a client can only see their "
     "own project."),
    ("How much does it cost?",
     "It depends on the modules you choose. Send the form below and we will suggest a package for your studio, with easy "
     "payment options."),
]

MODULE_CHOICES = [(k, label) for k, label, _, _ in MODULES] + [("complete", "Complete system"), ("not_sure", "Not sure yet")]


class ProductEnquiryForm(forms.ModelForm):
    modules = forms.MultipleChoiceField(label="What are you interested in?", choices=MODULE_CHOICES, required=False,
                                        widget=forms.CheckboxSelectMultiple)
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))  # honeypot

    class Meta:
        model = ProductEnquiry
        fields = ["name", "mobile", "studio_name", "city", "email", "team_size", "modules", "contact_pref", "message"]
        labels = {"name": "Your name", "mobile": "Mobile / WhatsApp", "studio_name": "Studio name", "team_size": "Team size",
                  "contact_pref": "Best way to reach you", "message": "Anything you'd like us to know?"}
        widgets = {"message": forms.Textarea(attrs={"rows": 3, "placeholder": "e.g. We get most enquiries on Instagram and "
                                                                              "make quotations in Excel."}),
                   "contact_pref": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ph = {"name": "e.g. Rohit Sharma", "mobile": "10-digit mobile", "studio_name": "e.g. Sharma Interiors",
              "city": "e.g. Indore", "email": "Optional"}
        self.fields["team_size"].choices = [("", "Select")] + list(ProductEnquiry.TeamSize.choices)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                continue
            w.attrs.setdefault("class", "form-select" if isinstance(w, forms.Select) else "form-control")
            if name in ph:
                w.attrs.setdefault("placeholder", ph[name])
        self.fields["mobile"].widget.attrs.update({"inputmode": "tel", "autocomplete": "tel"})
        self.fields["name"].widget.attrs["autocomplete"] = "name"
        for name in ("name", "mobile"):
            self.fields[name].widget.attrs["required"] = True

    def clean_mobile(self):
        return clean_indian_mobile(self.cleaned_data["mobile"])

    def clean_message(self):
        return (self.cleaned_data.get("message") or "")[:2000]

    def full_clean(self):
        super().full_clean()
        for name in getattr(self, "_errors", None) or {}:
            if name in self.fields:
                w = self.fields[name].widget
                w.attrs["class"] = (w.attrs.get("class", "") + " is-invalid").strip()


def landing(request):
    from website.models import Package
    sent = request.GET.get("sent") == "1"
    initial = {}
    pre = request.GET.get("module")
    if pre in dict(MODULE_CHOICES):
        initial["modules"] = [pre]
    form = ProductEnquiryForm(request.POST or None, initial=initial)
    if request.method == "POST":
        if request.POST.get("website"):                      # bot filled the hidden field: pretend success
            return redirect(reverse("landing") + "?sent=1#enquire-form")
        if not hit(f"enq:{client_ip(request)}", 5, 3600):
            messages.error(request, "Too many enquiries from this connection. Please message us on WhatsApp instead.")
        elif form.is_valid():
            enq = form.save(commit=False)
            enq.modules = form.cleaned_data["modules"]
            enq.ip = client_ip(request) if client_ip(request) != "unknown" else None
            enq.save()
            request.session["enquiry_name"] = enq.name.split()[0]
            return redirect(reverse("landing") + "?sent=1#enquire-form")
        else:
            messages.error(request, "Please check the highlighted fields.")
    first = request.session.get("enquiry_name", "") if sent else ""
    return render(request, "core/landing.html", {
        "form": form, "sent": sent, "first_name": first,
        "packages": Package.objects.filter(is_active=True), "faqs": FAQS,
        "devnix_wa_text": f"Hi {settings.DEVNIX_NAME}, I'm an interior designer and I'd like a demo of the studio system.",
    })


def root(request):
    """`/`: the product landing page when LANDING_PAGE is on; otherwise the studio's own home page."""
    if settings.LANDING_PAGE:
        return landing(request)
    from .models import StudioSettings
    if not StudioSettings.load().module_website:
        return redirect("core:login")
    from website.views import home
    return home(request)
