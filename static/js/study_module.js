import { reviewCardTwoButtons } from "./cards.js";

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

const cardTextEl = document.getElementById("card-text");
const showButtonEl = document.getElementById("show-button");
const editButtonEl = document.getElementById("edit-button");
const deleteButtonEl = document.getElementById("delete-button");
const deleteModalEl = document.getElementById("deleteCardModal");
const confirmDeleteButtonEl = document.getElementById("confirmDeleteButton");
const rightButtonEl = document.getElementById("right-button");
const wrongButtonEl = document.getElementById("wrong-button");
const messageEl = document.getElementById("review-message");
const REVIEW_MESSAGE_VISIBLE_MS = 1500;
const RIGHT_FEEDBACK_DELAY_MS = REVIEW_MESSAGE_VISIBLE_MS;

if (
  cardTextEl &&
  showButtonEl &&
  editButtonEl &&
  deleteButtonEl &&
  deleteModalEl &&
  confirmDeleteButtonEl &&
  rightButtonEl &&
  wrongButtonEl
) {
  const deleteModal = window.bootstrap ? new window.bootstrap.Modal(deleteModalEl) : null;
  let isAnswerInFlight = false;
  let reviewMessageTimeoutId = null;
  const cardState = {
    id: Number(cardTextEl.dataset.cardId),
    step: Number(cardTextEl.dataset.step || "0"),
    dueAt: cardTextEl.dataset.dueAt || null,
  };

  let frontText = cardTextEl.dataset.front || "";
  let backText = cardTextEl.dataset.back || "";

  function updateEditUrl() {
    const baseEditUrl = document.body.dataset.editBaseUrl;
    if (!baseEditUrl || !cardState.id) return;

    const params = new URLSearchParams({
      card_id: String(cardState.id),
      next: "study",
    });
    editButtonEl.dataset.href = `${baseEditUrl}?${params.toString()}`;
  }

  function showFront() {
    cardTextEl.textContent = frontText;
    showButtonEl.classList.remove("d-none");
    editButtonEl.classList.add("d-none");
    deleteButtonEl.classList.add("d-none");
    rightButtonEl.classList.add("d-none");
    wrongButtonEl.classList.add("d-none");
  }

  function showBack() {
    cardTextEl.textContent = backText;
    showButtonEl.classList.add("d-none");
    updateEditUrl();
    editButtonEl.classList.remove("d-none");
    deleteButtonEl.classList.remove("d-none");
    rightButtonEl.classList.remove("d-none");
    wrongButtonEl.classList.remove("d-none");
  }

  function moveToNextCard(next) {
    if (next) {
      cardState.id = next.id;
      cardState.step = Number.isFinite(next.step) ? next.step : 0;
      cardState.dueAt = next.due_at || null;

      frontText = next.front_text;
      backText = next.back_text;

      cardTextEl.dataset.cardId = String(next.id);
      cardTextEl.dataset.front = frontText;
      cardTextEl.dataset.back = backText;
      cardTextEl.dataset.step = String(cardState.step);
      cardTextEl.dataset.dueAt = cardState.dueAt || "";

      showFront();
      return;
    }

    showButtonEl.classList.add("d-none");
    editButtonEl.classList.add("d-none");
    deleteButtonEl.classList.add("d-none");
    rightButtonEl.classList.add("d-none");
    wrongButtonEl.classList.add("d-none");
    cardTextEl.textContent = " Well done you have completed all the cards! See you tomorrow!";
    if (messageEl) {
      messageEl.textContent = "";
    }
  }

  function wait(ms) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, ms);
    });
  }

  function showTransientMessage(text, durationMs = REVIEW_MESSAGE_VISIBLE_MS) {
    if (!messageEl || !text) return;
    if (reviewMessageTimeoutId) {
      window.clearTimeout(reviewMessageTimeoutId);
      reviewMessageTimeoutId = null;
    }
    messageEl.textContent = text;
    reviewMessageTimeoutId = window.setTimeout(() => {
      messageEl.textContent = "";
      reviewMessageTimeoutId = null;
    }, durationMs);
  }

  function clearReviewMessage() {
    if (!messageEl) return;
    if (reviewMessageTimeoutId) {
      window.clearTimeout(reviewMessageTimeoutId);
      reviewMessageTimeoutId = null;
    }
    messageEl.textContent = "";
  }

  function setAnswerActionDisabled(disabled) {
    rightButtonEl.disabled = disabled;
    wrongButtonEl.disabled = disabled;
    editButtonEl.disabled = disabled;
    deleteButtonEl.disabled = disabled;
  }

  async function handleAnswer(isRight) {
    if (isAnswerInFlight) return;
    isAnswerInFlight = true;
    setAnswerActionDisabled(true);

    const { card: updatedCard, message } = reviewCardTwoButtons(cardState, isRight);
    showTransientMessage(message);

    const deckId = Number(document.body.dataset.deckId);
    const csrftoken = getCookie("csrftoken");
    const delayPromise = isRight ? wait(RIGHT_FEEDBACK_DELAY_MS) : Promise.resolve();
    let resp = null;

    try {
      resp = await fetch(`/decks/${deckId}/review/answer/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken || "",
        },
        body: JSON.stringify({
          card_id: cardState.id,
          is_right: isRight,
          step: updatedCard.step,
          due_at: updatedCard.dueAt,
        }),
      });
    } catch (e) {
      console.error("Failed to save review result", e);
      resp = null;
    }

    await delayPromise;

    try {
      if (!resp || !resp.ok) {
        showFront();
        return;
      }

      if (isRight) {
        const data = await resp.json();
        clearReviewMessage();
        moveToNextCard(data.next_card);
        return;
      }

      cardState.step = updatedCard.step;
      cardState.dueAt = updatedCard.dueAt;
      showFront();
    } finally {
      setAnswerActionDisabled(false);
      isAnswerInFlight = false;
    }
  }

  showButtonEl.addEventListener("click", () => {
    showBack();
  });

  editButtonEl.addEventListener("click", () => {
    const href = editButtonEl.dataset.href;
    if (href) {
      window.location.assign(href);
    }
  });

  deleteButtonEl.addEventListener("click", () => {
    if (deleteModal) {
      deleteModal.show();
    }
  });

  confirmDeleteButtonEl.addEventListener("click", async () => {
    const deckId = Number(document.body.dataset.deckId);
    const csrftoken = getCookie("csrftoken");
    confirmDeleteButtonEl.disabled = true;

    try {
      const resp = await fetch(`/decks/${deckId}/cards/${cardState.id}/delete/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken || "",
        },
      });

      if (!resp.ok) {
        throw new Error(`Delete failed with status ${resp.status}`);
      }

      const data = await resp.json();
      if (deleteModal) {
        deleteModal.hide();
      }
      moveToNextCard(data.next_card);
      clearReviewMessage();
      showTransientMessage("Flashcard successfully deleted.", 3000);
    } catch (e) {
      console.error("Failed to delete flashcard", e);
      clearReviewMessage();
      showTransientMessage("Could not delete this flashcard. Please try again.");
    } finally {
      confirmDeleteButtonEl.disabled = false;
    }
  });

  rightButtonEl.addEventListener("click", () => {
    handleAnswer(true);
  });

  wrongButtonEl.addEventListener("click", () => {
    handleAnswer(false);
  });

  showFront();
}
