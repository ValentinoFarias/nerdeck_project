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
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count

from .forms import EmailSignupForm, CardForm
from .models import Deck, Card, ReviewSession, CardSRS, Folder


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


@method_decorator(xframe_options_exempt, name="dispatch")
class LandingPageView(TemplateView):
    """Render the minimal landing page with the NerDeck logo and link to home."""

    template_name = "landingPage.html"


@method_decorator(xframe_options_exempt, name="dispatch")
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
            .select_related("folder")
            .annotate(
                # Total active cards per deck.
                total_cards=Count(
                    "card",
                    filter=Q(card__status="active"),
                    distinct=True,
                ),
            )
            .order_by("sort_order", "created_at")
        )

        decks = list(decks)

        # For each deck, compute how many cards are due today.
        for deck in decks:
            deck.today_cards = (
                Card.objects.filter(deck=deck, status="active")
                .filter(Q(cardsrs__due_at__lte=end_of_today) | Q(cardsrs__isnull=True))
                .count()
            )

        folder_groups_map = {}
        ungrouped_decks = []
        for deck in decks:
            if deck.folder_id:
                group = folder_groups_map.setdefault(
                    deck.folder_id,
                    {"folder": deck.folder, "decks": []},
                )
                group["decks"].append(deck)
            else:
                ungrouped_decks.append(deck)

        folder_groups = sorted(
            folder_groups_map.values(),
            key=lambda item: item["folder"].created_at,
        )

        context["decks"] = decks
        context["folder_groups"] = folder_groups
        context["ungrouped_decks"] = ungrouped_decks
        return context


@login_required
def new_flashcard(request, deck_id):
    """Create a new flashcard or edit an existing one inside the given deck."""

    deck = get_object_or_404(Deck, id=deck_id, user=request.user, is_archived=False)
    edit_card_id = request.POST.get("edit_card_id") or request.GET.get("card_id")
    card_to_edit = None
    is_edit_mode = False

    if edit_card_id:
        card_to_edit = get_object_or_404(
            Card,
            id=edit_card_id,
            deck=deck,
            deck__user=request.user,
        )
        is_edit_mode = True

    next_target = request.POST.get("next") if request.method == "POST" else request.GET.get("next", "")

    if request.method == "POST":
        form = CardForm(request.POST, instance=card_to_edit)
        if form.is_valid():
            card = form.save(commit=False)
            card.deck = deck
            card.save()

            if is_edit_mode:
                messages.success(request, "Flashcard updated.")
            else:
                messages.success(request, "Flashcard created.")

            if next_target == "study":
                return redirect("study", deck_id=deck.id)
            return redirect("decks")
    else:
        form = CardForm(instance=card_to_edit)

    return render(request, "new_flashcard.html", {
        "deck": deck,
        "form": form,
        "is_edit_mode": is_edit_mode,
        "edit_card": card_to_edit,
        "next_target": next_target,
    })


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
@require_POST
def delete_flashcard(request, deck_id, card_id):
    """Delete a flashcard from study mode and return the next due card."""

    deck = get_object_or_404(Deck, id=deck_id, user=request.user, is_archived=False)
    card = get_object_or_404(Card, id=card_id, deck=deck, deck__user=request.user)

    card.delete()

    now = timezone.localtime()
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    due_filter = Q(cardsrs__due_at__lte=end_of_today) | Q(cardsrs__isnull=True)

    next_card = (
        Card.objects.filter(deck_id=deck_id, status="active")
        .filter(due_filter)
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
    folder_id = deck.folder_id
    deck.delete()

    if folder_id:
        folder = Folder.objects.filter(id=folder_id, user=request.user).first()
        folder_still_has_decks = Deck.objects.filter(
            user=request.user,
            is_archived=False,
            folder_id=folder_id,
        ).exists()
        if folder and not folder_still_has_decks:
            folder.delete()

    messages.success(request, f"NerDeck '{title}' deleted.")
    return redirect("decks")


@login_required
@require_POST
def rename_deck(request):
    """Rename a deck from the decks list inline editor."""

    deck_id = request.POST.get("deck_id")
    new_title = request.POST.get("title", "").strip()

    if not deck_id:
        messages.error(request, "Could not determine which NerDeck to rename.")
        return redirect("decks")

    deck = Deck.objects.filter(
        user=request.user,
        id=deck_id,
        is_archived=False,
    ).first()
    if not deck:
        messages.error(request, "NerDeck not found.")
        return redirect("decks")

    if not new_title:
        messages.error(request, "Please provide a valid NerDeck name.")
        return redirect("decks")

    if len(new_title) > 255:
        messages.error(request, "NerDeck name is too long.")
        return redirect("decks")

    if new_title == deck.title:
        return redirect("decks")

    deck.title = new_title
    deck.save(update_fields=["title"])
    messages.success(request, f"NerDeck renamed to '{new_title}'.")
    return redirect("decks")


@login_required
@require_POST
def rename_folder(request):
    """Rename a folder from the decks list inline editor."""

    folder_id = request.POST.get("folder_id")
    new_name = request.POST.get("name", "").strip()
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if not folder_id:
        if is_ajax:
            return JsonResponse(
                {"ok": False, "error": "Could not determine which folder to rename."},
                status=400,
            )
        messages.error(request, "Could not determine which folder to rename.")
        return redirect("decks")

    folder = Folder.objects.filter(
        user=request.user,
        id=folder_id,
    ).first()
    if not folder:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Folder not found."}, status=404)
        messages.error(request, "Folder not found.")
        return redirect("decks")

    if not new_name:
        if is_ajax:
            return JsonResponse(
                {"ok": False, "error": "Please provide a valid folder name."},
                status=400,
            )
        messages.error(request, "Please provide a valid folder name.")
        return redirect("decks")

    if len(new_name) > 255:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Folder name is too long."}, status=400)
        messages.error(request, "Folder name is too long.")
        return redirect("decks")

    if new_name == folder.name:
        if is_ajax:
            return JsonResponse(
                {"ok": True, "folder": {"id": folder.id, "name": folder.name}}
            )
        return redirect("decks")

    folder.name = new_name
    folder.save(update_fields=["name"])
    if is_ajax:
        return JsonResponse({"ok": True, "folder": {"id": folder.id, "name": folder.name}})
    messages.success(request, f"Folder renamed to '{new_name}'.")
    return redirect("decks")


def _build_folder_name(source_title: str, target_title: str) -> str:
    """Build a compact default folder name from two deck titles."""

    base = f"{target_title} + {source_title}"
    if len(base) <= 255:
        return base
    return base[:255]


@login_required
@require_POST
def organize_decks(request):
    """Assign decks to a folder based on drag-and-drop from the decks table."""

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    source_id = payload.get("source_deck_id")
    target_id = payload.get("target_deck_id")
    target_folder_id = payload.get("target_folder_id")
    target_root = bool(payload.get("target_root"))

    if not source_id:
        return JsonResponse(
            {"ok": False, "error": "Source deck id is required."},
            status=400,
        )

    if target_id and target_folder_id:
        return JsonResponse(
            {"ok": False, "error": "Provide either target deck id or target folder id."},
            status=400,
        )

    if target_root and (target_id or target_folder_id):
        return JsonResponse(
            {"ok": False, "error": "Root drop cannot include target deck or folder id."},
            status=400,
        )

    if not target_id and not target_folder_id and not target_root:
        return JsonResponse(
            {"ok": False, "error": "Target deck id, target folder id, or target_root is required."},
            status=400,
        )

    if target_id and str(source_id) == str(target_id):
        return JsonResponse(
            {"ok": False, "error": "Source and target decks must be different."},
            status=400,
        )

    source_deck = Deck.objects.filter(
        id=source_id,
        user=request.user,
        is_archived=False,
    ).select_related("folder").first()
    if not source_deck:
        return JsonResponse({"ok": False, "error": "Deck not found."}, status=404)

    source_folder_id_before = source_deck.folder_id
    deleted_empty_folder_id = None

    with transaction.atomic():
        if target_root:
            # Move deck out of any folder and make it the first ungrouped deck.
            min_ungrouped_sort = (
                Deck.objects.filter(
                    user=request.user,
                    is_archived=False,
                    folder__isnull=True,
                )
                .exclude(id=source_deck.id)
                .order_by("sort_order")
                .values_list("sort_order", flat=True)
                .first()
            )
            source_deck.folder = None
            source_deck.sort_order = (min_ungrouped_sort - 1) if min_ungrouped_sort is not None else 0
            source_deck.save(update_fields=["folder", "sort_order"])
            destination_folder = None
        elif target_folder_id:
            destination_folder = Folder.objects.filter(
                id=target_folder_id,
                user=request.user,
            ).first()
            if not destination_folder:
                return JsonResponse({"ok": False, "error": "Folder not found."}, status=404)

            if source_deck.folder_id != destination_folder.id:
                source_deck.folder = destination_folder
                source_deck.save(update_fields=["folder"])
        else:
            target_deck = Deck.objects.filter(
                id=target_id,
                user=request.user,
                is_archived=False,
            ).select_related("folder").first()

            if not target_deck:
                return JsonResponse({"ok": False, "error": "Deck not found."}, status=404)

            destination_folder = target_deck.folder or source_deck.folder

            # No existing folder on either side: create one and move both decks in.
            if destination_folder is None:
                destination_folder = Folder.objects.create(
                    user=request.user,
                    name=_build_folder_name(source_deck.title, target_deck.title),
                )

            # If both decks belong to different folders, merge source folder into target folder.
            source_folder = source_deck.folder
            target_folder = target_deck.folder
            if (
                source_folder
                and target_folder
                and source_folder.id != target_folder.id
            ):
                Deck.objects.filter(folder=source_folder, user=request.user).update(
                    folder=target_folder
                )
                destination_folder = target_folder
                if not Deck.objects.filter(folder=source_folder).exists():
                    source_folder.delete()

            if source_deck.folder_id != destination_folder.id:
                source_deck.folder = destination_folder
                source_deck.save(update_fields=["folder"])

            if target_deck.folder_id != destination_folder.id:
                target_deck.folder = destination_folder
                target_deck.save(update_fields=["folder"])

        # If the source deck moved out of its original folder, delete that folder if now empty.
        if source_folder_id_before and source_deck.folder_id != source_folder_id_before:
            source_folder = Folder.objects.filter(id=source_folder_id_before, user=request.user).first()
            folder_still_has_decks = Deck.objects.filter(
                user=request.user,
                is_archived=False,
                folder_id=source_folder_id_before,
            ).exists()
            if source_folder and not folder_still_has_decks:
                source_folder.delete()
                deleted_empty_folder_id = source_folder_id_before

    response_payload = {"ok": True}
    if destination_folder is not None:
        response_payload["folder"] = {
            "id": destination_folder.id,
            "name": destination_folder.name,
        }
    else:
        response_payload["folder"] = None
    response_payload["deleted_empty_folder_id"] = deleted_empty_folder_id

    return JsonResponse(response_payload)


@login_required
@require_POST
def merge_folders(request):
    """Merge one folder into another and create a freshly named destination folder."""

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    source_folder_id = payload.get("source_folder_id")
    target_folder_id = payload.get("target_folder_id")
    new_name = (payload.get("name") or "").strip()

    if not source_folder_id or not target_folder_id:
        return JsonResponse(
            {"ok": False, "error": "Both source and target folder ids are required."},
            status=400,
        )

    if str(source_folder_id) == str(target_folder_id):
        return JsonResponse({"ok": False, "error": "Folders must be different."}, status=400)

    if not new_name:
        return JsonResponse({"ok": False, "error": "Folder name is required."}, status=400)

    if len(new_name) > 255:
        return JsonResponse({"ok": False, "error": "Folder name is too long."}, status=400)

    source_folder = Folder.objects.filter(id=source_folder_id, user=request.user).first()
    target_folder = Folder.objects.filter(id=target_folder_id, user=request.user).first()

    if not source_folder or not target_folder:
        return JsonResponse({"ok": False, "error": "Folder not found."}, status=404)

    with transaction.atomic():
        merged_folder = Folder.objects.create(user=request.user, name=new_name)
        Deck.objects.filter(
            user=request.user,
            folder_id__in=[source_folder.id, target_folder.id],
        ).update(folder=merged_folder)

        source_folder.delete()
        target_folder.delete()

    return JsonResponse(
        {"ok": True, "folder": {"id": merged_folder.id, "name": merged_folder.name}}
    )


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
