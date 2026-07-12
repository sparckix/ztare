import React from "react";
import { createPortal } from "react-dom";

const modalStack = [];
const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function visibleFocusable(container) {
  if (!container) return [];
  return [...container.querySelectorAll(FOCUSABLE)].filter((node) =>
    !node.hidden && node.getAttribute("aria-hidden") !== "true" && node.getClientRects().length > 0);
}

/** Locks background scroll, traps focus, restores the trigger, and closes only the top modal. */
export function useModalBehavior({ open, onClose, initialFocusRef, onKeyDown }) {
  const dialogRef = React.useRef(null);
  const closeRef = React.useRef(onClose);
  const initialRef = React.useRef(initialFocusRef);
  const keyHandlerRef = React.useRef(onKeyDown);
  closeRef.current = onClose;
  initialRef.current = initialFocusRef;
  keyHandlerRef.current = onKeyDown;

  React.useEffect(() => {
    if (!open) return undefined;
    const token = Symbol("modal");
    const previousActive = document.activeElement;
    modalStack.push(token);
    document.body.classList.add("modal-open");

    const focusInitial = () => {
      const requested = initialRef.current && initialRef.current.current;
      const target = requested || visibleFocusable(dialogRef.current)[0] || dialogRef.current;
      if (target && typeof target.focus === "function") target.focus({ preventScroll: true });
    };
    const frame = window.requestAnimationFrame(focusInitial);
    const handleKeyDown = (event) => {
      if (modalStack[modalStack.length - 1] !== token) return;
      if (keyHandlerRef.current && keyHandlerRef.current(event)) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current && closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = visibleFocusable(dialogRef.current);
      if (!focusable.length) {
        event.preventDefault();
        dialogRef.current && dialogRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialogRef.current?.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown, true);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("keydown", handleKeyDown, true);
      const index = modalStack.lastIndexOf(token);
      if (index >= 0) modalStack.splice(index, 1);
      if (!modalStack.length) document.body.classList.remove("modal-open");
      if (previousActive && previousActive.isConnected && typeof previousActive.focus === "function") {
        window.requestAnimationFrame(() => previousActive.focus({ preventScroll: true }));
      }
    };
  }, [open]);

  return dialogRef;
}

export function ModalPortal({ children }) {
  return children ? createPortal(children, document.body) : null;
}
