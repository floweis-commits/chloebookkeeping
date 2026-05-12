"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getSupabaseUser, getUserRole } from "@/lib/auth";

interface UserContextValue {
  email: string;
  displayName: string;
  role: string | null;
}

const UserContext = createContext<UserContextValue>({
  email: "",
  displayName: "",
  role: null,
});

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    getSupabaseUser().then((u) => {
      if (!u) return;
      setEmail(u.email ?? "");
      setRole(getUserRole(u));
      const meta = u.user_metadata ?? {};
      const name = [meta.first_name, meta.last_name].filter(Boolean).join(" ");
      setDisplayName(name || u.email?.split("@")[0] || "");
    });
  }, []);

  return (
    <UserContext.Provider value={{ email, displayName, role }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
