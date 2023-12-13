from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import (
    SignUpForm,
    TournamentRegistrationForm,
    UserUpdateForm,
    ProfileUpdateForm,
)
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, time, date
from collections import defaultdict
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.http import JsonResponse
from django.core.serializers import serialize
import json
from django.db.models import Count, Q, Sum, Case, When, IntegerField, F

# Create your views here.
from .models import (
    Court,
    Reservation,
    TimeSlot,
    Tournament,
    TournamentRegistration,
    Profile,
    ReservationTimeSlotMaster,
)  # Import your Court model


def home(request):
    selected_date_str = request.GET.get("date")
    selected_gender = request.GET.get("gender", "").lower()
    selected_level = request.GET.get("level", "").lower()
    selected_part_of_day = request.GET.get("part_of_day", "").lower()

    # New selectors for full court
    full_court_selected_date_str = request.GET.get("full_court_date")
    full_court_selected_part_of_day = request.GET.get(
        "full_court_part_of_day", ""
    ).lower()

    selected_date = (
        datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        if selected_date_str
        else timezone.now().date()
    )

    full_court_selected_date = (
        datetime.strptime(full_court_selected_date_str, "%Y-%m-%d").date()
        if full_court_selected_date_str
        else timezone.now().date()
    )

    start_of_week = selected_date - timedelta(days=(selected_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)

    available_courts = Court.get_available_courts()

    morning_end = time(12, 0)
    afternoon_start = time(12, 1)
    afternoon_end = time(18, 0)
    evening_start = time(18, 1)

    courts_with_slots = []  # For individual slot bookings
    full_courts_with_slots = []  # For full court bookings

    for court in available_courts:
        timeslots_with_availability = []  # Stays the same for individual slots
        full_court_timeslots = []  # New list for full court timeslots

        timeslots_query = TimeSlot.objects.filter(
            template__court=court, date__gte=start_of_week, date__lte=end_of_week
        )

        if selected_gender:
            timeslots_query = timeslots_query.filter(
                template__player_type__name=selected_gender
            )
        if selected_level:
            timeslots_query = timeslots_query.filter(
                template__level__name=selected_level
            )
        if selected_part_of_day:
            if selected_part_of_day == "morning":
                timeslots_query = timeslots_query.filter(
                    template__start_time__lte=morning_end
                )
            elif selected_part_of_day == "afternoon":
                timeslots_query = timeslots_query.filter(
                    template__start_time__gte=afternoon_start,
                    template__end_time__lte=afternoon_end,
                )
            elif selected_part_of_day == "evening":
                timeslots_query = timeslots_query.filter(
                    template__start_time__gte=evening_start
                )

        timeslots = timeslots_query.select_related(
            "template__level", "template__player_type"
        ).order_by("template__start_time")

        for timeslot in timeslots_query:
            # Logic for individual slot bookings
            if timeslot.template.booking_type == "individual":
                current_reservations = Reservation.objects.filter(
                    timeslot=timeslot, is_active=True
                )
                total_reserved_slots = sum(
                    reservation.slot_count for reservation in current_reservations
                )
                available_slots = max(court.max_players - total_reserved_slots, 0)
                slot_range = list(range(1, available_slots + 1))
                timeslots_with_availability.append(
                    (timeslot, available_slots, slot_range)
                )

            # Logic for full court bookings
            elif (
                timeslot.template.booking_type == "full_court"
                and timeslot.is_full_court_booked == False
            ):
                full_court_timeslots.append(timeslot)

        if timeslots_with_availability:
            courts_with_slots.append(
                {"court": court, "slots": timeslots_with_availability}
            )
        if full_court_timeslots:
            full_courts_with_slots.append(
                {"court": court, "full_court_slots": full_court_timeslots}
            )
    # Filter active reservations for the logged-in user (if authenticated)
    if request.user.is_authenticated:
        active_reservations = request.user.reservation_set.filter(is_active=True)
        user_tournament_registrations = TournamentRegistration.objects.filter(
            user=request.user, tournament__start_date__gte=timezone.now()
        ).select_related("tournament")
    else:
        active_reservations = []
        user_tournament_registrations = []

    three_months_later = timezone.now() + timedelta(days=90)
    tournaments = Tournament.objects.filter(
        start_date__gte=timezone.now(), start_date__lte=three_months_later
    ).order_by("start_date")

    for tournament in tournaments:
        tournament.is_full = tournament.is_full()
        tournament.available_slots = tournament.available_slots()

    context = {
        "courts_with_slots": courts_with_slots,
        "selected_date": selected_date_str,
        "is_gender_men": selected_gender == "men",
        "is_gender_women": selected_gender == "women",
        "is_gender_mixed": selected_gender == "mixed",
        "is_level_beginner": selected_level == "beginner",
        "is_level_intermediate": selected_level == "intermediate",
        "is_level_advanced": selected_level == "advanced",
        "is_part_of_day_morning": selected_part_of_day == "morning",
        "is_part_of_day_afternoon": selected_part_of_day == "afternoon",
        "is_part_of_day_evening": selected_part_of_day == "evening",
        "full_court_selected_date": full_court_selected_date_str,
        "is_full_court_part_of_day_morning": full_court_selected_part_of_day
        == "morning",
        "is_full_court_part_of_day_afternoon": full_court_selected_part_of_day
        == "afternoon",
        "is_full_court_part_of_day_evening": full_court_selected_part_of_day
        == "evening",
        "active_reservations": active_reservations,
        "tournaments": tournaments,
        "user_tournament_registrations": user_tournament_registrations,
        "courts_with_slots": courts_with_slots,
        "full_courts_with_slots": full_courts_with_slots,
    }

    return render(request, "home.html", context)


def full_court_bookings(request):
    full_court_selected_date_str = request.GET.get("full_court_date")
    full_court_selected_part_of_day = request.GET.get(
        "full_court_part_of_day", ""
    ).lower()

    if full_court_selected_date_str:
        full_court_selected_date = datetime.strptime(
            full_court_selected_date_str, "%Y-%m-%d"
        ).date()
    else:
        # Get the first available date for a timeslot if no date is selected
        next_available_timeslot = (
            TimeSlot.objects.filter(
                template__booking_type="full_court",
                date__gte=timezone.now().date(),
                is_full_court_booked=False,
            )
            .order_by("date")
            .first()
        )
        full_court_selected_date = (
            next_available_timeslot.date
            if next_available_timeslot
            else timezone.now().date()
        )

    # Format the date as a string in YYYY-MM-DD format for the template
    full_court_selected_date_str = full_court_selected_date.strftime("%Y-%m-%d")

    available_courts = Court.get_available_courts()

    morning_end = time(12, 0)
    afternoon_start = time(12, 1)
    afternoon_end = time(18, 0)
    evening_start = time(18, 1)

    full_courts_with_slots = []

    for court in available_courts:
        full_court_timeslots = []

        timeslots_query = TimeSlot.objects.filter(
            template__court=court,
            date=full_court_selected_date,
            template__booking_type="full_court",
        )

        timeslots = timeslots_query.select_related(
            "template__level", "template__player_type"
        ).order_by("template__start_time")

        for timeslot in timeslots:
            if not timeslot.is_full_court_booked:
                full_court_timeslots.append(timeslot)

        if full_court_timeslots:
            full_courts_with_slots.append(
                {"court": court, "full_court_slots": full_court_timeslots}
            )

    context = {
        "full_courts_with_slots": full_courts_with_slots,
        "full_court_selected_date": full_court_selected_date_str,
        "is_full_court_part_of_day_morning": full_court_selected_part_of_day
        == "morning",
        "is_full_court_part_of_day_afternoon": full_court_selected_part_of_day
        == "afternoon",
        "is_full_court_part_of_day_evening": full_court_selected_part_of_day
        == "evening",
        "full_courts_with_slots": full_courts_with_slots,
    }

    return render(request, "full_court_bookings.html", context)


def individual_bookings(request):
    selected_date_str = request.GET.get("date")
    selected_gender = request.GET.get("gender", "").lower()
    selected_level = request.GET.get("level", "").lower()
    selected_part_of_day = request.GET.get("part_of_day", "").lower()

    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    else:
        # Get the first available date for a timeslot if no date is selected
        next_available_timeslot = (
            TimeSlot.objects.filter(
                template__booking_type="individual",
                date__gte=timezone.now().date(),
            )
            .annotate(
                booked_slots=Count("reservation", filter=Q(reservation__is_active=True))
            )
            .filter(booked_slots__lt=F("template__court__max_players"))
            .order_by("date")
            .first()
        )
        selected_date = (
            next_available_timeslot.date
            if next_available_timeslot
            else timezone.now().date()
        )

    available_courts = Court.get_available_courts()

    morning_end = time(12, 0)
    afternoon_start = time(12, 1)
    afternoon_end = time(18, 0)
    evening_start = time(18, 1)

    courts_with_slots = []

    for court in available_courts:
        timeslots_with_availability = []

        timeslots_query = (
            TimeSlot.objects.filter(
                template__court=court,
                date=selected_date,
                template__booking_type="individual",
            )
            .annotate(
                booked_slots=Sum(
                    Case(
                        When(
                            reservation__is_active=True, then="reservation__slot_count"
                        ),
                        default=0,
                        output_field=IntegerField(),
                    )
                )
            )
            .exclude(booked_slots__gte=F("template__court__max_players"))
        )

        if selected_gender:
            timeslots_query = timeslots_query.filter(
                template__player_type__name=selected_gender
            )
        if selected_level:
            timeslots_query = timeslots_query.filter(
                template__level__name=selected_level
            )
        if selected_part_of_day:
            if selected_part_of_day == "morning":
                timeslots_query = timeslots_query.filter(
                    template__start_time__lte=morning_end
                )
            elif selected_part_of_day == "afternoon":
                timeslots_query = timeslots_query.filter(
                    template__start_time__gte=afternoon_start,
                    template__end_time__lte=afternoon_end,
                )
            elif selected_part_of_day == "evening":
                timeslots_query = timeslots_query.filter(
                    template__start_time__gte=evening_start
                )

        timeslots = timeslots_query.select_related(
            "template__level", "template__player_type"
        ).order_by("template__start_time")

        for timeslot in timeslots:
            current_reservations = Reservation.objects.filter(
                timeslot=timeslot, is_active=True
            )
            total_reserved_slots = sum(
                reservation.slot_count for reservation in current_reservations
            )
            available_slots = max(court.max_players - total_reserved_slots, 0)

            slot_range = list(range(1, available_slots + 1))

            # Fetch the profiles of users who have reserved this slot
            reserved_profiles = [
                res.user.profile for res in current_reservations if res.user.profile
            ]

            timeslots_with_availability.append(
                (timeslot, available_slots, slot_range, reserved_profiles)
            )

        if timeslots_with_availability:
            courts_with_slots.append(
                {
                    "court": court,
                    "slots": timeslots_with_availability,
                    "max_players": court.max_players,
                }
            )

    context = {
        "courts_with_slots": courts_with_slots,
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "is_gender_men": selected_gender == "men",
        "is_gender_women": selected_gender == "women",
        "is_gender_mixed": selected_gender == "mixed",
        "is_level_beginner": selected_level == "beginner",
        "is_level_intermediate": selected_level == "intermediate",
        "is_level_advanced": selected_level == "advanced",
        "is_part_of_day_morning": selected_part_of_day == "morning",
        "is_part_of_day_afternoon": selected_part_of_day == "afternoon",
        "is_part_of_day_evening": selected_part_of_day == "evening",
        "courts_with_slots": courts_with_slots,
    }

    return render(request, "individual_bookings.html", context)


def tournaments_bookings(request):
    three_months_later = timezone.now() + timedelta(days=90)
    tournaments = Tournament.objects.filter(
        start_date__gte=timezone.now(), start_date__lte=three_months_later
    ).order_by("start_date")

    for tournament in tournaments:
        tournament.is_full = tournament.is_full()
        tournament.available_slots = tournament.available_slots()

    context = {
        "tournaments": tournaments,
    }

    return render(request, "tournaments_bookings.html", context)


def profile(request):
    return render(request, "profile.html")


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect("login")  # Redirect to a home page
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form, "hide_navbar": True})


def login_request(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("full_court_bookings")  # Redirect to a home page
            else:
                form = AuthenticationForm()
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form, "hide_navbar": True})


def logout_request(request):
    logout(request)
    return redirect("full_court_bookings")  # Redirect to a login page


@login_required
def reserve_court(request, court_id):
    court = get_object_or_404(Court, id=court_id)
    total_reserved_slots = 0
    booking_made = False  # Flag to track if any booking was made
    email_should_be_sent = False  # Flag to determine if email should be sent
    new_reservations = []  # Initialize the variable
    last_reservation = None  # Track the last reservation for email sending

    if request.method == "POST":
        if "book_full_court" in request.POST:
            timeslot_id = request.POST.get("full_court_timeslot_id")

            timeslot = get_object_or_404(
                TimeSlot, id=timeslot_id, template__booking_type="full_court"
            )
            # Check if all slots are free before proceeding
            if Reservation.objects.filter(timeslot=timeslot, is_active=True).exists():
                messages.error(
                    request,
                    "Cannot book full court as some slots are already reserved.",
                )
                return redirect("full_court_bookings.html")

            timeslot.is_full_court_booked = True
            timeslot.save()

            master_reservation = ReservationTimeSlotMaster.objects.create(
                user=request.user,
                timeslot=timeslot,
                total_slot_count=4,
                total_price=timeslot.full_court_price,
                is_active=True,
                is_full_court=True,
            )

            new_reservation = Reservation.objects.create(
                user=request.user,
                timeslot=timeslot,
                slot_count=4,
                slot_number=1,
                is_active=True,
                master_reservation_timeslot=master_reservation,
                was_full_court_booking=True,
            )

            new_reservation.save(send_email=True)  # Send email for full court booking
            booking_made = True

            if booking_made:
                messages.success(request, "Full court booking successful.")
                return redirect(
                    "full_court_bookings"
                )  # Redirect to full court bookings page
            else:
                messages.error(request, "No full court booking was made.")
                return redirect(
                    "full_court_bookings"
                )  # Stay on full court bookings page if error
        else:
            for key, value in request.POST.items():
                if key.startswith("slot_count_"):
                    timeslot_id = key.replace("slot_count_", "")
                    selected_slot_count = int(value)

                    if selected_slot_count > 0:
                        timeslot = get_object_or_404(TimeSlot, id=timeslot_id)

                        # Retrieve an active master reservation or create a new one if none exists
                        (
                            master_reservation,
                            created,
                        ) = ReservationTimeSlotMaster.objects.get_or_create(
                            user=request.user,
                            timeslot=timeslot,
                            is_active=True,
                            defaults={
                                "total_slot_count": 0,
                                "total_price": 0,
                                "is_full_court": False,
                            },
                        )

                        active_reservations = Reservation.objects.filter(
                            timeslot=timeslot, is_active=True
                        )

                        occupied_slots = [
                            reservation.slot_number
                            for reservation in active_reservations
                        ]
                        available_slots = set(range(1, court.max_players + 1)) - set(
                            occupied_slots
                        )

                        if len(available_slots) >= selected_slot_count:
                            for _ in range(selected_slot_count):
                                assigned_slot_number = available_slots.pop()
                                new_reservation = Reservation.objects.create(
                                    user=request.user,
                                    timeslot=timeslot,
                                    slot_count=1,
                                    slot_number=assigned_slot_number,
                                    is_active=True,
                                    master_reservation_timeslot=master_reservation,
                                )
                                new_reservations.append(new_reservation)
                                total_reserved_slots += 1

                            # Update the total slot count for master reservation
                            master_reservation.total_slot_count += total_reserved_slots
                            master_reservation.total_price += (
                                timeslot.individual_slot_price * total_reserved_slots
                            )
                            master_reservation.save()
                            # Update the master reservation
                            master_reservation.update_on_reservation_change()
            if new_reservations:
                new_reservations[-1].save(
                    send_email=True, total_slots_booked=total_reserved_slots
                )
                booking_made = True

            if booking_made:
                messages.success(request, "Individual booking successful.")
                return redirect(
                    "individual_bookings"
                )  # Redirect to individual bookings page
            else:
                messages.error(request, "No individual booking was made.")
                return redirect(
                    "individual_bookings"
                )  # Stay on individual bookings page if error

    # If not a POST request, redirect based on court type
    court_type = (
        Court.objects.filter(id=court_id).values_list("type", flat=True).first()
    )
    if court_type == "full_court":
        return redirect("full_court_bookings")
    else:
        return redirect("individual_bookings")


@login_required
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    # Add a context variable for the booking type
    booking_type = (
        "full_court_bookings"
        if reservation.master_reservation_timeslot.is_full_court
        else "individual_bookings"
    )

    if request.method == "POST":
        is_full_court = reservation.master_reservation_timeslot.is_full_court

        if reservation.master_reservation_timeslot.is_full_court:
            # Cancel all reservations associated with the master reservation
            linked_reservations = Reservation.objects.filter(
                master_reservation_timeslot=reservation.master_reservation_timeslot
            )
            for res in linked_reservations:
                res.is_active = False
                res.canceled_on = timezone.now()
                res.save()

            reservation.master_reservation_timeslot.cancel_master_reservation()
        else:
            reservation.is_active = False
            reservation.canceled_on = timezone.now()
            reservation.save()
            reservation.master_reservation_timeslot.update_on_reservation_change()
        # Call the method to send cancellation emails
        reservation.send_cancellation_email()

        messages.success(request, "Reservation canceled successfully.")

        if is_full_court:
            return redirect(
                "full_court_bookings"
            )  # Redirect to full court bookings page
        else:
            return redirect(
                "individual_bookings"
            )  # Redirect to individual bookings page
    else:
        # Display confirmation message for GET request
        return render(
            request,
            "confirm_cancellation.html",
            {"reservation": reservation, "booking_type": booking_type},
        )


@login_required
def tournament_registration(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    if request.method == "POST":
        form = TournamentRegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.user = request.user
            registration.tournament = (
                tournament  # Set the tournament for the registration
            )
            registration.save()
            # Redirect to a success page or home page
            return redirect("tournaments_bookings")
    else:
        # Prepopulate the tournament field in the form
        form = TournamentRegistrationForm(initial={"tournament": tournament})

    return render(
        request,
        "tournament_registration.html",
        {"form": form, "tournament": tournament},
    )


@login_required
def cancel_tournament_registration(request, registration_id):
    registration = get_object_or_404(
        TournamentRegistration, id=registration_id, user=request.user
    )

    if request.method == "POST":
        if registration.can_cancel():
            registration.cancel_registration()
            messages.success(request, "Tournament registration canceled successfully.")
        else:
            messages.error(
                request,
                "Cancellation deadline has passed. Please contact the organizer.",
            )
        return redirect("tournaments_bookings")
    else:
        # Display confirmation message
        return render(
            request,
            "confirm_tournament_cancellation.html",
            {"registration": registration},
        )


def user_reservations(request):
    if request.user.is_authenticated:
        active_reservations = request.user.reservation_set.filter(is_active=True)
    else:
        active_reservations = []

    return render(
        request, "user_reservations.html", {"active_reservations": active_reservations}
    )


def user_tournaments(request):
    if request.user.is_authenticated:
        user_tournament_registrations = TournamentRegistration.objects.filter(
            user=request.user, tournament__start_date__gte=timezone.now()
        ).select_related("tournament")
    else:
        user_tournament_registrations = []

    return render(
        request,
        "user_tournaments.html",
        {"user_tournament_registrations": user_tournament_registrations},
    )


@login_required
def profile(request):
    # Create a profile if it does not exist
    Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, request.FILES, instance=request.user.profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            # Redirect or add a success message
            messages.success(
                request, "Profile updated successfully."
            )  # Add success message
            return redirect(
                "profile"
            )  # Redirect to the profile page or any other page you prefer
           
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    return render(
        request, "profile.html", {"user_form": user_form, "profile_form": profile_form}
    )


def get_date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def get_timeslots(request):
    court_type = request.GET.get("court_type")
    date_str = request.GET.get("date")
    level_id = request.GET.get("level")
    player_type_id = request.GET.get("player_type")

    if court_type not in ["full_court", "individual"]:
        return JsonResponse({"error": "Invalid court type"}, status=400)

    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"error": "Invalid date format"}, status=400)

        timeslots = TimeSlot.objects.filter(
            template__booking_type=court_type, date=date
        )

        if court_type == "individual":
            # Filters for individual booking type
            level_id = int(level_id) if level_id else None
            player_type_id = int(player_type_id) if player_type_id else None

            if level_id:
                timeslots = timeslots.filter(template__level_id=level_id)
            if player_type_id:
                timeslots = timeslots.filter(template__player_type_id=player_type_id)

        elif court_type == "full_court":
            # Exclude fully booked full court timeslots
            timeslots = timeslots.exclude(is_full_court_booked=True)

    else:
        timeslots = []

    timeslots_data = []
    for timeslot in timeslots:
        template = timeslot.template
        timeslot_data = {
            "pk": timeslot.pk,
            "court_name": template.court.name if template.court else "",
            "start_time": template.start_time.strftime("%H:%M"),
            "end_time": template.end_time.strftime("%H:%M"),
            "booking_type": template.get_booking_type_display(),
        }

        if template.booking_type == "individual":
            reserved_slots = Reservation.objects.filter(
                timeslot=timeslot, is_active=True
            ).aggregate(total_reserved=Count("id"))["total_reserved"]

            max_slots = template.court.max_players
            available_slots = (
                max_slots - reserved_slots if reserved_slots else max_slots
            )
            timeslot_data.update(
                {
                    "available_slots": available_slots,
                    "player_type": template.player_type.name
                    if template.player_type
                    else "",
                    "level": template.level.name if template.level else "",
                }
            )

        timeslots_data.append(timeslot_data)

    return JsonResponse({"timeslots": json.dumps(timeslots_data)})


def calendar_data(request):
    # Fetching all timeslots within a reasonable range (e.g., next 60 days)
    end_date = datetime.now().date() + timedelta(days=60)
    timeslots = (
        TimeSlot.objects.filter(date__gte=datetime.now().date(), date__lte=end_date)
        .annotate(
            booked_slots=Sum(
                Case(
                    When(reservation__is_active=True, then="reservation__slot_count"),
                    default=0,
                    output_field=IntegerField(),
                )
            )
        )
        .select_related(
            "template__court",
            "template__level",
            "template__player_type",
        )
    )

    events = []
    for timeslot in timeslots:
        if timeslot.booked_slots < timeslot.template.court.max_players:
            start_datetime = datetime.combine(
                timeslot.date, timeslot.template.start_time
            )
            end_datetime = datetime.combine(timeslot.date, timeslot.template.end_time)
            title = f"{timeslot.template.court.name}"
            if timeslot.template.level:
                title += f" - {timeslot.template.level.name}"
            if timeslot.template.player_type:
                title += f" - {timeslot.template.player_type.name}"

            event = {
                "title": f"{timeslot.template.court.name} - Available",
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat(),
                "bookingType": timeslot.template.booking_type,  # Set the bookingType field
                "courtName": timeslot.template.court.name
                if timeslot.template.court
                else "",
                "levelName": timeslot.template.level.name
                if timeslot.template.level
                else "",
                "availableSlots": timeslot.template.court.max_players
                - timeslot.booked_slots
                # Include additional information as needed
            }
            events.append(event)

    return JsonResponse(events, safe=False)
