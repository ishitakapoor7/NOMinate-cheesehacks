import { useEffect, useRef, useState } from 'react';

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const GSI_SRC = 'https://accounts.google.com/gsi/client';

/**
 * Renders the Google Identity Services sign-in button and hands the ID token
 * credential to `onCredential`. Renders nothing when VITE_GOOGLE_CLIENT_ID is
 * unset so local dev works without Google configured.
 */
export default function GoogleButton({ onCredential, text = 'continue_with' }) {
  const slotRef = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!CLIENT_ID) return;

    function renderButton() {
      if (!window.google?.accounts?.id || !slotRef.current) return;
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: (response) => onCredential(response.credential),
      });
      window.google.accounts.id.renderButton(slotRef.current, {
        theme: 'outline',
        size: 'large',
        text,
        width: 420,
        logo_alignment: 'center',
      });
    }

    if (window.google?.accounts?.id) {
      renderButton();
      return;
    }
    let script = document.querySelector(`script[src="${GSI_SRC}"]`);
    if (!script) {
      script = document.createElement('script');
      script.src = GSI_SRC;
      script.async = true;
      document.head.appendChild(script);
    }
    script.addEventListener('load', renderButton);
    script.addEventListener('error', () => setFailed(true));
    return () => script.removeEventListener('load', renderButton);
  }, [onCredential, text]);

  if (!CLIENT_ID || failed) return null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <span className="h-px flex-grow bg-ink/20" />
        <span className="font-mono text-xs tracking-caps text-gray">OR</span>
        <span className="h-px flex-grow bg-ink/20" />
      </div>
      <div ref={slotRef} className="flex justify-center" />
    </div>
  );
}
