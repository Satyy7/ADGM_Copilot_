import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: {
          50:  "#FEFDF5",
          100: "#FEFAE8",
          200: "#FDF5D0",
          300: "#FAEDB0",
        },
        amber: {
          50:  "#FFFBEB",
          100: "#FEF3C7",
          200: "#FDE68A",
          300: "#FCD34D",
          400: "#FBBF24",
          500: "#F59E0B",
          600: "#D97706",
          700: "#B45309",
          800: "#92400E",
        },
        warm: {
          50:  "#FAF8F4",
          100: "#F3EFE8",
          200: "#E8E2D8",
          300: "#D9D1C5",
          400: "#BDB3A5",
          500: "#9B9083",
          600: "#7A6E63",
          700: "#5C5249",
          800: "#3D3630",
          900: "#1E1914",
          950: "#0F0C09",
        },
        jade: {
          50:  "#ECFDF5",
          100: "#D1FAE5",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
        },
        rose: {
          50:  "#FFF1F2",
          100: "#FFE4E6",
          500: "#F43F5E",
          600: "#E11D48",
          700: "#BE123C",
        },
        sky: {
          50:  "#F0F9FF",
          100: "#E0F2FE",
          500: "#0EA5E9",
          600: "#0284C7",
          700: "#0369A1",
        },
        violet: {
          50:  "#F5F3FF",
          100: "#EDE9FE",
          500: "#8B5CF6",
          600: "#7C3AED",
          700: "#6D28D9",
        },
        coral: {
          50:  "#FFF7ED",
          100: "#FFEDD5",
          500: "#F97316",
          600: "#EA580C",
        },
        pink: {
          50:  "#FDF2F8",
          100: "#FCE7F3",
          500: "#EC4899",
          600: "#DB2777",
        },
      },
      fontFamily: {
        display: ["'Playfair Display'", "Georgia", "serif"],
        sans:    ["'DM Sans'", "Inter", "system-ui", "sans-serif"],
        mono:    ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        card:  "0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.10), 0 12px 32px rgba(0,0,0,0.06)",
        amber: "0 0 0 3px rgba(245,158,11,0.15)",
        inner: "inset 0 1px 2px rgba(0,0,0,0.05)",
      },
      animation: {
        "fade-up":   "fade-up 0.4s ease-out",
        "fade-in":   "fade-in 0.3s ease-out",
        "slide-in":  "slide-in 0.3s ease-out",
        "bounce-in": "bounce-in 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97)",
        float:       "float 4s ease-in-out infinite",
        shimmer:     "shimmer 1.8s linear infinite",
        "spin-slow": "spin 2.5s linear infinite",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(14px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "slide-in": {
          from: { opacity: "0", transform: "translateX(-10px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        "bounce-in": {
          "0%":   { transform: "scale(0.9)", opacity: "0" },
          "60%":  { transform: "scale(1.03)" },
          "100%": { transform: "scale(1)",   opacity: "1" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%":     { transform: "translateY(-8px)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition:  "400px 0" },
        },
        "pulse-dot": {
          "0%,100%": { opacity: "1",   transform: "scale(1)" },
          "50%":     { opacity: "0.5", transform: "scale(0.8)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
