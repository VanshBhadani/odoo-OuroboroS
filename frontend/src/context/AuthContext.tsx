'use client';
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import api from '@/lib/api';
import { User } from '@/types';

interface AuthContextType {
  user: User | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  isLoading: boolean;
}

/**
 * AuthContext exposes the global authentication state.
 * It provides the current logged-in user profile, loading state, 
 * and strictly typed functions to handle login/logout across the app.
 */
const AuthContext = createContext<AuthContextType>({ user: null, login: () => {}, logout: () => {}, isLoading: true });

/**
 * AuthProvider wraps the application and syncs authentication 
 * state with localStorage and the FastAPI backend.
 */
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Re-hydrate authentication state on first load or route change
    const initializeAuth = async () => {
      const token = localStorage.getItem('token');
      
      if (token) {
        try {
          // Verify token validity by fetching the current user profile from the backend
          const res = await api.get('/auth/me');
          setUser(res.data);
        } catch (error) {
          // Token is expired or invalid; clear local storage
          localStorage.removeItem('token');
          // Enforce redirect to login unless already on a public auth page
          if (!pathname.includes('/login') && !pathname.includes('/signup') && !pathname.includes('/forgot-password')) {
            router.push('/login');
          }
        }
      } else {
        // No token found; restrict access to protected dashboard routes
        if (!pathname.includes('/login') && !pathname.includes('/signup') && !pathname.includes('/forgot-password')) {
          router.push('/login');
        }
      }
      
      // Stop the global loading spinner once auth check is complete
      setIsLoading(false);
    };

    initializeAuth();
  }, [pathname, router]);

  const login = (token: string, userData: User) => {
    localStorage.setItem('token', token);
    setUser(userData);
    router.push('/');
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    router.push('/login');
  };

  return <AuthContext.Provider value={{ user, login, logout, isLoading }}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
