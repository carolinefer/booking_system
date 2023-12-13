from django.db import models
from datetime import datetime, timedelta
from django.contrib.auth.models import User  # Import the User model
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_extensions.db.models import  TimeStampedModel
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Sum
from django.contrib import messages

# Create your models here.


class Court( TimeStampedModel, models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    is_available = models.BooleanField(default=True)
    max_players = models.IntegerField(default=4)
    image = models.ImageField(
        upload_to="court_images/", null=True, blank=True
    )  # Add an image field
    game_duration = models.DurationField(
        default=timedelta(minutes=90)
    )  # 1 hour 30 minutes

    map_link = models.URLField(null=True, blank=True)  # Add a map_link field

    def __str__(self):
        return self.name

    @staticmethod
    def get_available_courts():
        return Court.objects.filter(is_available=True)


class GameLevel( TimeStampedModel, models.Model):
    name = models.CharField(
        max_length=100
    )  # e.g., 'Beginner', 'Intermediate', 'Advanced'

    def __str__(self):
        return self.name


class PlayerType(TimeStampedModel, models.Model):
    name = models.CharField(max_length=100)  # e.g., 'Men', 'Women', 'Mixed'

    def __str__(self):
        return self.name


class TimeSlotTemplate(models.Model):
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    level = models.ForeignKey(
        GameLevel, on_delete=models.SET_NULL, null=True, blank=True
    )
    player_type = models.ForeignKey(
        PlayerType, on_delete=models.SET_NULL, null=True, blank=True
    )
    booking_type = models.CharField(
        max_length=15,
        choices=(("individual", "Individual"), ("full_court", "Full Court")),
        default="individual",
    )

    def __str__(self):
        details = f"{self.court.name} - {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')}"
        if self.booking_type:
            details += f" - {self.get_booking_type_display()}"
        if self.level:
            details += f" - Level: {self.level}"
        if self.player_type:
            details += f" - Player Type: {self.player_type}"
        return details


class TimeSlot( TimeStampedModel, models.Model):
    template = models.ForeignKey(TimeSlotTemplate, on_delete=models.CASCADE)
    date = models.DateField()  # Temporarily allow null
    is_full_court_booked = models.BooleanField(default=False)
    individual_slot_price = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    full_court_price = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    def __str__(self):
        time_range = f"{self.template.start_time.strftime('%H:%M')} to {self.template.end_time.strftime('%H:%M')}"
        return f"{self.template} on {self.date}"


class ReservationTimeSlotMaster(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    total_slot_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_full_court = models.BooleanField(default=False)

    def update_on_reservation_change(self):
        """
        Update the master reservation based on the current status of linked reservations.
        """
        active_reservations = self.reservations.filter(is_active=True)

        # Check if there is a full court booking
        if any(
            reservation.was_full_court_booking for reservation in active_reservations
        ):
            # If a full court booking exists, set total_slot_count to the court's maximum capacity
            self.total_slot_count = self.timeslot.template.court.max_players
        else:
            # Otherwise, count the total number of active slots
            self.total_slot_count = (
                active_reservations.aggregate(Sum("slot_count"))["slot_count__sum"] or 0
            )

        # Update total price based on the type of booking
        if self.timeslot.template.booking_type == "full_court":
            self.total_price = self.timeslot.full_court_price
        else:
            self.total_price = (
                self.timeslot.individual_slot_price * self.total_slot_count
            )

        self.save()

    def cancel_master_reservation(self):
        """Cancel the master reservation."""
        self.total_slot_count = 0
        self.total_price = 0
        self.is_active = False  # Set the reservation as inactive
        self.timeslot.is_full_court_booked = False
        self.timeslot.save()
        # Set additional fields if needed to indicate cancellation
        self.save()

    def __str__(self):
        return f"Master Reservation id {self.id}"


class Reservation( TimeStampedModel, models.Model):
    timeslot = models.ForeignKey(
        TimeSlot, on_delete=models.CASCADE, null=True, blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reserved_on = models.DateTimeField(auto_now_add=True)
    slot_number = models.IntegerField(default=1)  # Slot number within the timeslot
    slot_count = models.IntegerField(default=1)  # Number of slots booked
    is_active = models.BooleanField(default=True)
    canceled_on = models.DateTimeField(null=True, blank=True)
    was_full_court_booking = models.BooleanField(default=False)
    master_reservation_timeslot = models.ForeignKey(
        ReservationTimeSlotMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )

    def can_cancel(self):
        """Check if the reservation can be cancelled."""
        return timezone.now() <= self.timeslot.start_time - timedelta(hours=6)

    def cancel_reservation(self):
        """
        Cancel the reservation and update the master reservation.
        """
        if self.is_active:
            self.is_active = False
            self.canceled_on = timezone.now()
            self.save()

            if self.timeslot.template.booking_type == "full_court":
                # For a full court booking, set the corresponding flag in the timeslot
                self.timeslot.is_full_court_booked = False
                self.timeslot.save()

            # Update the master reservation
            if self.master_reservation_timeslot:
                self.master_reservation_timeslot.update_on_reservation_change()

    def send_reservation_confirmation_email(self, total_slots_booked=None):
        # Determine booking type
        booking_type = self.timeslot.template.booking_type

        if booking_type == "full_court":
            booking_type_text = "Full court"
        else:
            slot_count = (
                total_slots_booked
                if total_slots_booked is not None
                else self.slot_count
            )
            booking_type_text = f"{slot_count} individual slot(s)"
        # Email content for the user
        user_subject = f"Reservation Confirmation"
        user_message = f"You have successfully reserved {booking_type_text} at {self.timeslot.template.start_time} for {self.timeslot.template.court.name}."

        # Email content for admin
        admin_subject = "Reservation Confirmation"
        admin_message = f"A reservation has been made for {booking_type_text} at {self.timeslot.template.start_time} for {self.timeslot.template.court.name}."

        # Send email to the user
        send_mail(
            user_subject,
            user_message,
            settings.EMAIL_HOST_USER,
            [self.user.email],
        )

        # Send email to all admins
        admin_emails = User.objects.filter(is_superuser=True).values_list(
            "email", flat=True
        )
        for admin_email in admin_emails:
            send_mail(
                admin_subject,
                admin_message,
                settings.EMAIL_HOST_USER,
                [admin_email],
            )

    def send_cancellation_email(self):
        # Determine booking type
        booking_type = self.timeslot.template.booking_type

        if booking_type == "full_court":
            booking_type_text = "Full court"
        else:
            booking_type_text = f"{self.slot_count} individual slot(s)"
        # Fetch admin emails
        admin_emails = User.objects.filter(is_superuser=True).values_list(
            "email", flat=True
        )

        # Email content for user
        user_subject = "Reservation Cancellation"
        user_message = f"Your reservation for {self.timeslot.template.court.name} at {self.timeslot.template.start_time} has been cancelled."

        # Email content for admin
        admin_subject = "Reservation Cancelled"
        admin_message = f"A reservation for {self.timeslot.template.court.name} at {self.timeslot.template.start_time} has been cancelled."

        # Send email to the user who made the reservation
        send_mail(
            user_subject, user_message, settings.EMAIL_HOST_USER, [self.user.email]
        )

        # Send email to all admins
        for admin_email in admin_emails:
            send_mail(
                admin_subject, admin_message, settings.EMAIL_HOST_USER, [admin_email]
            )

    def save(self, *args, **kwargs):
        send_email = kwargs.pop("send_email", False)
        was_active = self.is_active if self.pk else None
        total_slots_booked = kwargs.pop("total_slots_booked", None)
        super().save(*args, **kwargs)

        if send_email:
            self.send_reservation_confirmation_email(
                total_slots_booked=total_slots_booked
            )
        elif was_active and not self.is_active:
            self.send_cancellation_email()

    

    def __str__(self):
        return f"Reservation ID {self.id}"


class Tournament( TimeStampedModel, models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    image = models.ImageField(upload_to="tournament_images/", null=True, blank=True)
    map_link = models.URLField(null=True, blank=True)
    contact_details = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    additional_info = models.TextField(null=True, blank=True)  # For extra details
    max_teams = models.IntegerField(default=10)

    def is_full(self):
        # Check if the number of registered teams has reached the maximum
        return self.tournamentregistration_set.count() >= self.max_teams

    def available_slots(self):
        return self.max_teams - self.tournamentregistration_set.count()

    def __str__(self):
        return self.name


class TournamentRegistration( TimeStampedModel, models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    partner_name = models.CharField(max_length=100)
    partner_contact = models.CharField(max_length=100)
    registered_on = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tournament.name} - {self.user.username}"

    def can_cancel(self):
        # Check if the current time is at least one week before the tournament start date
        return timezone.now() <= self.tournament.start_date - timedelta(weeks=1)

    def cancel_registration(self):
        self.is_confirmed = False
        self.save()


class Profile( TimeStampedModel, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="profile_pics", blank=True, null=True)
    federation_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"


# Create a Profile for each new user
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
