import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        blush: {
          50: "#faf5f2",
          100: "#f3ebe5",
          200: "#E8D5CF",
          300: "#d4b8ab",
          400: "#C9A99A",
          500: "#b08d7a",
          600: "#9a7565",
          700: "#7d5e52",
          800: "#5f4840",
          900: "#3f302b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
