/**
 * The conversation's identity, so ORCA can follow a thread.
 *
 * Without a stable id every question is a first question: "and what about
 * tomorrow instead?" arrives with nothing to resolve "that" against. The
 * backend keeps a short rolling transcript per id and uses it to interpret
 * follow-ups, so this is what makes refining a query work at all.
 *
 * Kept in localStorage rather than memory so a reload does not silently drop
 * the thread mid-conversation. It is an opaque random id, not an account:
 * nothing about the user is encoded in it.
 */

const STORAGE_KEY = 'orca_session_id';

const newId = (): string => {
  const globalCrypto = globalThis.crypto as Crypto | undefined;
  if (globalCrypto?.randomUUID) return globalCrypto.randomUUID();
  // Older browsers: good enough for a conversation key, which never needs to be
  // unguessable — it is not an auth token.
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
};

/** The current conversation id, creating one on first use. */
export const getSessionId = (): string => {
  try {
    const existing = localStorage.getItem(STORAGE_KEY);
    if (existing) return existing;
    const id = newId();
    localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    // Private browsing or blocked storage: fall back to a per-load id. The
    // thread lasts the page rather than being lost per message.
    return (window as unknown as { __orcaSession?: string }).__orcaSession ??=
      newId();
  }
};

/**
 * Start a fresh conversation, deliberately forgetting the previous thread.
 * Backs a "new conversation" action, and is the honest way to clear context
 * rather than letting stale turns steer an unrelated question.
 */
export const resetSession = (): string => {
  const id = newId();
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    (window as unknown as { __orcaSession?: string }).__orcaSession = id;
  }
  return id;
};
