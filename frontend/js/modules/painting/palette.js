// Frozen allow-lists for "בוא נצייר". Its own file so the security property is
// greppable: nothing the child picks reaches a style attribute or the server
// unless it is one of these exact strings (precedent: typing's FONT_FAMILIES).

// 12 saturated, distinct hues + black + white. Every value is #rrggbb lowercase
// so it passes the server's ^#[0-9a-f]{6}$ check verbatim.
export const COLOURS = [
  "#e23b3b", // red
  "#f0821e", // orange
  "#f7c531", // yellow
  "#7bc043", // green
  "#2ba84a", // deep green
  "#37b6c4", // teal
  "#3f7fd6", // blue
  "#3b3fb0", // indigo
  "#8e44c9", // purple
  "#e35fa8", // pink
  "#8a5a3c", // brown
  "#000000", // black
  "#ffffff", // white
];

export const DEFAULT_COLOUR = "#e23b3b";

// Normalised to the page's smaller side. Stored as a number so a future 4th
// size never invalidates saved art.
export const BRUSH_SIZES = [
  { key: "s", w: 0.012, label: "דק" },
  { key: "m", w: 0.028, label: "בינוני" },
  { key: "l", w: 0.055, label: "עבה" },
];

export const TOOLS = ["brush", "bucket", "eraser"];

export function isColour(c) {
  return typeof c === "string" && /^#[0-9a-f]{6}$/.test(c) && COLOURS.includes(c);
}
