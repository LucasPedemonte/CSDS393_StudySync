/**
 * Auth-guard wrapper for routes that require a signed-in Firebase user.
 * Renders nothing while the auth state is resolving, redirects to "/"
 * if the user is signed out, and otherwise renders its children.
 *
 * @module ProtectedRoute
 */
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "./firebase";

/**
 * @param {{ children: React.ReactNode }} props
 * @returns {React.ReactElement|null} The protected children, a redirect, or null while loading.
 */
export default function ProtectedRoute({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
    });
    return () => unsub();
  }, []);

  if (loading) return null; 
  if (!user) return <Navigate to="/" replace />;

  return children;
}