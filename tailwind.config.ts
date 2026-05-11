import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:  "#0d0f14",
        s1:  "#13161d",
        s2:  "#1a1e28",
        tx:  "#e8eaf0",
        mu:  "#5e6478",
        mu2: "#8891a8",
        ac:  "#5b8fff",
        gr:  "#3ecf8e",
        am:  "#f5a623",
        re:  "#f25f5c",
      },
      fontFamily: {
        sora: ["var(--font-sora)", "Sora", "sans-serif"],
        mono: ["var(--font-dm-mono)", "DM Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
