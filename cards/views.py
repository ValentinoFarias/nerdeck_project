"""View functions and classes for the NerDeck spaced‑repetition app.

This module contains:
- Simple landing/home pages (no logic, just templates)
- Deck listing and CRUD views
- Flashcard creation and study views (spaced‑repetition logic)
- Signup and logout helpers
"""

import json

from django.views.generic import TemplateView
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, logout
from django.views import View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count

from .forms import EmailSignupForm, CardForm
from .models import Deck, Card, ReviewSession, CardSRS


# Default review ladder in days used by the simple spaced‑repetition system.
DEFAULT_LADDER_DAYS = [1, 3, 7, 14, 30, 60, 120, 240, 365]


def _step_from_interval(interval_days: int) -> int:
    """Map a card's current interval (in days) to a step index.

    The step index is an integer position in DEFAULT_LADDER_DAYS and is used
    on the frontend to determine which "step" the card is currently on.
    Unknown intervals are treated as brand‑new cards (step 0).
    """

    # Guard against None/negative intervals.
    interval = max(interval_days or 0, 0)

    for idx, days in enumerate(DEFAULT_LADDER_DAYS):
        if interval == days:
            # After scheduling interval "days" we advance to the next rung.
            return min(idx + 1, len(DEFAULT_LADDER_DAYS) - 1)

    # Unknown interval: treat as brand new.
    return 0


# ---------------------------------------------------------------------------
# Simple template‑only pages
# ---------------------------------------------------------------------------


class LandingPageView(TemplateView):
    """Render the minimal landing page with the NerDeck logo and link to home."""

    template_name = "landingPage.html"


class HomeView(TemplateView):
    """Render the marketing/overview home page (no auth required)."""

    template_name = "home.html"


# ---------------------------------------------------------------------------
# Deck listing and basic CRUD
# ---------------------------------------------------------------------------


@method_decorator(login_required, name="dispatch")
class DecksView(TemplateView):
    """Show the logged‑in user's active decks with due/total card counts."""

    template_name = "decks.html"

    def get_context_data(self, **kwargs):
        """Add the user's decks plus today/total card counts into the context."""
        context = super().get_context_data(**kwargs)

        now = timezone.localtime()
        end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Base queryset: all non‑archived decks for this user.
        decks = (
            Deck.objects
            .filter(user=self.request.user, is_archived=False)
            .annotate(
                # Total active cards per deck.
                total_cards=Count(
                    "card",
                    filter=Q(card__status="active"),
                    distinct=True,
                ),
            )
            .order_by("created_at")
        )

        decks = list(decks)

        # For each deck, compute how many cards are due today.
        for deck in decks:
            deck.today_cards = (
                Card.objects.filter(deck=deck, status="active")
                .filter(Q(cardsrs__due_at__lte=end_of_today) | Q(cardsrs__isnull=True))
                .count()
            )

        context["decks"] = decks
        return context


@login_required
def deck_flashcards(request, deck_id):
    """Show all active flashcards in a single deck."""

    deck = get_object_or_404(Deck, id=deck_id, user=request.user, is_archived=False)
    cards = Card.objects.filter(deck=deck, status="active").order_by("created_at")
    return render(request, "flashcards.html", {"deck": deck, "cards": cards})


@login_required
def new_flashcard(request, deck_id):
    """Create a new flashcard inside the given deck."""

    deck = get_object_or_404(Deck, id=deck_id, user=request.user, is_archived=False)

    if request.method == "POST":
        form = CardForm(request.POST)
        if form.is_valid():
            card = form.save(commit=False)
            card.deck = deck
            card.save()
            messages.success(request, "Flashcard created.")
            return redirect("deck_flashcards", deck_id=deck.id)
    else:
        form = CardForm()

    return render(request, "new_flashcard.html", {"deck": deck, "form": form})


# ---------------------------------------------------------------------------
# Study / spaced‑repetition views
# ---------------------------------------------------------------------------


@login_required
def study_deck(request, deck_id):
    """Start a study session for a given deck.

    Selects all due cards for today, determines the current card and its SRS
    state, and creates a ReviewSession row for tracking the session.
    """

    deck = get_object_or_404(Deck, id=deck_id, user=request.user, is_archived=False)
    now = timezone.localtime()
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # All active cards that are due now or have never been scheduled.
    due_cards = (
        Card.objects.filter(deck=deck, status="active")
        .filter(Q(cardsrs__due_at__lte=end_of_today) | Q(cardsrs__isnull=True))
        .select_related("cardsrs")
        .order_by("created_at")
    )

    current_card = due_cards.first() if due_cards.exists() else None

    current_card_state = {
        "step": 0,
        "due_at": "",
    }

    # If the current card already has SRS data, expose it to the frontend.
    if current_card and hasattr(current_card, "cardsrs") and current_card.cardsrs:
        current_card_state = {
            "step": _step_from_interval(current_card.cardsrs.interval_days),
            "due_at": current_card.cardsrs.due_at.isoformat(),
        }

    # Create a new review session for this user.
    session = ReviewSession.objects.create(
        user=request.user,
        mode="review",  # or "cram" later if you add that mode in the UI
    )

    return render(request, "study.html", {
        "deck": deck,
        "cards": due_cards,
        "current_card": current_card,
        "current_card_state": current_card_state,
        "session": session,
    })


@login_required
@require_POST
def review_answer(request, deck_id):
    """AJAX endpoint called when the user answers a card.

    Updates the CardSRS record based on whether the answer was right/wrong and
    the chosen next due date, then returns the next due card (if any).
    """

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    now = timezone.localtime()
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    card_id = payload.get("card_id")
    is_right = payload.get("is_right")
    step = payload.get("step")  # currently unused but kept for future logic
    due_at_str = payload.get("due_at")

    if card_id is None or is_right is None:
        return JsonResponse({"error": "Missing fields"}, status=400)

    card = get_object_or_404(
        Card,
        id=card_id,
        deck_id=deck_id,
        deck__user=request.user,
    )

    # Parse due_at from ISO string; if missing, fall back to now.
    if due_at_str:
        try:
            due_at = timezone.datetime.fromisoformat(due_at_str.replace("Z", "+00:00"))
            if timezone.is_naive(due_at):
                due_at = timezone.make_aware(due_at, timezone.utc)
        except Exception:
            due_at = timezone.now()
    else:
        due_at = timezone.now()

    # Create or update the SRS record for this card.
    srs, _ = CardSRS.objects.get_or_create(
        card=card,
        defaults={"due_at": due_at},
    )

    srs.due_at = due_at
    # Interval in days from today to due_at.
    srs.interval_days = (due_at.date() - timezone.now().date()).days
    srs.last_reviewed_at = timezone.now()

    if is_right:
        srs.repetitions += 1
    else:
        srs.lapses += 1

    srs.save()

    # Next due card: still active, due today or earlier (or never scheduled).
    due_filter = Q(cardsrs__due_at__lte=end_of_today) | Q(cardsrs__isnull=True)

    next_card = (
        Card.objects.filter(deck_id=deck_id, status="active")
        .filter(due_filter)
        .exclude(id=card.id)
        .select_related("cardsrs")
        .order_by("created_at")
        .first()
    )

    response = {"ok": True}

    if next_card is not None:
        response["next_card"] = {
            "id": next_card.id,
            "front_text": next_card.front_text,
            "back_text": next_card.back_text,
            "due_at": next_card.cardsrs.due_at.isoformat() if hasattr(next_card, "cardsrs") and next_card.cardsrs else "",
            "step": _step_from_interval(next_card.cardsrs.interval_days) if hasattr(next_card, "cardsrs") and next_card.cardsrs else 0,
        }
    else:
        response["next_card"] = None

    return JsonResponse(response)


@login_required
def create_deck(request):
    """Handle creation of a new deck via the small form on decks.html."""

    if request.method != "POST":
        return redirect("decks")

    title = request.POST.get("title", "").strip()
    if not title:
        messages.error(request, "Please provide a name for your NerDeck.")
        return redirect("decks")

    Deck.objects.create(user=request.user, title=title)
    messages.success(request, f"NerDeck '{title}' created.")
    return redirect("decks")


@login_required
def delete_deck(request):
    """Delete a deck selected from the modal list on decks.html."""

    if request.method != "POST":
        return redirect("decks")

    deck_id = request.POST.get("deck_id")
    if not deck_id:
        messages.error(request, "Could not determine which NerDeck to delete.")
        return redirect("decks")

    deck = Deck.objects.filter(user=request.user, id=deck_id).first()
    if not deck:
        messages.error(request, "NerDeck not found.")
        return redirect("decks")

    title = deck.title
    deck.delete()
    messages.success(request, f"NerDeck '{title}' deleted.")
    return redirect("decks")


# ---------------------------------------------------------------------------
# Auth helpers (logout + signup)
# ---------------------------------------------------------------------------


def logout_view(request):
    """Log the user out and send them back to the home page."""

    logout(request)
    return redirect("home")


class SignupView(View):
    """Handle email‑based signup using EmailSignupForm."""

    def get(self, request):
        """Render an empty signup form."""
        form = EmailSignupForm()
        return render(request, "signup.html", {"form": form})

    def post(self, request):
        """Validate the submitted form and create/log the user in."""
        form = EmailSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(
                request,
                f"Account created successfully. Welcome, {user.email}!",
            )

            return redirect("home")

        # If the form is not valid, re-render the page with field errors only.
        return render(request, "signup.html", {"form": form})