---
name: anthropic-html-style
description: Create or restyle standalone HTML pages using the warm, editorial Anthropic-inspired UI design system. Use when building HTML pages that should follow this palette, component style, and responsive behavior.
---

# Style HTML pages with the Anthropic UI

Use this skill when creating or restyling standalone HTML pages that should follow the Anthropic-inspired visual system. The bundled [`references/anthropic-ui.css`](references/anthropic-ui.css) is the reference stylesheet and a reusable starting point.

When working in an existing project, inspect its page and stylesheet first. If the project already has its own `anthropic-ui.css`, use that project file as the source of truth for existing behavior; consult the bundled reference for the intended design language and component patterns. For a new project, copy the bundled stylesheet into the project and link it from each page.

## Link the stylesheet and scope page rules

Link the shared stylesheet from the page head and give the body a unique, descriptive class:

```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Descriptive page title</title>
  <link rel="stylesheet" href="anthropic-ui.css">
</head>
<body class="page-your-topic">
  ...
</body>
```

Keep page-specific overrides scoped under that class. Reuse shared selectors for the page foundation, headings, inputs, buttons, cards, messages, explanation callouts, and raw-data disclosures rather than duplicating their rules.

## Visual language

- Use a warm paper canvas (`--paper`, `#f0eee6`) with ivory or off-white surfaces (`--surface`, `#fbfaf7`; `--ivory`, `#fffdfa`).
- Use `--ink` (`#1f1e1d`) for primary text, `--muted` (`#55524c`) for supporting text, `--stone` (`#8c877c`) for secondary detail, and `--line` (`#e2ddd2`) for subtle borders.
- Use terracotta (`--terra`, `#d97757`) for primary actions and restrained emphasis; use `--terra-dark` (`#c9633f`) for hover states.
- Use a system sans-serif stack for interface text and JetBrains Mono for code, JSON, tool calls, and literal technical output.
- Favor whitespace, fine borders, soft shadows, and rounded surfaces. Keep the overall effect calm, readable, and approachable.
- Reference CSS custom properties instead of repeating color values.

```css
body.page-your-topic .example-panel {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--surface);
  color: var(--ink);
  box-shadow: 0 4px 18px rgba(31, 30, 29, .045);
}
```

## Structure and components

For an explanatory page, use a clear editorial heading and a semantic main region:

```html
<body class="page-your-topic">
  <header class="page-heading">
    <p class="eyebrow">03 · Tool use</p>
    <h1>Clear page title</h1>
    <p class="lede">One short sentence explaining what the visitor will see.</p>
  </header>

  <main class="chat-card" aria-label="Demo description">
    <!-- controls and demo content -->
  </main>
</body>
```

Use `.eyebrow` for a brief category or sequence label, one concise `h1`, and `.lede` for a short summary. The shared `.chat-card` is suitable for an interactive demo surface; it is optional for other page types. Use semantic landmarks and associated labels for controls.

Existing reusable patterns include:

- `.page-heading`, `.eyebrow`, `h1`, `.lede`: centered page introduction.
- `.chat-card` and `.setup`: rounded main surface and divided setup area.
- Inputs and buttons: rounded controls with visible keyboard focus; buttons use the terracotta accent.
- `.message` variants: assistant, tool call, tool result, error, and final answer states.
- `.explain`, `.badge`, `.summary`, `.detail`: explanatory callout with a label and supporting text.
- `details.raw`: collapsible dark panel for raw JSON or technical details.

Reuse patterns when their meaning fits. Give new UI states descriptive classes; avoid broad selectors that could unintentionally affect unrelated content.

## Page-specific styles and responsive behavior

Add only the overrides the page needs, scoped to its body class. Preserve the shared defaults where possible. Animation pages may use a full-viewport stage or SVG while retaining the palette, typography, and restrained surfaces. Provide a reduced-motion alternative when animation is not essential to understanding.

Use a small-screen breakpoint around `640px`, consistent with the reference stylesheet. Let pages scroll vertically instead of clipping content in a fixed-height layout. Reduce outer gutters and card padding on narrow screens; ensure long prompts and output wrap or scroll within their own containers.

Keep visible `:focus-visible` indicators, sufficient text contrast, and comfortable touch targets. Pair color with labels or shapes to communicate status, and use the actual `disabled` attribute for inactive controls.

## Working with an existing stylesheet

Before styling a page, read the relevant HTML and the project's shared stylesheet. Reuse its tokens and components. If the design system needs a shared change, update the shared stylesheet so future pages benefit; do not create a competing palette or copy the entire stylesheet into each page.

Check the result at desktop and mobile widths, including long content and keyboard focus. Fix overflow, clipped controls, and low-contrast text.
