from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
from .admin import admin_site
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.admin.views.decorators import staff_member_required
from .admin import admin_site
from .views import (
    get_timeslots,
    tournaments_bookings,
    full_court_bookings,
    individual_bookings,
)
from django.views.generic.base import RedirectView


@staff_member_required
def calendar_view(request):
    return admin_site.calendar_view(request)


urlpatterns = [
    path("", RedirectView.as_view(url="/login/", permanent=False), name="index"),
    # path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_request, name="login"),
    path("logout/", views.logout_request, name="logout"),
    path("reserve/<int:court_id>/", views.reserve_court, name="reserve"),
    path(
        "cancel_reservation/<int:reservation_id>/",
        views.cancel_reservation,
        name="cancel_reservation",
    ),
    path(
        "tournament/register/<int:tournament_id>/",
        views.tournament_registration,
        name="tournament_registration",
    ),  # URL for tournament registration
    path("profile/", views.profile, name="profile"),
    path("tournaments/", tournaments_bookings, name="tournaments_bookings"),
    path("full_court_bookings/", full_court_bookings, name="full_court_bookings"),
    path("individual_bookings/", individual_bookings, name="individual_bookings"),
    path("user_reservations/", views.user_reservations, name="user_reservations"),
    path("user_tournaments/", views.user_tournaments, name="user_tournaments"),
    path(
        "cancel_tournament/<int:registration_id>/",
        views.cancel_tournament_registration,
        name="cancel_tournament_registration",
    ),
    path("admin/my_calendar/", calendar_view, name="admin_calendar"),
    path("admin/", admin_site.urls),
    path(
        "password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("get_timeslots/", get_timeslots, name="get_timeslots"),
    path("calendar_data/", views.calendar_data, name="calendar_data"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
