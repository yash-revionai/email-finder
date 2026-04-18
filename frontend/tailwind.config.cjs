const colors = require("tailwindcss/colors");
const formsPlugin = require("@tailwindcss/forms");

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    transparent: "transparent",
    current: "currentColor",
    extend: {
      colors: {
        tremor: {
          brand: {
            faint: colors.amber[50],
            muted: colors.orange[200],
            subtle: colors.orange[400],
            DEFAULT: colors.orange[500],
            emphasis: colors.red[700],
            inverted: colors.white,
          },
          background: {
            muted: colors.stone[50],
            subtle: colors.stone[100],
            DEFAULT: colors.white,
            emphasis: colors.stone[700],
          },
          border: {
            DEFAULT: colors.stone[200],
          },
          ring: {
            DEFAULT: colors.stone[200],
          },
          content: {
            subtle: colors.stone[400],
            DEFAULT: colors.stone[500],
            emphasis: colors.stone[700],
            strong: colors.stone[900],
            inverted: colors.white,
          },
        },
        "dark-tremor": {
          brand: {
            faint: colors.orange[950],
            muted: colors.orange[900],
            subtle: colors.orange[700],
            DEFAULT: colors.orange[500],
            emphasis: colors.amber[300],
            inverted: colors.stone[950],
          },
          background: {
            muted: colors.stone[950],
            subtle: colors.stone[900],
            DEFAULT: colors.stone[900],
            emphasis: colors.stone[300],
          },
          border: {
            DEFAULT: colors.stone[800],
          },
          ring: {
            DEFAULT: colors.stone[800],
          },
          content: {
            subtle: colors.stone[500],
            DEFAULT: colors.stone[400],
            emphasis: colors.stone[200],
            strong: colors.stone[50],
            inverted: colors.stone[950],
          },
        },
        ember: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
          950: "#431407"
        },
      },
      boxShadow: {
        "tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        "tremor-card": "0 20px 40px -24px rgb(41 24 12 / 0.35)",
        "tremor-dropdown": "0 25px 50px -24px rgb(41 24 12 / 0.3)",
        "dark-tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.25)",
        "dark-tremor-card": "0 20px 40px -24px rgb(0 0 0 / 0.8)",
        "dark-tremor-dropdown": "0 25px 50px -24px rgb(0 0 0 / 0.85)"
      },
      borderRadius: {
        "tremor-small": "0.375rem",
        "tremor-default": "0.75rem",
        "tremor-full": "9999px",
      },
      fontFamily: {
        sans: ["Avenir Next", "Trebuchet MS", "Segoe UI", "sans-serif"],
        display: ["Iowan Old Style", "Palatino Linotype", "Book Antiqua", "serif"],
      },
      fontSize: {
        "tremor-label": ["0.75rem", { lineHeight: "1rem" }],
        "tremor-default": ["0.875rem", { lineHeight: "1.35rem" }],
        "tremor-title": ["1.125rem", { lineHeight: "1.75rem" }],
        "tremor-metric": ["1.875rem", { lineHeight: "2.25rem" }],
      },
      keyframes: {
        "fade-rise": {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-rise": "fade-rise 0.7s ease-out both",
        shimmer: "shimmer 2s linear infinite",
      },
    },
  },
  safelist: [
    {
      pattern:
        /^(bg|text|border|ring|fill|stroke)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(50|100|200|300|400|500|600|700|800|900|950)$/,
      variants: ["hover", "data-[selected]"],
    },
  ],
  plugins: [formsPlugin],
};
