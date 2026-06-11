import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#04080f",
          900: "#070d1a",
          800: "#0d1526",
          700: "#122038",
          600: "#1a2d50",
          500: "#243d6a",
        },
        gold: {
          300: "#fcd97a",
          400: "#f0c050",
          500: "#d4a030",
          600: "#b88020",
          700: "#9a6010",
        },
        jade: {
          400: "#34d4a0",
          500: "#20b88a",
        },
        crimson: {
          400: "#ff5c6e",
          500: "#e83a50",
        },
        amber: {
          400: "#ffb040",
          500: "#f09020",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "JetBrains Mono", "monospace"],
      },
      backgroundImage: {
        "aurora": "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(212,160,48,0.12), transparent), radial-gradient(ellipse 60% 40% at 80% 80%, rgba(26,45,80,0.6), transparent)",
        "card-gradient": "linear-gradient(135deg, rgba(13,21,38,0.9) 0%, rgba(18,32,56,0.8) 100%)",
        "gold-glow": "linear-gradient(135deg, rgba(212,160,48,0.15), rgba(212,160,48,0.05))",
        "sidebar-gradient": "linear-gradient(180deg, #070d1a 0%, #0a1220 60%, #070d1a 100%)",
      },
      boxShadow: {
        "gold": "0 0 30px rgba(212,160,48,0.15), 0 0 60px rgba(212,160,48,0.05)",
        "gold-sm": "0 0 12px rgba(212,160,48,0.2)",
        "card": "0 4px 24px rgba(0,0,0,0.4), 0 1px 4px rgba(0,0,0,0.2)",
        "glow-jade": "0 0 20px rgba(52,212,160,0.2)",
        "glow-red": "0 0 20px rgba(255,92,110,0.2)",
        "inner-gold": "inset 0 1px 0 rgba(212,160,48,0.1)",
      },
      animation: {
        "aurora": "aurora 8s ease-in-out infinite alternate",
        "pulse-gold": "pulse-gold 2s ease-in-out infinite",
        "slide-up": "slide-up 0.4s ease-out",
        "slide-in-right": "slide-in-right 0.3s ease-out",
        "fade-in": "fade-in 0.3s ease-out",
        "spin-slow": "spin 3s linear infinite",
        "float": "float 3s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
      keyframes: {
        aurora: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "100% 50%" },
        },
        "pulse-gold": {
          "0%, 100%": { boxShadow: "0 0 10px rgba(212,160,48,0.2)" },
          "50%": { boxShadow: "0 0 30px rgba(212,160,48,0.5)" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-right": {
          from: { opacity: "0", transform: "translateX(16px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
export default config;
