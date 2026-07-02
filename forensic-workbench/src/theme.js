import { createTheme } from "@mantine/core";

// A calm, human-facing theme for the workbench: a warm indigo accent, generous
// radius, and a readable system font stack. Tuned so the tool reads like a place
// a person works, not a machine console.
export const workbenchTheme = createTheme({
  primaryColor: "indigo",
  primaryShade: { light: 6, dark: 5 },
  defaultRadius: "md",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif',
  fontFamilyMonospace:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
  headings: {
    fontWeight: "650",
    sizes: {
      h1: { fontSize: "1.6rem", lineHeight: "1.25" },
      h2: { fontSize: "1.25rem", lineHeight: "1.3" },
      h3: { fontSize: "1.05rem", lineHeight: "1.35" }
    }
  },
  defaultGradient: { from: "indigo", to: "violet", deg: 135 },
  cursorType: "pointer",
  components: {
    Card: { defaultProps: { withBorder: true, padding: "lg", radius: "md" } },
    Button: { defaultProps: { radius: "md" } },
    Badge: { defaultProps: { radius: "sm", variant: "light" } }
  }
});
