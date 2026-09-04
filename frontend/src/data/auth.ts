export interface GoogleUser {
  name: string;
  email: string;
  photoUrl: string | null;
  isAuthenticated: boolean;
}

const AUTH_STORAGE_KEY = 'orca_google_user';
const AUTH_STATUS_KEY = 'orca_auth_status';

/**
 * Retrieves the current authenticated user.
 * Supports localStorage persistence, dynamic user resolution,
 * and tracks logged-out state.
 */
export const getStoredUser = (): GoogleUser | null => {
  if (typeof window === 'undefined') return null;

  const status = localStorage.getItem(AUTH_STATUS_KEY);
  if (status === 'logged_out') {
    return null;
  }

  const stored = localStorage.getItem(AUTH_STORAGE_KEY);
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      if (parsed && typeof parsed.email === 'string') {
        return {
          name: parsed.name || 'Ankan Giri',
          email: parsed.email,
          photoUrl: parsed.photoUrl ?? null,
          isAuthenticated: true,
        };
      }
    } catch (err) {
      console.warn('Could not parse stored auth user', err);
    }
  }

  // Active authenticated Google account session
  return {
    name: 'Ankan Giri',
    email: 'ankangiri05@gmail.com',
    photoUrl: 'https://lh3.googleusercontent.com/a/ACg8ocISYFhJ1T_1dY0Z_74l-bQ=s96-c',
    isAuthenticated: true,
  };
};

/**
 * Updates or stores authenticated user information.
 */
export const saveUser = (user: GoogleUser): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    localStorage.removeItem(AUTH_STATUS_KEY);
  }
};

/**
 * Logs out the user and records logged-out state in storage.
 */
export const logoutUser = (): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(AUTH_STATUS_KEY, 'logged_out');
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
};

/**
 * Logs in the user and clears logged-out state.
 */
export const loginUser = (customUser?: Partial<GoogleUser>): GoogleUser => {
  const newUser: GoogleUser = {
    name: customUser?.name || 'Ankan Giri',
    email: customUser?.email || 'ankangiri05@gmail.com',
    photoUrl: customUser?.photoUrl ?? 'https://lh3.googleusercontent.com/a/ACg8ocISYFhJ1T_1dY0Z_74l-bQ=s96-c',
    isAuthenticated: true,
  };
  saveUser(newUser);
  return newUser;
};
