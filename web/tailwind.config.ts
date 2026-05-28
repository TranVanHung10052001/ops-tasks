import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // Typography — 2 typefaces only:
      //   sans/display → "Be Vietnam Pro" (body, headings, KPI numbers)
      //   mono         → "JetBrains Mono" (codes, callsigns, tabular numbers)
      // `display` is an alias of `sans` so existing `font-display` classes
      // continue rendering Be Vietnam Pro (not Cormorant Garamond serif).
      fontFamily: {
        sans:    ['"Be Vietnam Pro"', "system-ui", "sans-serif"],
        display: ['"Be Vietnam Pro"', "system-ui", "sans-serif"],
        mono:    ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": "10px",
        xs:    "11px",
        sm:    "12px",
        base:  "14px",   // bumped from 13px — better Vietnamese readability
        md:    "15px",
        lg:    "17px",
        xl:    "20px",
        "2xl": "28px",
        "3xl": "40px",
        "4xl": "56px",
        "5xl": "80px",
      },
      letterSpacing: {
        // Tighter scale (was 0.05 / 0.08 / 0.12 mixed). Use `ops` for labels.
        ops:     "0.06em",
        opswide: "0.12em",
      },
      colors: {
        canvas: "var(--canvas)",
        surface: "var(--surface)",
        "surface-raised": "var(--surface-raised)",
        "surface-deep": "var(--surface-deep)",
        divider: "var(--divider)",
        "divider-strong": "var(--divider-strong)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        "text-tertiary": "var(--text-tertiary)",
        "text-disabled": "var(--text-disabled)",
        signal: {
          p0: "var(--signal-p0)",
          p1: "var(--signal-p1)",
          p2: "var(--signal-p2)",
          p3: "var(--signal-p3)",
          p4: "var(--signal-p4)",
        },
        state: {
          active: "var(--state-active)",
          pending: "var(--state-pending)",
          blocked: "var(--state-blocked)",
          done: "var(--state-done)",
          paused: "var(--state-paused)",
        },
        accent: {
          amber: "var(--accent-amber)",
          "amber-deep": "var(--accent-amber-deep)",
          paper: "var(--accent-paper)",
        },
      },
      borderRadius: {
        none: "0",
        sm: "2px",
        DEFAULT: "3px",
        md: "4px",
      },
      spacing: {
        "1.5": "6px",
        "2.5": "10px",
        "3.5": "14px",
      },
      transitionTimingFunction: {
        snap: "cubic-bezier(0.2, 0, 0, 1)",
        smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
        sharp: "cubic-bezier(0.4, 0, 0.6, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;
