/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        culinary: {
          leaf: "#059669",
          forest: "#065f46",
          gold: "#f59e0b",
          charcoal: "#0f172a",
          mist: "#f1f5f9",
          teal: "#115e59",
        },
      },
    },
  },
};
