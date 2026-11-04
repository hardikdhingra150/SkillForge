import { X } from 'lucide-react';
import { useEffect, useRef } from 'react';

export function Modal({
  children,
  title,
  eyebrow,
  onClose,
  className = '',
}) {
  const ref = useRef();

  useEffect(() => {
    const before = document.activeElement;
    const previous = document.body.style.overflow;

    document.body.style.overflow = 'hidden';

    const node = ref.current;

    (
      node.querySelector('input')
      || node.querySelector('button')
    )?.focus();

    const handle = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }

      if (event.key === 'Tab') {
        const items = [
          ...node.querySelectorAll(
            'button:not(:disabled),input,textarea,select,[tabindex="0"]',
          ),
        ];

        if (
          event.shiftKey
          && document.activeElement === items[0]
        ) {
          event.preventDefault();
          items.at(-1)?.focus();
        } else if (
          !event.shiftKey
          && document.activeElement === items.at(-1)
        ) {
          event.preventDefault();
          items[0]?.focus();
        }
      }
    };

    document.addEventListener('keydown', handle);

    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener('keydown', handle);
      before?.focus();
    };
    // Mount-only on purpose: the focus trap and scroll lock live for the modal's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        ref={ref}
        className={`modal ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2 id="modal-title">{title}</h2>
          </div>

          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>

        {children}
      </section>
    </div>
  );
}
