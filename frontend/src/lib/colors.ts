// Mirrors tailwind.config.js — useful when a hex value needs to be passed
// through a non-Tailwind path (inline SVG, react-markdown, chart libs).
export const KPMG = {
  blue: "#00338D",
  cobalt: "#1E49E2",
  darkBlue: "#0C233C",
  lightBlue: "#ACEAFF",
  pacificBlue: "#00B8F5",
  purple: "#7213EA",
  pink: "#FD349C",
} as const;

export const STATUS = {
  red: "#ED2124",
  yellow: "#F1C44D",
  green: "#269924",
} as const;
