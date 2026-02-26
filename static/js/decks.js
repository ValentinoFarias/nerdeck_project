// Modal for New Deck and New Folder forms

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("newDeckNameInput");
  const confirmBtn = document.getElementById("confirmCreateDeckBtn");
  const hiddenTitle = document.getElementById("deck-title-input");
  const form = document.getElementById("create-deck-form");
  const modalEl = document.getElementById("createDeckModal");
  const deleteDeckModalEl = document.getElementById("deleteDeckModal");
  const deleteDeckConfirmModalEl = document.getElementById("deleteDeckConfirmModal");
  const deleteDeckConfirmNameEl = document.getElementById("deleteDeckConfirmName");
  const confirmDeleteDeckBtn = document.getElementById("confirmDeleteDeckBtn");
  const deleteDeckForms = document.querySelectorAll(".delete-deck-form");

  if (confirmBtn && input && hiddenTitle && form && modalEl) {
    confirmBtn.addEventListener("click", () => {
      const name = input.value.trim();
      if (!name) return;
      hiddenTitle.value = name;
      form.submit();
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        confirmBtn.click();
      }
    });
  }

  if (!deleteDeckForms.length) {
    return;
  }

  function getDeckNameFromForm(deleteDeckForm) {
    return (
      deleteDeckForm.querySelector(".delete-deck-name")?.textContent?.trim() ||
      "this deck"
    );
  }

  if (
    !window.bootstrap ||
    !deleteDeckConfirmModalEl ||
    !deleteDeckConfirmNameEl ||
    !confirmDeleteDeckBtn
  ) {
    deleteDeckForms.forEach((deleteDeckForm) => {
      deleteDeckForm.addEventListener("submit", (event) => {
        const deckName = getDeckNameFromForm(deleteDeckForm);
        const shouldDelete = window.confirm(
          `Are you sure you want to delete the NerDeck "${deckName}"?`
        );
        if (!shouldDelete) {
          event.preventDefault();
        }
      });
    });
    return;
  }

  const deleteDeckPickerModal = deleteDeckModalEl
    ? window.bootstrap.Modal.getOrCreateInstance(deleteDeckModalEl)
    : null;
  const deleteDeckConfirmModal = window.bootstrap.Modal.getOrCreateInstance(
    deleteDeckConfirmModalEl
  );
  let pendingDeleteDeckForm = null;

  deleteDeckForms.forEach((deleteDeckForm) => {
    deleteDeckForm.addEventListener("submit", (event) => {
      event.preventDefault();
      pendingDeleteDeckForm = deleteDeckForm;
      deleteDeckConfirmNameEl.textContent = getDeckNameFromForm(deleteDeckForm);

      if (deleteDeckPickerModal && deleteDeckModalEl?.classList.contains("show")) {
        const showConfirmModal = () => {
          deleteDeckModalEl.removeEventListener("hidden.bs.modal", showConfirmModal);
          deleteDeckConfirmModal.show();
        };
        deleteDeckModalEl.addEventListener("hidden.bs.modal", showConfirmModal);
        deleteDeckPickerModal.hide();
        return;
      }

      deleteDeckConfirmModal.show();
    });
  });

  deleteDeckConfirmModalEl.addEventListener("show.bs.modal", () => {
    confirmDeleteDeckBtn.disabled = false;
  });

  confirmDeleteDeckBtn.addEventListener("click", () => {
    if (!pendingDeleteDeckForm) return;
    const formToSubmit = pendingDeleteDeckForm;
    pendingDeleteDeckForm = null;
    confirmDeleteDeckBtn.disabled = true;
    formToSubmit.submit();
  });

  deleteDeckConfirmModalEl.addEventListener("hidden.bs.modal", () => {
    if (!pendingDeleteDeckForm) return;
    pendingDeleteDeckForm = null;
    if (deleteDeckPickerModal) {
      deleteDeckPickerModal.show();
    }
  });
});


// Page behavior for:
// - deck row actions (study/add buttons)
// - inline deck renaming
// - folder expand/collapse
// - drag/drop deck and folder organization
document.addEventListener("DOMContentLoaded", () => {
  const radios = document.querySelectorAll(".deck-radio");
  const studyButtons = document.querySelectorAll(".study-button");
  const addButtons = document.querySelectorAll(".add-flashcard-button");
  const renameForms = document.querySelectorAll(".deck-rename-form");
  const folderRenameForms = document.querySelectorAll(".folder-rename-form");
  const deckRows = document.querySelectorAll(".deck-row");
  const folderRows = document.querySelectorAll(".folder-row");
  const folderToggles = document.querySelectorAll(".folder-toggle");
  const rootDropZone = document.querySelector(".root-drop-zone");
  const dragState = { type: null, deckId: null, folderId: null };
  const isSmallViewport = window.matchMedia("(max-width: 767.98px)").matches;

  function clearButtons() {
    // Hide all action buttons, then selectively show only for the selected deck.
    studyButtons.forEach((btn) => btn.classList.add("d-none"));
    addButtons.forEach((btn) => btn.classList.add("d-none"));
  }

  function showButtonsForDeck(deckId) {
    const studyBtn = document.querySelector(
      `.study-button[data-deck-id="${deckId}"]`
    );
    const addBtn = document.querySelector(
      `.add-flashcard-button[data-deck-id="${deckId}"]`
    );
    if (studyBtn) {
      studyBtn.classList.remove("d-none");
    }
    if (addBtn) {
      addBtn.classList.remove("d-none");
    }
  }

  if (radios.length) {
    radios.forEach((radio) => {
      radio.addEventListener("change", () => {
        if (!radio.checked) return;
        clearButtons();
        showButtonsForDeck(radio.value);
      });
    });
  }

  function startRename(form) {
    const label = form.querySelector(".deck-name-display");
    const input = form.querySelector(".deck-name-input");
    if (!label || !input) return;

    // Keep layout stable: hide label visually and overlay the input in the same spot.
    form.dataset.editing = "1";
    label.classList.add("deck-name-editing");
    input.classList.remove("d-none");
    input.focus();
    input.select();
  }

  function cancelRename(form) {
    const label = form.querySelector(".deck-name-display");
    const input = form.querySelector(".deck-name-input");
    if (!label || !input) return;

    // Revert input back to current label text and close editor.
    input.value = label.textContent.trim();
    form.dataset.editing = "0";
    input.classList.add("d-none");
    label.classList.remove("deck-name-editing");
  }

  function saveRename(form) {
    if (form.dataset.submitting === "1") return;

    const label = form.querySelector(".deck-name-display");
    const input = form.querySelector(".deck-name-input");
    if (!label || !input) return;

    const current = label.textContent.trim();
    const next = input.value.trim();

    // Do not submit empty or unchanged values.
    if (!next || next === current) {
      cancelRename(form);
      return;
    }

    input.value = next;
    form.dataset.submitting = "1";
    form.submit();
  }

  renameForms.forEach((form) => {
    const label = form.querySelector(".deck-name-display");
    const input = form.querySelector(".deck-name-input");
    if (!label || !input) return;

    label.addEventListener("click", () => {
      startRename(form);
    });

    label.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        startRename(form);
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveRename(form);
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        cancelRename(form);
      }
    });

    input.addEventListener("blur", () => {
      saveRename(form);
    });
  });

  function startFolderRename(form) {
    const label = form.querySelector(".folder-name-display");
    const input = form.querySelector(".folder-name-input");
    if (!label || !input) return;

    form.dataset.editing = "1";
    label.classList.add("folder-name-editing");
    input.classList.remove("d-none");
    input.focus();
    input.select();
  }

  function cancelFolderRename(form) {
    const label = form.querySelector(".folder-name-display");
    const input = form.querySelector(".folder-name-input");
    if (!label || !input) return;

    input.value = label.textContent.trim();
    form.dataset.editing = "0";
    input.classList.add("d-none");
    label.classList.remove("folder-name-editing");
  }

  function saveFolderRename(form) {
    if (form.dataset.submitting === "1") return Promise.resolve();

    const label = form.querySelector(".folder-name-display");
    const input = form.querySelector(".folder-name-input");
    const folderIdInput = form.querySelector('input[name="folder_id"]');
    if (!label || !input || !folderIdInput) return Promise.resolve();

    const current = label.textContent.trim();
    const next = input.value.trim();

    if (!next || next === current) {
      cancelFolderRename(form);
      return Promise.resolve();
    }

    const folderId = folderIdInput.value;
    const formData = new FormData(form);
    formData.set("name", next);
    input.value = next;
    form.dataset.submitting = "1";

    return fetch(form.action, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: formData,
    })
      .then((response) => response.json().then((payload) => ({ response, payload })))
      .then(({ response, payload }) => {
        if (!response.ok || !payload.ok) {
          const error = payload.error || "Could not rename folder.";
          throw new Error(error);
        }

        const finalName = payload.folder?.name || next;
        const finalFolderId = String(payload.folder?.id || folderId);
        label.textContent = finalName;
        cancelFolderRename(form);

        const allFolderLabels = document.querySelectorAll(
          `.folder-row[data-folder-id="${finalFolderId}"] .folder-name-display`
        );
        allFolderLabels.forEach((node) => {
          node.textContent = finalName;
        });

        const allFolderBadges = document.querySelectorAll(
          `.deck-row[data-folder-id="${finalFolderId}"] .deck-folder-badge`
        );
        allFolderBadges.forEach((node) => {
          node.textContent = finalName;
        });
      })
      .catch((error) => {
        window.alert(error.message || "Could not rename folder.");
        cancelFolderRename(form);
      })
      .finally(() => {
        form.dataset.submitting = "0";
      });
  }

  folderRenameForms.forEach((form) => {
    const label = form.querySelector(".folder-name-display");
    const input = form.querySelector(".folder-name-input");
    if (!label || !input) return;

    label.addEventListener("click", () => {
      startFolderRename(form);
    });

    label.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        startFolderRename(form);
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveFolderRename(form);
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        cancelFolderRename(form);
      }
    });

    input.addEventListener("blur", () => {
      saveFolderRename(form);
    });
  });

  function toggleFolder(folderId) {
    // Folder rows are parent rows; deck rows under that folder are hidden/shown.
    const deckRowsInFolder = document.querySelectorAll(
      `.deck-row[data-folder-id="${folderId}"]`
    );
    const toggle = document.querySelector(`.folder-toggle[data-folder-id="${folderId}"]`);
    if (!deckRowsInFolder.length || !toggle) return;

    const willExpand = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", willExpand ? "true" : "false");

    const arrow = toggle.querySelector(".folder-arrow");
    if (arrow) {
      arrow.textContent = willExpand ? "▼" : "▶";
    }

    deckRowsInFolder.forEach((row) => {
      row.classList.toggle("d-none", !willExpand);
    });
  }

  folderToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const folderId = toggle.dataset.folderId;
      if (!folderId) return;
      toggleFolder(folderId);
    });
  });

  function getCsrfToken() {
    // Read Django CSRF token from cookies for fetch POST requests.
    const cookie = document.cookie
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith("csrftoken="));

    if (!cookie) return "";
    return decodeURIComponent(cookie.split("=")[1]);
  }

  if (isSmallViewport) {
    return;
  }

  async function organizeDecks(sourceDeckId, targetDeckId, targetFolderId, targetRoot = false) {
    // Generic move endpoint:
    // - deck -> deck
    // - deck -> folder
    // - deck -> root (ungroup)
    const payload = { source_deck_id: sourceDeckId };
    if (targetDeckId) payload.target_deck_id = targetDeckId;
    if (targetFolderId) payload.target_folder_id = targetFolderId;
    if (targetRoot) payload.target_root = true;

    const response = await fetch("/decks/organize/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    const responsePayload = await response.json().catch(() => ({}));
    if (!response.ok || !responsePayload.ok) {
      const error = responsePayload.error || "Could not organize NerDecks.";
      throw new Error(error);
    }
    return responsePayload;
  }

  async function mergeFolders(sourceFolderId, targetFolderId, name) {
    // Merge two folders into a brand-new folder with a user-provided name.
    const response = await fetch("/decks/folders/merge/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        source_folder_id: sourceFolderId,
        target_folder_id: targetFolderId,
        name,
      }),
    });

    const responsePayload = await response.json().catch(() => ({}));
    if (!response.ok || !responsePayload.ok) {
      const error = responsePayload.error || "Could not merge folders.";
      throw new Error(error);
    }
  }

  function clearDropStyles() {
    // Visual cleanup for highlighted drop targets.
    deckRows.forEach((row) => row.classList.remove("deck-row-drop-target"));
    folderRows.forEach((row) => row.classList.remove("folder-row-drop-target"));
    if (rootDropZone) rootDropZone.classList.remove("root-drop-zone-drop-target");
  }

  function resetDragState() {
    dragState.type = null;
    dragState.deckId = null;
    dragState.folderId = null;
    clearDropStyles();
    deckRows.forEach((row) => row.classList.remove("deck-row-dragging"));
    folderRows.forEach((row) => row.classList.remove("folder-row-dragging"));
  }

  function moveDeckToUngroupedTop(deckId) {
    const row = document.querySelector(`.deck-row[data-deck-id="${deckId}"]`);
    if (!row) return;

    row.dataset.folderId = "";
    row.classList.remove("d-none");

    const deckNameWrap = row.querySelector("td .d-flex");
    if (deckNameWrap) {
      deckNameWrap.classList.remove("ps-4");
    }

    const folderCell = row.children[3];
    if (folderCell) {
      folderCell.classList.add("text-muted");
      folderCell.textContent = "-";
    }

    const tbody = row.closest("tbody");
    if (!tbody) return;

    const rootZone = tbody.querySelector(".root-drop-zone");
    if (rootZone) {
      tbody.insertBefore(row, rootZone);
      return;
    }

    const firstUngrouped = Array.from(tbody.querySelectorAll(".deck-row")).find(
      (deckRow) => !deckRow.dataset.folderId
    );
    if (firstUngrouped && firstUngrouped !== row) {
      tbody.insertBefore(row, firstUngrouped);
    } else {
      tbody.appendChild(row);
    }
  }

  function moveDeckToFolder(deckId, targetFolderId, targetFolderName) {
    if (!targetFolderId) return;

    const row = document.querySelector(`.deck-row[data-deck-id="${deckId}"]`);
    if (!row) return;

    row.dataset.folderId = String(targetFolderId);

    const deckNameWrap = row.querySelector("td .d-flex");
    if (deckNameWrap) {
      deckNameWrap.classList.add("ps-4");
    }

    const folderCell = row.children[3];
    if (folderCell) {
      folderCell.classList.remove("text-muted");
      folderCell.textContent = "";
      const badge = document.createElement("span");
      badge.className = "badge text-bg-light border deck-folder-badge";
      badge.textContent = targetFolderName || "";
      folderCell.appendChild(badge);
    }

    const tbody = row.closest("tbody");
    if (!tbody) return;

    const targetFolderDeckRows = Array.from(
      tbody.querySelectorAll(`.deck-row[data-folder-id="${targetFolderId}"]`)
    ).filter((deckRow) => deckRow !== row);
    const targetFolderRow = tbody.querySelector(`.folder-row[data-folder-id="${targetFolderId}"]`);

    if (targetFolderDeckRows.length) {
      targetFolderDeckRows[targetFolderDeckRows.length - 1].insertAdjacentElement("afterend", row);
    } else if (targetFolderRow) {
      targetFolderRow.insertAdjacentElement("afterend", row);
    }

    const targetToggle = document.querySelector(`.folder-toggle[data-folder-id="${targetFolderId}"]`);
    const isExpanded = targetToggle?.getAttribute("aria-expanded") === "true";
    row.classList.toggle("d-none", !isExpanded);
  }

  function removeFolderGroup(folderId) {
    if (!folderId) return;
    const normalizedFolderId = String(folderId);

    const folderRow = document.querySelector(`.folder-row[data-folder-id="${normalizedFolderId}"]`);
    if (folderRow) {
      folderRow.remove();
    }

    document
      .querySelectorAll(`.deck-row[data-folder-id="${normalizedFolderId}"]`)
      .forEach((deckRow) => deckRow.remove());
  }

  function removeFolderIfEmpty(folderId) {
    if (!folderId) return;
    const normalizedFolderId = String(folderId);
    const remainingDeckRows = document.querySelectorAll(
      `.deck-row[data-folder-id="${normalizedFolderId}"]`
    );
    if (!remainingDeckRows.length) {
      removeFolderGroup(normalizedFolderId);
    }
  }

  function cleanupSourceFolderAfterMove(sourceFolderId, deletedEmptyFolderId) {
    if (!sourceFolderId) return;
    const normalizedSourceFolderId = String(sourceFolderId);
    if (
      deletedEmptyFolderId &&
      String(deletedEmptyFolderId) === normalizedSourceFolderId
    ) {
      removeFolderGroup(normalizedSourceFolderId);
      return;
    }
    removeFolderIfEmpty(normalizedSourceFolderId);
  }

  function getDropSource(event) {
    // Prefer drag source encoded in dataTransfer (reliable across events/browsers).
    // Fallback to in-memory dragState if needed.
    const raw = event.dataTransfer?.getData("text/plain") || "";
    if (raw.startsWith("folder:")) {
      return { type: "folder", id: raw.slice("folder:".length) };
    }
    if (raw.startsWith("deck:")) {
      return { type: "deck", id: raw.slice("deck:".length) };
    }

    if (dragState.type === "folder") {
      return { type: "folder", id: dragState.folderId };
    }
    if (dragState.type === "deck") {
      return { type: "deck", id: dragState.deckId };
    }
    return { type: null, id: null };
  }

  function startFolderDrag(folderId, row, event) {
    if (!folderId) return;
    dragState.type = "folder";
    dragState.folderId = folderId;
    dragState.deckId = null;
    row.classList.add("folder-row-dragging");
    event.dataTransfer.effectAllowed = "move";
    // Encoding drag type/id lets drop handlers decide between deck-vs-folder flows.
    event.dataTransfer.setData("text/plain", `folder:${folderId}`);
  }

  deckRows.forEach((row) => {
    row.addEventListener("dragstart", (event) => {
      const interactiveTarget = event.target.closest(
        "a, button, input, textarea, .deck-name-input, .deck-name-display"
      );
      if (interactiveTarget) {
        event.preventDefault();
        return;
      }

      dragState.type = "deck";
      dragState.deckId = row.dataset.deckId;
      dragState.folderId = row.dataset.folderId || null;
      row.classList.add("deck-row-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", `deck:${dragState.deckId || ""}`);
    });

    row.addEventListener("dragend", () => {
      resetDragState();
    });

    row.addEventListener("dragover", (event) => {
      if (dragState.type !== "deck") return;
      if (!dragState.deckId || dragState.deckId === row.dataset.deckId) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      row.classList.add("deck-row-drop-target");
    });

    row.addEventListener("dragleave", () => {
      row.classList.remove("deck-row-drop-target");
    });

    row.addEventListener("drop", async (event) => {
      event.preventDefault();
      row.classList.remove("deck-row-drop-target");
      const source = getDropSource(event);

      // Folder dropped on a deck row inside a folder: treat as folder merge.
      if (source.type === "folder") {
        const targetFolderId = row.dataset.folderId;
        if (!source.id || !targetFolderId || source.id === targetFolderId) {
          return;
        }
        try {
          const name = window.prompt("Name for the new folder:");
          if (!name) return;
          await mergeFolders(source.id, targetFolderId, name.trim());
          window.location.reload();
        } catch (error) {
          window.alert(error.message);
        }
        return;
      }

      // Otherwise only deck->deck is valid on deck rows.
      if (source.type !== "deck") return;

      const targetDeckId = row.dataset.deckId;
      if (!source.id || !targetDeckId || source.id === targetDeckId) {
        return;
      }

      try {
        await organizeDecks(source.id, targetDeckId, null);
        window.location.reload();
      } catch (error) {
        window.alert(error.message);
      }
    });
  });

  folderRows.forEach((row) => {
    row.addEventListener("dragstart", (event) => {
      startFolderDrag(row.dataset.folderId, row, event);
    });

    row.addEventListener("dragend", () => {
      resetDragState();
    });

    row.addEventListener("dragover", (event) => {
      const targetFolderId = row.dataset.folderId;
      if (!targetFolderId) return;
      if (dragState.type === "folder" && dragState.folderId === targetFolderId) return;
      if (dragState.type !== "folder" && dragState.type !== "deck") return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      row.classList.add("folder-row-drop-target");
    });

    row.addEventListener("dragleave", () => {
      row.classList.remove("folder-row-drop-target");
    });

    row.addEventListener("drop", async (event) => {
      event.preventDefault();
      row.classList.remove("folder-row-drop-target");
      const source = getDropSource(event);

      const targetFolderId = row.dataset.folderId;
      if (!targetFolderId) return;

      try {
        // Deck dropped on folder row: move deck into this folder.
        if (source.type === "deck") {
          if (!source.id) return;
          const sourceRow = document.querySelector(
            `.deck-row[data-deck-id="${source.id}"]`
          );
          const sourceFolderId = sourceRow?.dataset.folderId || null;
          if (sourceFolderId && String(sourceFolderId) === String(targetFolderId)) {
            return;
          }

          const organizePayload = await organizeDecks(source.id, null, targetFolderId);
          const targetFolderName =
            organizePayload.folder?.name ||
            row.querySelector(".folder-name-display")?.textContent?.trim() ||
            "";
          moveDeckToFolder(source.id, targetFolderId, targetFolderName);
          cleanupSourceFolderAfterMove(
            sourceFolderId,
            organizePayload.deleted_empty_folder_id
          );
          return;
        }

        // Folder dropped on folder row: prompt user and merge into a new folder.
        if (source.type === "folder") {
          if (!source.id || source.id === targetFolderId) return;
          const name = window.prompt("Name for the new folder:");
          if (!name) return;
          await mergeFolders(source.id, targetFolderId, name.trim());
          window.location.reload();
        }
      } catch (error) {
        window.alert(error.message);
      }
    });
  });

  folderToggles.forEach((toggle) => {
    toggle.setAttribute("draggable", "true");
    toggle.addEventListener("dragstart", (event) => {
      const row = toggle.closest(".folder-row");
      if (!row) return;
      startFolderDrag(row.dataset.folderId, row, event);
      event.stopPropagation();
    });
    toggle.addEventListener("dragend", () => {
      resetDragState();
    });
  });

  if (rootDropZone) {
    rootDropZone.addEventListener("dragover", (event) => {
      if (dragState.type !== "deck" || !dragState.deckId) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      rootDropZone.classList.add("root-drop-zone-drop-target");
    });

    rootDropZone.addEventListener("dragleave", () => {
      rootDropZone.classList.remove("root-drop-zone-drop-target");
    });

    rootDropZone.addEventListener("drop", async (event) => {
      event.preventDefault();
      rootDropZone.classList.remove("root-drop-zone-drop-target");

      const source = getDropSource(event);
      if (source.type !== "deck" || !source.id) return;

      try {
        const sourceRow = document.querySelector(`.deck-row[data-deck-id="${source.id}"]`);
        const sourceFolderId = sourceRow?.dataset.folderId || null;
        const organizePayload = await organizeDecks(source.id, null, null, true);
        moveDeckToUngroupedTop(source.id);
        cleanupSourceFolderAfterMove(
          sourceFolderId,
          organizePayload.deleted_empty_folder_id
        );
      } catch (error) {
        window.alert(error.message);
      }
    });
  }
});
