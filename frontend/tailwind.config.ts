import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f7f8fa",
          100: "#eceff4",
          200: "#d8dde6",
          300: "#b6bfd0",
          500: "#5e6b85",
          700: "#2a3245",
          900: "#101524",
        },
        accent: {
          500: "#6366f1",
          600: "#4f46e5",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 22, 36, 0.06), 0 4px 12px rgba(15, 22, 36, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
