from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Folder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Deck(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey(
        Folder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sort_order = models.IntegerField(default=0)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"


class Card(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("archived", "Archived"),
    ]

    deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
    front_text = models.TextField()
    back_text = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        front_preview = (self.front_text or "").strip().replace("\n", " ")
        if len(front_preview) > 40:
            front_preview = front_preview[:40] + "..."
        return f"{self.deck.title} - {front_preview}"


class CardSRS(models.Model):
    """
    One-to-one relationship with Card.
    Each card has exactly one SRS state.
    """

    card = models.OneToOneField(Card, on_delete=models.CASCADE)
    due_at = models.DateTimeField()
    interval_days = models.IntegerField(default=0)
    ease_factor = models.FloatField(default=2.5)
    repetitions = models.IntegerField(default=0)
    lapses = models.IntegerField(default=0)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.card} - due {self.due_at:%Y-%m-%d %H:%M}"


class ReviewSession(models.Model):
    MODE_CHOICES = [
        ("review", "Review"),
        ("cram", "Cram"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default="review",
    )

    def __str__(self):
        if self.ended_at:
            ended = self.ended_at.strftime("%Y-%m-%d %H:%M")
        else:
            ended = "..."

        return (
            f"{self.user.username} - {self.mode} - "
            f"{self.started_at:%Y-%m-%d %H:%M} -> {ended}"
        )
