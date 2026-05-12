"use client";

import { useEffect, useState } from "react";
import { getTimeAwareGreeting } from "@/lib/utils";

export default function TimeAwareGreeting() {
  const [greeting, setGreeting] = useState("");

  useEffect(() => {
    setGreeting(getTimeAwareGreeting());
  }, []);

  if (!greeting) return null;

  return (
    <div className="text-center">
      <h1 className="text-4xl font-light text-blush-700">{greeting}!</h1>
      <p className="mt-3 text-lg text-blush-600">
        Welcome to the Channeled by Chloe client portal.
      </p>
    </div>
  );
}
