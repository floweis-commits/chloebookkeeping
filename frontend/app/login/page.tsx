"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { createClient } from "@/utils/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left panel */}
      <div className="hidden flex-1 flex-col items-center justify-center bg-blush-200 lg:flex">
        <div className="text-center text-white">
          <h1 className="text-4xl font-light mb-3">Good morning.</h1>
          <p className="text-lg opacity-80">Welcome to your bookkeeping portal.</p>
        </div>
      </div>

      {/* Right panel */}
      <div className="flex flex-1 items-center justify-center bg-white px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex justify-center">
            
          </div>

          <h2 className="mb-6 text-xl font-semibold text-gray-800">Please sign in</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Email Address<span className="text-red-400">*</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email address"
                required
                disabled={loading}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400 disabled:bg-gray-100"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Password<span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  disabled={loading}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 pr-10 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400 disabled:bg-gray-100"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-blush-400 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-blush-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>

            <p className="text-center text-sm text-gray-500">
              <a href="/forgot-password" className="text-blush-500 hover:text-blush-600 font-medium">
                Forgot your password?
              </a>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
