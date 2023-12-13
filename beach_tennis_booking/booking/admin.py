from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from collections import defaultdict
from datetime import datetime, date, timedelta
from itertools import product
import logging  # Add this line to import the logging module
from django.core.exceptions import ValidationError
from django import forms
from .forms import (
    CalendarFilterForm,
    TimeSlotGenerationForm,
    TimeSlotAdminForm,
    TimeSlotTemplateAdminForm,
    ReservationAdminForm,
)
from .models import (
    Court,
    TimeSlot,
    Reservation,
    GameLevel,
    PlayerType,
    Tournament,
    TournamentRegistration,
    Profile,
    TimeSlotTemplate,
    ReservationTimeSlotMaster,
)
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.db.models import Sum  # Import Sum
import logging

# Create a logger for your app
logger = logging.getLogger("booking")


# Register GameLevel and PlayerType with default admin view
# @admin.register(GameLevel, PlayerType)
class DefaultAdmin(admin.ModelAdmin):
    pass


class TimeSlotAdmin(admin.ModelAdmin):
    form = TimeSlotAdminForm  # Set your custom form here
    list_display = [
        "get_court",
        "get_start_time",
        "get_end_time",
        "get_level",
        "get_player_type",
        "date",
        "get_booking_type",
        "individual_slot_price",
        "full_court_price",
    ]

    def get_court(self, obj):
        return obj.template.court if obj.template else "No template"

    get_court.short_description = "Court"

    def get_start_time(self, obj):
        return (
            f"{obj.template.start_time.strftime('%H:%M')}"
            if obj.template
            else "No template"
        )

    get_start_time.short_description = "Start Time"

    def get_end_time(self, obj):
        return (
            f"{obj.template.end_time.strftime('%H:%M')}"
            if obj.template
            else "No template"
        )

    get_end_time.short_description = "End Time"

    def get_level(self, obj):
        return obj.template.level if obj.template else "No template"

    get_level.short_description = "Level"

    def get_player_type(self, obj):
        return obj.template.player_type if obj.template else "No template"

    get_player_type.short_description = "Player Type"

    def get_booking_type(self, obj):
        return obj.template.booking_type if obj.template else "No template"

    get_booking_type.short_description = "Booking Type"

    def save_model(self, request, obj, form, change):
        if not change:  # Only for new instances
            end_date = form.cleaned_data["end_date"]
            days_of_week = form.cleaned_data["days_of_week"]

            current_date = obj.date  # Use the existing date field as start_date
            while current_date <= end_date:
                if not days_of_week or str(current_date.weekday()) in days_of_week:
                    # Check if a TimeSlot with the same attributes already exists for the current_date
                    if not TimeSlot.objects.filter(
                        template=obj.template, date=current_date
                    ).exists():
                        TimeSlot.objects.create(
                            template=obj.template,
                            date=current_date,
                            individual_slot_price=obj.individual_slot_price,
                            full_court_price=obj.full_court_price,
                        )
                current_date += timedelta(days=1)
        else:
            # Ensure booking_type is set correctly
            obj.booking_type = form.cleaned_data.get("booking_type", "individual")
            obj.save()


class TimeSlotTemplateAdmin(admin.ModelAdmin):
    form = TimeSlotTemplateAdminForm
    list_display = [
        "court",
        "formatted_start_time",
        "formatted_end_time",
        "level",
        "player_type",
        "booking_type",
    ]

    def formatted_start_time(self, obj):
        return obj.start_time.strftime("%H:%M")

    formatted_start_time.short_description = "Start Time"

    def formatted_end_time(self, obj):
        return obj.end_time.strftime("%H:%M")

    formatted_end_time.short_description = "End Time"

    def save_model(self, request, obj, form, change):
        if obj.booking_type == "individual" and (not obj.level or not obj.player_type):
            raise ValidationError(
                "Level and Player Type are required for individual bookings."
            )
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "generate-timeslots/",
                self.admin_site.admin_view(self.generate_timeslots),
                name="generate-timeslots",
            ),
        ]
        return custom_urls + urls

    def generate_timeslots(self, request):
        context = {}
        if request.method == "POST":
            form = TimeSlotGenerationForm(request.POST)
            if form.is_valid():
                template = form.cleaned_data["template"]
                start_date = form.cleaned_data["start_date"]
                end_date = form.cleaned_data["end_date"]
                days_of_week = form.cleaned_data["days_of_week"]

                current_date = start_date
                while current_date <= end_date:
                    if str(current_date.weekday()) in days_of_week:
                        TimeSlot.objects.create(template=template, date=current_date)
                    current_date += timedelta(days=1)

                context["success_message"] = "Time slots generated successfully."
        else:
            form = TimeSlotGenerationForm()
        context["form"] = form
        return render(request, "admin/generate_timeslots.html", context)

    def process_timeslot_generation(self, cleaned_data):
        template = cleaned_data["template"]
        dates_str = cleaned_data["dates"]
        individual_slot_price = cleaned_data["individual_slot_price"]
        full_court_price = cleaned_data["full_court_price"]
        date_strings = dates_str.split(
            ","
        )  # Split the string into a list of date strings

        for date_str in date_strings:
            try:
                # Convert each string to a date object
                date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
                # Create a TimeSlot for each date
                TimeSlot.objects.create(
                    template=template,
                    date=date,
                    individual_slot_price=individual_slot_price,
                    full_court_price=full_court_price,
                )
            except ValueError:
                # Handle the case where the date string is not valid
                # You can add a message or log this error as needed
                pass


# Custom admin view for Court
# @admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_available", "max_players", "map_link")
    # Include other fields or customizations as needed


class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "start_date", "end_date", "is_full")
    list_filter = ("location", "start_date")
    search_fields = ("name", "location")


class MyAdminSite(admin.AdminSite):
    def get_date_range(self, start_date, end_date):
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + timedelta(n)

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["custom_calendar_url"] = reverse("admin_calendar")
        return super().index(request, extra_context)

    def calendar_view(self, request):
        form = CalendarFilterForm(request.GET or None)

        # Initialize default date range
        default_start_date = date.today()
        default_end_date = default_start_date + timedelta(days=30)

        # Initialize querysets
        all_timeslots_queryset = TimeSlot.objects.all()  # Initialize with all timeslots

        # Apply filters if the form is valid
        if form.is_valid():
            # Update start_date based on form data
            start_date = form.cleaned_data.get("start_date", default_start_date)
            end_date = start_date + timedelta(
                days=30
            )  # Set end_date 30 days from the form's start_date

            # Apply date range filter to the queryset
            all_timeslots_queryset = all_timeslots_queryset.filter(
                date__range=(start_date, end_date)
            )

            # Additional filters for court, level, and player_type
            court = form.cleaned_data.get("court")
            level = form.cleaned_data.get("level")
            player_type = form.cleaned_data.get("player_type")

            if court:
                all_timeslots_queryset = all_timeslots_queryset.filter(
                    template__court=court
                )
            if level:
                all_timeslots_queryset = all_timeslots_queryset.filter(
                    template__level=level
                )
            if player_type:
                all_timeslots_queryset = all_timeslots_queryset.filter(
                    template__player_type=player_type
                )
        else:
            # If the form is not valid, use the default date range
            start_date = default_start_date
            end_date = default_end_date
            all_timeslots_queryset = all_timeslots_queryset.filter(
                date__range=(start_date, end_date)
            )

        # Fetch all courts
        all_courts = Court.objects.all()

        # Initialize data structure to store timeslots and reservations
        calendar_data = []

        # Fetch timeslots and organize them by court and date
        for court in all_courts:
            court_data = {"court_name": court.name, "days_data": []}

            for day in self.get_date_range(start_date, end_date):
                day_data = {"date_key": day, "timeslots": []}
                day_timeslots = all_timeslots_queryset.filter(
                    date=day, template__court=court
                ).order_by("template__start_time")

                for timeslot in day_timeslots:
                    slots_data = {slot_num: None for slot_num in range(1, 5)}

                    if timeslot.is_full_court_booked:
                        # If full court is booked, find the reservation and mark all slots as occupied
                        reservation = Reservation.objects.filter(
                            timeslot=timeslot,
                            was_full_court_booking=True,
                            is_active=True,
                        ).first()
                        for slot_num in slots_data.keys():
                            slots_data[slot_num] = reservation

                    else:
                        # Process individual slot reservations
                        for slot_num in slots_data.keys():
                            reservation = Reservation.objects.filter(
                                timeslot=timeslot, slot_number=slot_num, is_active=True
                            ).first()
                            slots_data[slot_num] = reservation

                    timeslot.slots_data = slots_data
                    day_data["timeslots"].append(timeslot)

                court_data["days_data"].append(day_data)

            calendar_data.append(court_data)

        context = {
            "form": form,
            "calendar_data": calendar_data,
            "dates": [
                start_date + timedelta(days=i)
                for i in range((end_date - start_date).days + 1)
            ],
        }

        return render(request, "admin/admin_calendar.html", context)


# Make sure your UserAdmin is set up with search fields
class CustomUserAdmin(UserAdmin):
    search_fields = ["email", "first_name", "last_name", "username"]


class ReservationAdmin(admin.ModelAdmin):
    form = ReservationAdminForm
    # Add autocomplete fields
    autocomplete_fields = ["user"]

    class Media:
        js = ("js/timeslot_ajax.js",)

    list_display = (
        "id",
        "get_timeslot_time",
        "get_timeslot_date",
        "court_name",
        "booking_type",
        "level_name",
        "player_type_name",  # Display player type name
        "slot_number",
        "slot_count",
        "user_full_name",  # Custom method to display user's full name
        "reserved_on",
        "canceled_on",
        "master_reservation_timeslot",
        "was_full_court_booking",
    )
    list_filter = (
        "is_active",
        "user__username",  # Filter by user's username
        "user__first_name",  # Filter by user's first name
        "user__last_name",  # Filter by user's last name
    )
    search_fields = (
        "user__username",  # Search by user's username
        "user__first_name",  # Search by user's first name
        "user__last_name",  # Search by user's last name
        "id",  # Search by reservation ID
    )

    def available_slots(self, obj):
        max_slots = obj.timeslot.template.court.max_players
        active_reservations = Reservation.objects.filter(
            timeslot=obj.timeslot, is_active=True
        ).aggregate(total_slots_booked=Sum("slot_count"))
        return max_slots - active_reservations["total_slots_booked"]

    def user_full_name(self, obj):
        user = obj.user
        if user:
            return user.get_full_name() if user.get_full_name() else user.username
        return "N/A"

    def get_timeslot_time(self, obj):
        start_time = obj.timeslot.template.start_time.strftime("%H:%M")
        end_time = obj.timeslot.template.end_time.strftime("%H:%M")
        return f"{start_time} to {end_time}"

    get_timeslot_time.short_description = "Time"

    def get_timeslot_date(self, obj):
        return obj.timeslot.date

    get_timeslot_date.short_description = "Date"

    def booking_type(self, obj):
        return (
            obj.timeslot.template.booking_type
            if obj.timeslot and obj.timeslot.template
            else "N/A"
        )

    booking_type.short_description = "Booking Type"

    def court_name(self, obj):
        return (
            obj.timeslot.template.court.name
            if obj.timeslot and obj.timeslot.template
            else "N/A"
        )

    court_name.short_description = "Court"

    def level_name(self, obj):
        return (
            obj.timeslot.template.level.name
            if obj.timeslot and obj.timeslot.template and obj.timeslot.template.level
            else "N/A"
        )

    level_name.short_description = "Level"

    def player_type_name(self, obj):
        return (
            obj.timeslot.template.player_type.name
            if obj.timeslot
            and obj.timeslot.template
            and obj.timeslot.template.player_type
            else "N/A"
        )

    player_type_name.short_description = "Player Type"

    def save_model(self, request, obj, form, change):
        # This boolean will track whether an email needs to be sent
        send_confirmation_email = False
        if not change:
            # Check if the timeslot is already fully booked for full court bookings
            if (
                obj.timeslot.is_full_court_booked
                and obj.timeslot.template.booking_type == "full_court"
            ):
                messages.error(
                    request, "This timeslot is already fully booked for a full court."
                )
                return
            else:
                send_confirmation_email = True

            # Fetch or create a master reservation
            master_reservation, _ = ReservationTimeSlotMaster.objects.get_or_create(
                user=obj.user, timeslot=obj.timeslot
            )

            if obj.timeslot.template.booking_type == "individual":
                # Handle individual slot bookings
                occupied_slots = set(
                    Reservation.objects.filter(
                        timeslot=obj.timeslot, is_active=True
                    ).values_list("slot_number", flat=True)
                )
                total_slots = set(range(1, obj.timeslot.template.court.max_players + 1))
                available_slots = total_slots - occupied_slots
                send_confirmation_email = True

                slots_to_book = min(obj.slot_count, len(available_slots))
                for _ in range(slots_to_book):
                    if available_slots:
                        slot_number = available_slots.pop()
                        Reservation.objects.create(
                            user=obj.user,
                            timeslot=obj.timeslot,
                            slot_number=slot_number,
                            slot_count=1,  # Individual slot should have count 1
                            is_active=True,
                            master_reservation_timeslot=master_reservation,
                        )

            elif obj.timeslot.template.booking_type == "full_court":
                # Handle full court booking
                full_court_slot_count = obj.timeslot.template.court.max_players

                Reservation.objects.create(
                    user=obj.user,
                    timeslot=obj.timeslot,
                    slot_number=1,  # Full court can have a default slot number
                    slot_count=full_court_slot_count,  # Full court booking counts as all slots
                    is_active=True,
                    master_reservation_timeslot=master_reservation,
                    was_full_court_booking=True,
                )
                # Set the timeslot as fully booked for full court
                obj.timeslot.is_full_court_booked = True
                obj.timeslot.save()

                # Explicitly update the total_slot_count in master reservation for full court booking
                master_reservation.total_slot_count = full_court_slot_count
                master_reservation.save()

            # Update other details of master reservation
            master_reservation.update_on_reservation_change()

        else:
            send_confirmation_email = True
            super().save_model(request, obj, form, change)

        # Send email if needed
        if send_confirmation_email:
            obj.send_reservation_confirmation_email()

    def response_add(self, request, obj, post_url_continue=None):
        """
        Handle the response after adding a new object.
        """
        response = super().response_add(request, obj, post_url_continue)
        if hasattr(self, "insufficient_slots") and self.insufficient_slots:
            messages.error(request, "Not enough slots available for this timeslot.")
        return response

    def response_change(self, request, obj):
        """
        Handle the response after changing an object.
        """
        response = super().response_change(request, obj)
        if hasattr(self, "insufficient_slots") and self.insufficient_slots:
            messages.error(request, "Not enough slots available for this timeslot.")
        return response

    def master_reservation_timeslot(self, obj):
        return (
            obj.master_reservation_timeslot.id
            if obj.master_reservation_timeslot
            else "N/A"
        )

    master_reservation_timeslot.short_description = "Master Reservation ID"

    def delete_queryset(self, request, queryset):
        """Handle bulk deletion of Reservations."""
        for reservation in queryset:
            master_reservation_id = reservation.master_reservation_timeslot_id
            was_full_court = reservation.was_full_court_booking
            timeslot = reservation.timeslot

            reservation.delete()  # Delete each reservation individually

            # Check if the timeslot needs to be updated
            if was_full_court:
                # Check if there are any remaining full court bookings for this timeslot
                remaining_full_court_bookings = Reservation.objects.filter(
                    timeslot=timeslot, was_full_court_booking=True, is_active=True
                ).exists()

                if not remaining_full_court_bookings:
                    timeslot.is_full_court_booked = False
                    timeslot.save()

            if master_reservation_id:
                self.update_or_delete_master_reservation(master_reservation_id)

    def update_or_delete_master_reservation(self, master_reservation_id):
        """Update or delete the master reservation based on remaining linked reservations."""
        remaining_reservations_count = Reservation.objects.filter(
            master_reservation_timeslot_id=master_reservation_id
        ).count()

        if remaining_reservations_count == 0:
            # Delete the master reservation if no active linked reservations are left
            ReservationTimeSlotMaster.objects.filter(id=master_reservation_id).delete()
        else:
            # Update the master reservation
            master_reservation = ReservationTimeSlotMaster.objects.get(
                id=master_reservation_id
            )
            master_reservation.update_on_reservation_change()

    actions = ["cancel_admin_reservations"]  # add other actions if needed

    def cancel_admin_reservations(self, request, queryset):
        for reservation in queryset:
            if reservation.is_active:
                reservation.cancel_reservation()
                reservation.send_cancellation_email()  # Send cancellation email
                messages.success(
                    request,
                    f"Reservation {reservation.id} canceled successfully and email sent.",
                )
            else:
                messages.warning(
                    request, f"Reservation {reservation.id} is already inactive."
                )

    cancel_admin_reservations.short_description = (
        "Cancel selected reservations and send emails"
    )


# Admin view for ReservationTimeSlotMaster
class ReservationTimeSlotMasterAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "user_full_name",
        "get_timeslot_time",
        "get_timeslot_date",
        "booking_type",
        "total_price",
        "created_at",
        "court_name",
        "level_name",
        "player_type_name",
        "is_active",
        "total_slot_count",
    ]
    search_fields = ["user__username", "timeslot__template__court__name"]
    list_filter = ["user", "timeslot__date"]
    readonly_fields = ["total_price", "created_at"]

    def user_full_name(self, obj):
        user = obj.user
        if user:
            return user.get_full_name() if user.get_full_name() else user.username
        return "N/A"

    def get_timeslot_time(self, obj):
        start_time = obj.timeslot.template.start_time.strftime("%H:%M")
        end_time = obj.timeslot.template.end_time.strftime("%H:%M")
        return f"{start_time} to {end_time}"

    get_timeslot_time.short_description = "Time"

    def get_timeslot_date(self, obj):
        return obj.timeslot.date

    get_timeslot_date.short_description = "Date"

    def booking_type(self, obj):
        return (
            obj.timeslot.template.booking_type
            if obj.timeslot and obj.timeslot.template
            else "N/A"
        )

    booking_type.short_description = "Booking Type"

    def court_name(self, obj):
        return (
            obj.timeslot.template.court.name
            if obj.timeslot and obj.timeslot.template
            else "N/A"
        )

    court_name.short_description = "Court"

    def level_name(self, obj):
        return (
            obj.timeslot.template.level.name
            if obj.timeslot and obj.timeslot.template and obj.timeslot.template.level
            else "N/A"
        )

    level_name.short_description = "Level"

    def player_type_name(self, obj):
        return (
            obj.timeslot.template.player_type.name
            if obj.timeslot
            and obj.timeslot.template
            and obj.timeslot.template.player_type
            else "N/A"
        )

    player_type_name.short_description = "Player Type"


# Replace default admin site with your custom site
admin_site = MyAdminSite(name="customadmin")


# Register Reservation with your custom admin site
admin_site.register(Reservation, ReservationAdmin)

admin_site.register(ReservationTimeSlotMaster, ReservationTimeSlotMasterAdmin)
# Register Tournament with its custom admin class
admin_site.register(Tournament, TournamentAdmin)

# Register TournamentRegistration with the default admin view
admin_site.register(TournamentRegistration)
admin_site.register(Profile)
# Register models with your custom admin site
admin_site.register(GameLevel, DefaultAdmin)
admin_site.register(PlayerType, DefaultAdmin)
admin_site.register(TimeSlot, TimeSlotAdmin)
admin_site.register(Court, CourtAdmin)
# Replace default admin site registration with your custom admin site registration

# Check if the User model is registered with your custom admin site. If not, register it.

# Check if User model is already registered, if not then register it
if User not in admin_site._registry:
    admin_site.register(User, CustomUserAdmin)

admin_site.register(Group, GroupAdmin)
admin_site.register(TimeSlotTemplate, TimeSlotTemplateAdmin)
