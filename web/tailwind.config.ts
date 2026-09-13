import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12100c",
        paper: "#f3ead7",
        pass: "#1c6b4a",
        warn: "#c4841d",
        danger: "#9b1d2a",
      },
      fontFamily: {
        sans: ["Pretendard", "Apple SD Gothic Neo", "sans-serif"],
        display: ["Song Myung", "serif"],
      },
    },
  },
  plugins: [],
};

export default config;
