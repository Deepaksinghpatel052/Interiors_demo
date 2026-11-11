from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("demo/", views.demo_home, name="home"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("portfolio/<slug:slug>/", views.project_detail, name="project_detail"),
    path("moodboard/<slug:slug>/", views.moodboard, name="moodboard"),
    path("style-quiz/", views.style_quiz, name="quiz"),
    path("style-quiz/result/", views.style_quiz_result, name="quiz_result"),
    path("estimate/", views.estimate, name="estimate"),
    path("api/estimate/", views.api_estimate, name="api_estimate"),
    path("services/", views.services, name="services"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("thank-you/", views.thanks, name="thanks"),
    path("faq/", views.faq, name="faq"),
    path("privacy/", views.privacy, name="privacy"),
    path("photo-credits/", views.photo_credits, name="credits"),
    path("why/", views.why, name="why"),
]
