# ASGuard Dashboard — DESIGN.md

> Design system for the ASGuard AI Security Firewall dashboard.
> Vibe: dark instrument panel · premium hardware · calm authority.
> Style name: **Lacquer & Kinpaku** (warm-black lacquer, kinpaku gold, verdigris patina).

## 1. Product Overview

ASGuard is a bidirectional AI security firewall. The dashboard is a SOC-style control
room: dense, technical, information-first. It shows live traffic metrics, security
events, transaction lifecycles, policy rules, and test results. Everything displayed is
real data — the design must never decorate or obscure the proof.

**Vibe keywords:** precise, mineral, lacquered, instrument-grade, restrained, warm-dark.

## 2. Color System

### Surfaces (warm lacquer — never pure black)
| Token | Hex | Usage |
|---|---|---|
| background | #12100d | page ground |
| background-deep | #0b0a08 | sidebar, inputs, insets |
| panel | #1a1815 | cards |
| panel-raised | #211e1a | hover fills, table hover |
| panel-active | #2a2723 | pills, tracks |
| border | #2e2a25 | default card/row hairlines |
| border-strong | #3d3831 | controls, emphasis |

### Text
| Token | Hex | Usage |
|---|---|---|
| text-primary | #f0ede6 | headlines, values |
| text-muted | #a39c8f | labels, captions |
| text-faint | #6f6a5f | meta, hints |
| text-disabled | #4d4941 | disabled |

### Brand — kinpaku gold (primary accent)
| Token | Hex | Usage |
|---|---|---|
| gold | #e9b44c | brand mark, active nav, primary CTA, SANITIZE state |
| gold-pale | #f3d489 | hover text on gold contexts |
| gold-deep | #8a6a2f | gold borders at rest |

### Semantic states
| State | Color | Tinted bg |
|---|---|---|
| ALLOW / success / online | #4fb3a9 (verdigris) | rgba(79,179,169,0.10) |
| BLOCK / error | #e5484d (vermilion) | rgba(229,72,77,0.10) |
| SANITIZE / warning | #e9b44c (gold) | rgba(233,180,76,0.10) |
| REVIEW | #a99bd6 (muted lilac) | rgba(169,155,214,0.10) |

Rules: gold is reserved for brand, active state and SANITIZE — never as large fills
behind text. ALLOW is always verdigris. Never pure black or pure white.

## 3. Typography

- **Sans:** Inter / system sans — all UI copy, titles, labels.
- **Mono:** JetBrains Mono / ui-monospace — ALL data: metrics, IDs, timestamps, table
  cells with numbers, stage names, code. Tabular numerals everywhere.

| Role | Spec |
|---|---|
| Page title | 16px / 600 / -0.01em |
| Section label | 11.5px / 600 / UPPERCASE / +0.10em tracking / muted |
| Body | 14px / 400 |
| Data cell | 12–13px mono |
| Stat value | 27px mono / 700 / tabular-nums |
| Badge | 10.5px mono / 600 / +0.06em / uppercase |

## 4. Spacing, Shape, Density

- Base grid: 8px. Page padding 26–28px. Card padding 14–16px.
- Radius: 6px cards · 4px controls/badges. Compact density — no oversized cards.
- Borders: 1px hairlines only. Flat surfaces — no drop shadows except overlays
  (soft 36px neutral). Cards are never nested.
- Density: information-dense without clutter; every metric is real data.

## 5. Components

**StatCard** — panel card; uppercase 10.5px tracked label with 7px colored dot;
27px mono bold value; 2px gold underline bar at bottom edge that scales in on hover.

**Data table** — uppercase 10.5px muted headers, 1px hairline row separators,
mono data cells, row hover = panel-raised. Status column shows Badge.

**Badge** — mono 10.5px, 3px radius, tinted bg + 1px tinted border + small colored
dot prefix. Variants: ALLOW, BLOCK, SANITIZE, REVIEW, ERROR, ONLINE, OFFLINE, PASS, FAIL.

**Button** — flat, 4px radius. Primary: solid gold bg, near-black text (#1a1509),
semibold. Secondary: panel bg + strong border. Hover: border shifts to gold-deep.
Active: scale(0.97). Disabled: 45% opacity.

**Pipeline flow (signature component)** — vertical list of transaction stages.
Each row: 11px status node (teal=OK, vermilion=BLOCKED/FAILED, gold=SANITIZED,
lilac=FLAGGED), mono stage name, right-aligned mono latency, muted detail line.
Nodes connected by a single 1px vertical hairline. BLOCKED nodes pulse gently.

**Charts (SVG, no library)** — stacked time-series bars
(teal=allowed, gold=sanitized, vermilion=blocked, lilac=review);
donut with 13px segments and mono center value; horizontal bars with
gold-deep→gold gradient fill.

## 6. Motion

- Easing: `cubic-bezier(0.22, 1, 0.36, 1)` (smooth ease-out). **Never bounce.**
- Durations: 160ms micro · 320ms standard · 640ms page.
- Page navigation: fade + 10px rise, whole page as one unit.
- Staggered reveals: children cascade at 70ms intervals.
- Numbers: count up from previous value (ease-out cubic, ~900ms).
- Chart bars grow from baseline; donut segments sweep via stroke-dashoffset.
- Live indicators: soft opacity pulse (2.2s). BLOCKED pipeline nodes pulse gently.

## 7. Do / Don't

**Do**
- Keep data dense, calm, and legible; hierarchy through type, not decoration.
- Use gold sparingly: brand, active state, primary action, SANITIZE only.
- Use mono type for anything that is data.
- Keep cards flat, compact, sharply bounded with 1px hairlines.

**Don't**
- No purple gradients, no glassmorphism, no neon cyan, no generic AI glow.
- No bounce/spring easing, no playful illustrations.
- No pure black (#000) or pure white (#fff).
- No wide rounded cards, nested cards, or decorative fake metrics.