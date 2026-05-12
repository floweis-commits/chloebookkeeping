import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/Toast";
import { UserProvider } from "@/components/UserProvider";

export const metadata: Metadata = {
  title: "Chloe Bookkeeping",
  description: "Client portal for Channeled by Chloe LLC",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-blush-50 text-gray-800 antialiased">
        <ToastProvider>
          <UserProvider>
            {children}
          </UserProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
