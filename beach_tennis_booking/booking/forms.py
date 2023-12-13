from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from .models import (
    TournamentRegistration,
    Tournament,
    Profile,
    Court,
    GameLevel,
    PlayerType,
    TimeSlotTemplate,
    TimeSlot,
    Reservation,
)
from django.forms import SelectDateWidget, TimeInput
import datetime
from django_flatpickr.widgets import DatePickerInput
from django.forms.widgets import CheckboxSelectMultiple, DateInput
from django.contrib import admin
from django.db.models import Count, F, Q, Sum, Exists, OuterRef  # Import F
from collections import OrderedDict
from django.db.models.functions import Coalesce


"""
class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254, help_text="Required. Inform a valid email address."
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
        )
"""


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254, help_text="Required. Inform a valid email address."
    )
    first_name = forms.CharField(max_length=30, required=False, help_text="Optional.")
    last_name = forms.CharField(max_length=30, required=False, help_text="Optional.")
    # Add other custom fields here

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )
        # Include other custom fields in the fields tuple

    def save(self, commit=True):
        user = super(SignUpForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        # Set other custom fields here
        if commit:
            user.save()
            # Handle saving of related Profile model here, if necessary
        return user


class TournamentRegistrationForm(forms.ModelForm):
    partner_name = forms.CharField(max_length=100, required=True)
    partner_contact = forms.CharField(max_length=100, required=True)
    tournament = forms.ModelChoiceField(
        queryset=Tournament.objects.all(),
        empty_label="Select Tournament",
        required=True,
    )

    class Meta:
        model = TournamentRegistration
        fields = ["partner_name", "partner_contact", "tournament"]


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        # Add other fields as needed


"""
class UserUpdateForm(forms.ModelForm):
    image = forms.ImageField(required=False)
    federation_number = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("instance", None)
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        if user and hasattr(user, "profile"):
            self.fields["image"].initial = user.profile.image
            self.fields["federation_number"].initial = user.profile.federation_number

    def save(self, commit=True):
        user = super(UserUpdateForm, self).save(commit=False)
        if commit:
            user.save()
            if self.cleaned_data["image"] or self.cleaned_data["federation_number"]:
                profile = Profile.objects.get_or_create(user=user)[0]
                profile.image = self.cleaned_data["image"]
                profile.federation_number = self.cleaned_data["federation_number"]
                profile.save()
        return user
"""


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["image", "federation_number"]


class CalendarFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    court = forms.ModelChoiceField(queryset=Court.objects.all(), required=False)
    level = forms.ModelChoiceField(queryset=GameLevel.objects.all(), required=False)
    player_type = forms.ModelChoiceField(
        queryset=PlayerType.objects.all(), required=False
    )


class TimeSlotGenerationForm(forms.Form):
    template = forms.ModelChoiceField(queryset=TimeSlotTemplate.objects.all())
    start_date = forms.DateField(widget=DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=DateInput(attrs={"type": "date"}))
    individual_slot_price = forms.DecimalField(max_digits=6, decimal_places=2)
    full_court_price = forms.DecimalField(max_digits=6, decimal_places=2)
    days_of_week = forms.MultipleChoiceField(
        choices=[
            (0, "Monday"),
            (1, "Tuesday"),
            (2, "Wednesday"),
            (3, "Thursday"),
            (4, "Friday"),
            (5, "Saturday"),
            (6, "Sunday"),
        ],
        widget=CheckboxSelectMultiple,
        required=False,
    )


class TimeSlotAdminForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "format": "%Y-%m-%d"})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "format": "%Y-%m-%d"})
    )

    # ... other fields ...
    days_of_week = forms.MultipleChoiceField(
        choices=[
            (0, "Monday"),
            (1, "Tuesday"),
            (2, "Wednesday"),
            (3, "Thursday"),
            (4, "Friday"),
            (5, "Saturday"),
            (6, "Sunday"),
        ],
        widget=CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = TimeSlot
        fields = [
            "template",
            "date",
            "end_date",
            "days_of_week",
            "is_full_court_booked",
            "individual_slot_price",
            "full_court_price",
        ]


class TimeSlotTemplateAdminForm(forms.ModelForm):
    class Meta:
        model = TimeSlotTemplate
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        booking_type = cleaned_data.get("booking_type")

        if booking_type == "individual":
            level = cleaned_data.get("level")
            player_type = cleaned_data.get("player_type")

            if not level:
                self.add_error("level", "Level is required for individual bookings.")
            if not player_type:
                self.add_error(
                    "player_type", "Player type is required for individual bookings."
                )

        return cleaned_data


class ReservationAdminForm(forms.ModelForm):
    court_type = forms.ChoiceField(
        choices=[("individual", "Individual"), ("full_court", "Full Court")],
        required=False,
    )
    reservation_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=False
    )

    level = forms.ModelChoiceField(
        queryset=GameLevel.objects.all(),
        required=False,
        empty_label="Select Level",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    player_type = forms.ModelChoiceField(
        queryset=PlayerType.objects.all(),
        required=False,
        empty_label="Select Player Type",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    timeslot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Reservation
        fields = [
            "user",
            "reservation_date",
            "court_type",
            "level",
            "player_type",
            "slot_count",
            "timeslot",
        ]

    def clean_timeslot(self):
        timeslot_id = self.cleaned_data.get("timeslot")
        print("Timeslot ID:", timeslot_id)
        print("Type of Timeslot ID:", type(timeslot_id))

        if isinstance(timeslot_id, TimeSlot):
            # If it's a TimeSlot instance, get the id
            return timeslot_id
        else:
            # Otherwise, try to get the TimeSlot by id
            try:
                return TimeSlot.objects.get(pk=timeslot_id)
            except TimeSlot.DoesNotExist:
                raise forms.ValidationError("Invalid timeslot selected.")

    def __init__(self, *args, **kwargs):
        super(ReservationAdminForm, self).__init__(*args, **kwargs)

        if "initial" in kwargs:
            court_type = kwargs["initial"].get("court_type")
            reservation_date = kwargs["initial"].get("reservation_date")

            if court_type and reservation_date:
                timeslot_qs = TimeSlot.objects.filter(
                    template__booking_type=court_type, date=reservation_date
                )

                if court_type == "individual":
                    timeslot_qs = timeslot_qs.annotate(
                        booked_slots=Count(
                            "reservation", filter=Q(reservation__is_active=True)
                        )
                    ).exclude(booked_slots__gte=F("template__court__max_players"))

                elif court_type == "full_court":
                    # For full court, exclude timeslots that are fully booked
                    timeslot_qs = timeslot_qs.exclude(is_full_court_booked=True)

                self.fields["timeslot"].queryset = timeslot_qs
