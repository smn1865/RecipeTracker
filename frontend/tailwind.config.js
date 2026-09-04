/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        culinary: { emerald: "#047857", gold: "#f59e0b", ink: "#18181b", mist: "#f1f5f9" },
      },
    },
  },
};
