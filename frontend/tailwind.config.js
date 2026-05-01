/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // KPMG brand palette (PRD §10).
        kpmg: {
          blue: "#00338D",        // primary
          cobalt: "#1E49E2",      // hover/active
          darkBlue: "#0C233C",
          lightBlue: "#ACEAFF",
          pacificBlue: "#00B8F5",
          purple: "#7213EA",
          pink: "#FD349C",        // response box border (Slides 7/8)
        },
        status: {
          red: "#ED2124",
          yellow: "#F1C44D",
          green: "#269924",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "pulse-slow": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out",
        "pulse-slow": "pulse-slow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
