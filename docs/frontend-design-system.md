# Frontend Design System

VaaniEval is an operational workspace for voice AI quality review. The UI should feel focused, crisp, and trustworthy: clear enough for repeated QA work, but polished enough that the signin page and authenticated product feel like one system.

## Visual Principles

- Lead with the workspace, not marketing decoration. Product screens should prioritize scanning, comparison, and action.
- Use restrained surfaces: white panels on a soft off-white background, subtle borders, and measured shadows.
- Keep controls predictable. Icon plus label buttons are preferred for commands; dense tool surfaces should avoid oversized hero typography.
- Use visual richness where it carries meaning: signin, page headers, quality states, charts, waveform/audio review, and provider status.

## Tokens

The canonical implementation lives in `frontend/src/index.css` under `:root`.

| Purpose | Token | Value |
| --- | --- | --- |
| App background | `--workspace-bg` | `#f8fafc` |
| Card/surface | `--workspace-card` | `#ffffff` |
| Primary action | `--workspace-primary` | `#0f766e` |
| Primary hover | `--workspace-primary-hover` | `#115e59` |
| Dark command | `--workspace-ink` | `#111827` |
| Accent | `--workspace-accent` | `#f59e0b` |
| Success | `--workspace-success` | `#10b981` |
| Warning | `--workspace-warning` | `#f59e0b` |
| Danger | `--workspace-danger` | `#ef4444` |
| Text | `--workspace-text` | `#0f172a` |
| Secondary text | `--workspace-text-secondary` | `#64748b` |
| Border | `--workspace-border` | `#dbe5e1` |
| Radius | `--workspace-radius` | `8px` |

## Layout

- Authenticated pages use `page` plus page-specific classes; dashboard/conversations use `workspace-page`.
- Page sections should be unframed layouts or single panels. Avoid nested cards unless representing repeated items.
- Panels use `--workspace-radius`, `--workspace-border`, and the shared soft shadow.
- Mobile layouts should keep primary actions in the first viewport when practical.

## Typography

- Body: Inter/Segoe system stack.
- Headings: Sora/Manrope/Segoe stack.
- Product screens use compact headings. Reserve oversized type for signin or true entry experiences only.
- Do not use negative letter spacing. Keep labels and compact metadata at readable 12-14px sizes.

## Color Usage

- Primary teal is for main actions, active navigation, focus rings, and positive brand emphasis.
- Navy/ink is for secondary strong actions and high-contrast shell elements.
- Amber is for accents and warning-adjacent emphasis.
- Avoid returning to the old dominant blue gradient language except for existing third-party/provider-specific affordances where needed.

## Components

- `PageHeader`: white surface, icon tile, concise title/subtitle, optional actions.
- `StatCard`: compact metric card with a tinted icon tile and tone-specific state.
- `panel`: shared white surface with 8px radius.
- Primary buttons: teal background, white text, icon plus label where practical.
- Secondary buttons: white or light neutral surface with border.
- Danger buttons: light red background and red text.
- Forms: 8px inputs, border focus ring in primary teal.

## New Work Checklist

Before shipping new frontend work:

- Reuse existing primitives before adding page-specific styles.
- Use tokens instead of hard-coded brand colors.
- Keep border radius at 8px unless a circular pill/icon control is intentional.
- Verify desktop and mobile viewports.
- Run `npm run build` from `frontend/`.
