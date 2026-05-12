"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, FolderOpen, FileBarChart, Settings, Plug, ClipboardCheck } from "lucide-react";
import clsx from "clsx";
import { signOut } from "@/lib/auth";
import { useUser } from "@/components/UserProvider";

const navItems = [
  { label: "Home", href: "/dashboard", icon: Home },
  { label: "Files", href: "/files", icon: FolderOpen },
  { label: "Reports", href: "/reports", icon: FileBarChart },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { email, displayName, role } = useUser();

  return (
    <aside className="fixed left-0 top-0 flex h-screen w-56 flex-col border-r border-blush-200 bg-white">
      {/* ── Logo placeholder ──────────────────────── */}
      <div className="flex flex-col items-center justify-center px-6 py-6 border-b border-blush-100">
        <p className="text-sm font-semibold text-blush-500">Channeled by Chloe</p>
      </div>

      {/* ── Role badge ────────────────────────────── */}
      {role === "bookkeeper" && (
        <div className="mx-3 mt-3 rounded-lg bg-blue-50 px-2 py-1.5 text-center">
          <p className="text-xs font-medium text-blue-700">Bookkeeper View</p>
        </div>
      )}

      {/* ── Navigation ────────────────────────────── */}
      <nav className="flex-1 px-3 py-2">
        {navItems.map(({ label, href, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "mb-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-blush-100 text-blush-700"
                  : "text-gray-500 hover:bg-blush-50 hover:text-gray-700"
              )}
            >
              <Icon size={20} />
              {label}
            </Link>
          );
        })}

        {role === "bookkeeper" && (
          <>
            <Link
              href="/review"
              className={clsx(
                "mb-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname.startsWith("/review")
                  ? "bg-blush-100 text-blush-700"
                  : "text-gray-500 hover:bg-blush-50 hover:text-gray-700"
              )}
            >
              <ClipboardCheck size={20} />
              Review Queue
            </Link>
            <Link
              href="/integrations"
              className={clsx(
                "mb-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname.startsWith("/integrations")
                  ? "bg-blush-100 text-blush-700"
                  : "text-gray-500 hover:bg-blush-50 hover:text-gray-700"
              )}
            >
              <Plug size={20} />
              Integrations
            </Link>
          </>
        )}
      </nav>

      {/* ── Footer ────────────────────────────────── */}
      <div className="border-t border-blush-200 px-4 py-4 space-y-3">
        {displayName && (
          <div>
            <p className="text-sm font-medium text-gray-700 truncate">{displayName}</p>
            <p className="text-xs text-gray-400 truncate">{email}</p>
          </div>
        )}

        <Link
          href="/settings"
          className={clsx(
            "flex items-center gap-2 text-sm transition-colors",
            pathname.startsWith("/settings") ? "text-blush-600" : "text-gray-500 hover:text-gray-700"
          )}
        >
          <Settings size={16} />
          Settings
        </Link>

        <button
          onClick={signOut}
          className="flex w-full items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <span className="text-base leading-none">↩</span>
          Sign out
        </button>
      </div>
    </aside>
  );
}
