/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0d1015",
          900: "#141922",
          800: "#1c232e",
          700: "#28313f",
          600: "#374252",
        },
        gold: {
          300: "#f0d3a3",
          400: "#e6bd7f",
          500: "#d9a75c",
        },
      },
      fontFamily: {
        serif: ["Georgia", "'Times New Roman'", "serif"],
        sans: ["system-ui", "-apple-system", "'Segoe UI'", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "dot-bounce": {
          "0%, 80%, 100%": { opacity: "0.25", transform: "translateY(0)" },
          "40%": { opacity: "1", transform: "translateY(-3px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.35s ease both",
        "dot-bounce": "dot-bounce 1.2s infinite ease-in-out",
      },
    },
  },
  plugins: [],
};