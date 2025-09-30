from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import uuid


class Appointment(models.Model):
    """
    Model for customer appointments at different stores
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('not_required', 'Not Required'),
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]
    
    # Unique appointment ID
    appointment_id = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    
    # Customer who booked the appointment
    customer = models.ForeignKey('POSMagicApp.Customer', on_delete=models.CASCADE, related_name='appointments')
    
    # Store where the appointment is scheduled (can be null for out-of-salon appointments)
    store = models.ForeignKey('production.Store', on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    is_out_of_salon = models.BooleanField(default=False, help_text="Whether this is an out-of-salon appointment")
    out_of_salon_address = models.TextField(blank=True, help_text="Address for out-of-salon appointments")
    
    # Services requested (many-to-many for multiple services)
    services = models.ManyToManyField('production.ServiceName', related_name='appointments', help_text="Services requested for this appointment")
    
    # Appointment timing
    appointment_date = models.DateField(help_text="Date of the appointment")
    appointment_time = models.TimeField(help_text="Time of the appointment")
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Expected duration in minutes")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='not_required')
    
    # Customer details for the appointment
    customer_name = models.CharField(max_length=200, help_text="Customer name for the appointment")
    customer_phone = models.CharField(max_length=20, help_text="Customer phone number")
    customer_email = models.EmailField(blank=True, null=True, help_text="Customer email address")
    
    # Special requests or notes
    special_requests = models.TextField(blank=True, help_text="Any special requests or notes for the appointment")
    
    # Staff assignment (optional - can be assigned later)
    assigned_staff = models.ManyToManyField('POSMagicApp.Staff', blank=True, related_name='assigned_appointments', help_text="Staff members assigned to this appointment")
    
    # Financial tracking
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Estimated cost of services")
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Deposit amount paid")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When the appointment was confirmed")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the appointment was completed")
    
    # Created by (staff member who helped with booking)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Staff member who created this appointment")
    
    class Meta:
        ordering = ['appointment_date', 'appointment_time']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
    
    def __str__(self):
        location = "Out of Salon" if self.is_out_of_salon else (self.store.name if self.store else "Unknown Location")
        return f"Appointment {self.appointment_id} - {self.customer_name} at {location} on {self.appointment_date}"
    
    def save(self, *args, **kwargs):
        if not self.appointment_id:
            self.appointment_id = self.generate_appointment_id()
        super().save(*args, **kwargs)
    
    def generate_appointment_id(self):
        """Generate a unique appointment ID"""
        if self.is_out_of_salon:
            store_prefix = 'OS'  # Out of Salon
        else:
            store_prefix = self.store.name[:2].upper() if self.store else 'AP'
        date_part = timezone.now().strftime('%m%y')
        unique_part = str(uuid.uuid4()).replace('-', '').upper()[:6]
        return f"{store_prefix}-{date_part}-{unique_part}"
    
    @property
    def appointment_datetime(self):
        """Combine date and time into a datetime object"""
        return datetime.combine(self.appointment_date, self.appointment_time)
    
    @property
    def is_past(self):
        """Check if the appointment is in the past"""
        return self.appointment_datetime < timezone.now()
    
    @property
    def is_today(self):
        """Check if the appointment is today"""
        return self.appointment_date == timezone.now().date()
    
    @property
    def is_upcoming(self):
        """Check if the appointment is in the future"""
        return self.appointment_datetime > timezone.now()
    
    @property
    def can_be_cancelled(self):
        """Check if the appointment can be cancelled"""
        return self.status in ['pending', 'confirmed'] and self.is_upcoming
    
    @property
    def can_be_rescheduled(self):
        """Check if the appointment can be rescheduled"""
        return self.status in ['pending', 'confirmed'] and self.is_upcoming
    
    def get_services_display(self):
        """Get a formatted string of all services"""
        return ", ".join([service.name for service in self.services.all()])
    
    def calculate_estimated_cost(self):
        """Calculate estimated cost based on services"""
        total_cost = 0
        for service in self.services.all():
            # Get the service price from the store
            try:
                store_service = self.store.store_services.get(service=service)
                total_cost += store_service.service.price
            except:
                # Fallback to service's default price
                total_cost += service.price
        return total_cost
    
    def confirm_appointment(self, confirmed_by=None):
        """Confirm the appointment"""
        if self.status == 'pending':
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            if confirmed_by:
                self.created_by = confirmed_by
            self.save()
            return True
        return False
    
    def complete_appointment(self):
        """Mark the appointment as completed"""
        if self.status in ['confirmed', 'in_progress']:
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            return True
        return False
    
    def cancel_appointment(self, reason=None):
        """Cancel the appointment"""
        if self.can_be_cancelled:
            self.status = 'cancelled'
            if reason:
                self.special_requests += f"\nCancellation reason: {reason}"
            self.save()
            return True
        return False


class AppointmentReminder(models.Model):
    """
    Model to track appointment reminders sent to customers
    """
    REMINDER_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('phone', 'Phone Call'),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=10, choices=REMINDER_TYPE_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_to = models.CharField(max_length=200, help_text="Email or phone number the reminder was sent to")
    message = models.TextField(help_text="The reminder message sent")
    is_delivered = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Reminder for {self.appointment.appointment_id} via {self.reminder_type}"


class AppointmentFeedback(models.Model):
    """
    Model to store customer feedback after appointments
    """
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]
    
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(choices=RATING_CHOICES, help_text="Overall rating of the appointment")
    service_quality = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for service quality")
    staff_friendliness = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for staff friendliness")
    cleanliness = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for cleanliness")
    value_for_money = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for value for money")
    
    comments = models.TextField(blank=True, help_text="Additional comments or feedback")
    would_recommend = models.BooleanField(default=True, help_text="Would you recommend us to others?")
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Feedback for {self.appointment.appointment_id} - Rating: {self.rating}/5"