---
name: vue-saas-redesign
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface with a vertical left sidebar (replacing a top nav bar), consistent spacing, and a polished professional look. Use when the user asks to "redesign the UI", "modernize the layout", "convert the top nav to a sidebar", or make the app "look like a SaaS product".
---

# Vue 3 SaaS Redesign

Converts a top-nav Vue 3 layout into a modern SaaS-style shell: a fixed vertical
sidebar for primary navigation, a slim top bar for contextual actions, and a
consistent spacing/typography system applied across views.

This skill produces a plan and a checklist to execute against — it does not
replace judgment about this specific app's structure. Read the current layout
before changing it.

## Mandatory delegation

**Any creation or significant modification of a `.vue` file MUST be delegated
to the `vue-expert` subagent.** This is a hard project rule (see root
`CLAUDE.md`), not a suggestion. Use this skill to decide *what* the redesign
should contain, then hand each concrete file change to `vue-expert` with a
specific, self-contained brief (file path, what to change, what to preserve).

## Step 1 — Audit the current UI before touching anything

Read, don't assume:
- The root layout component (commonly `App.vue`) — find the top nav markup,
  its CSS, and what it renders alongside the nav (logo, filters, user menu).
- Every view/page component — note per-page headers, spacing, card styles,
  and any inline design values (colors, padding, font sizes) that aren't
  centralized.
- Whether a design-token system already exists (CSS custom properties, a
  shared stylesheet, a design-system doc). If the project has documented
  colors/spacing (check `CLAUDE.md` files), treat those as constraints, not
  suggestions — a redesign should not fight the app's existing brand.
- The router config, to get the full, authoritative list of routes/pages that
  must appear in the new sidebar (don't rely on what's in the current nav —
  it may be stale or incomplete).

Do this audit yourself (Read/Grep) or via the `Explore` agent if the app is
large. Don't hand raw exploration to `vue-expert` — give it conclusions and
a concrete brief instead.

## Step 2 — Define the design system before writing markup

Before any component changes, decide and write down (in your plan, not a
new file unless asked):

**Layout shell**
- Fixed-width sidebar (e.g. 240–280px expanded), full viewport height, on the
  left. Optional collapse to icon-only rail (e.g. 64–72px) for smaller
  viewports or a user toggle.
- Sidebar contains: brand/logo at top, primary nav links (icon + label,
  grouped by section if there are >6 items), and secondary items (settings,
  profile, help) pinned to the bottom.
- Active route gets a clear visual state (background tint + left accent bar
  or bold icon/label) — reuse the existing active-link logic
  (`$route.path === ...` or `router-link-active`), don't reinvent it.
- Top bar (if kept) shrinks to a slim contextual strip: page title, filters,
  search, user menu — no duplicate primary nav.
- Main content area shifts right by the sidebar's width and keeps its own
  scroll; the sidebar stays fixed/sticky.

**Spacing scale**
- Pick one base unit (4px or 8px) and express all paddings/margins/gaps as
  multiples of it (e.g. 4/8/12/16/24/32/48). Define these as CSS custom
  properties (`--space-1` … `--space-8`) on `:root` if the project doesn't
  already have a spacing scale — check first, don't create a second one.
- Apply the scale consistently: card padding, section gaps, sidebar item
  padding, form field spacing should all resolve to scale values, not
  one-off pixel numbers.

**Visual polish**
- Typography: one font stack, a small set of weights/sizes with a clear
  hierarchy (page title > section header > body > caption).
- Color: reuse the project's existing palette (don't introduce new brand
  colors). Add neutral surface levels if missing (app background vs. card
  background vs. sidebar background should be distinguishable, e.g. via
  subtle elevation/border rather than heavy shadows).
- Elevation: prefer 1px borders or a single soft shadow over multiple heavy
  drop-shadows — SaaS UIs read as "polished" partly through restraint.
- Corners/radii and border colors should be consistent across cards, inputs,
  and buttons — pick one radius scale (e.g. 6px/8px/12px) and stick to it.
- No emojis in the UI (see root `CLAUDE.md`).

## Step 3 — Plan the component changes

Typically:
1. A new sidebar component (e.g. `AppSidebar.vue`) encapsulating nav markup,
   active-state logic, and collapse behavior.
2. The root layout component (`App.vue`) restructured to a flex/grid shell:
   sidebar + main content column, with the old `<header class="top-nav">`
   removed or reduced to the slim contextual bar.
3. Shared spacing/color tokens added once (CSS custom properties in the root
   stylesheet or root component), then referenced — not duplicated — by
   other views.
4. Existing view components (`views/*.vue`) updated only where they rely on
   spacing/sizing that assumed a top-nav layout (e.g. `margin-top` offsets),
   or where inconsistent spacing is visible.

Keep the diff proportional: don't rewrite every view's internals if only the
shell and spacing constants need to change.

## Step 4 — Execute via vue-expert

For each `.vue` file to create or modify, call the `vue-expert` subagent with
a brief that includes:
- The exact file path.
- What layout/spacing/token decisions from Step 2 apply to it.
- What existing behavior (routes, active-state logic, i18n keys, event
  handlers, API calls) must be preserved unchanged.
- Any sibling files it needs to stay consistent with (e.g. the new sidebar
  component and the root layout must agree on the sidebar width variable).

Batch independent file changes into parallel `vue-expert` calls; sequence
ones that depend on a shared decision (e.g. finalize the sidebar-width
variable before both the sidebar and the main-content offset are written).

## Step 5 — Verify visually

Use the `run` skill or Playwright MCP tools to start the app and check the
real UI at `http://localhost:3000` (per root `CLAUDE.md`), not just that it
compiles:
- Every route from the router is reachable from the new sidebar.
- Active-state highlighting matches the current route on navigation.
- Layout holds at a narrow and a wide viewport (resize, don't assume).
- No leftover styles from the old top nav (dead CSS, unused classes).
- Spacing is visually consistent across at least two different views, not
  just the one you edited most.

## Common pitfalls

- Introducing a second, competing spacing/color system instead of reusing or
  centralizing the existing one.
- Losing routes that were in the old nav but not re-added to the sidebar (or
  vice versa — sidebar drifting from the router's actual routes).
- Breaking i18n: nav labels are often driven by translation keys
  (`t('nav.xxx')`) — reuse those keys in the sidebar rather than hardcoding
  English strings.
- Forgetting components that render alongside the old nav (language switcher,
  profile menu, notifications) — these need a new home in the sidebar or top
  bar, not to be silently dropped.
- Modifying `.vue` files directly instead of delegating to `vue-expert`.
