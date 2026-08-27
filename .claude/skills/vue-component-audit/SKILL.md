---
name: vue-component-audit
description: Analyze Vue 3 component structure under client/src and produce a prioritized report of performance and code-reuse optimizations. Use this skill when asked to audit, review, or optimize Vue components, find duplicated frontend logic, or identify candidates for composables/subcomponents.
---

# Vue Component Structure Audit

Produces a report of concrete, file-and-line-referenced optimization opportunities across
`client/src/views/*.vue`, `client/src/components/*.vue`, and `client/src/composables/*.js`.
This skill is **read-only analysis** — it does not modify `.vue` files itself. If the user
wants findings applied, delegate the actual edits to the `vue-expert` subagent (mandatory per
the root `CLAUDE.md` rule for any `.vue` file creation/modification).

## Scope

Read, in this order:
1. `client/src/composables/*.js` — existing shared logic (`useFilters`, `useAuth`, `useI18n`, etc.)
2. `client/src/components/*.vue` — reusable components
3. `client/src/views/*.vue` — page-level components (largest, most likely to need splitting)
4. `client/src/api.js` — to check whether views call it consistently vs. duplicating request logic

Use `Grep`/`Glob` for cross-file pattern searches (e.g. counting `v-for` occurrences, finding
inline `toLocaleString(` calls) rather than opening every file blind — views like `Dashboard.vue`
and `Spending.vue` are large (25-38k) and worth targeting directly.

## What to look for

### Performance

- **Methods that should be `computed`** — a function under `methods`/returned from `setup()`
  that only derives a value from reactive state (filtering, mapping, summing) and is called
  directly in the template. Recomputes on every render instead of caching until deps change.
- **Heavy work inside `watch` without debounce** — especially watchers on filter/search refs
  that trigger an API call. Check for `watchDebounced` from `@vueuse/core`; flag raw `watch`
  that fires on every keystroke.
- **`v-if` on frequently toggled elements** that would be cheaper as `v-show` (e.g. modal
  content, tab panels toggled often in the same session).
- **Uncached chart/SVG data transforms** — chart data built inline in the template or in a
  plain method instead of a `computed`, recalculating on unrelated re-renders.
- **Missing `key` uniqueness in `v-for`** — using `index` instead of a stable id (`sku`,
  `order_number`, `month`) per the "Common Issues" section of the root `CLAUDE.md`.
- **Unvalidated date parsing** — `new Date(x).getMonth()` etc. without an `isNaN` check before use.
- **Large monolithic `computed`/`setup()` bodies** that recompute more than the template
  actually needs — look for a computed used only for one small sub-value that could be split
  so unrelated template regions don't all re-evaluate together.

### Code reuse

- **Duplicated data-loading boilerplate** — the same `loading`/`error`/try-catch-finally
  shape repeated across multiple views instead of a shared composable.
- **Duplicated formatting logic** — currency/percentage/date formatting reimplemented inline
  in more than one file instead of a shared `utils/` helper or composable.
- **Duplicated filter-application logic** — logic that reads `useFilters()` state and applies
  it to a local dataset, repeated across views instead of being expressed once.
- **Repeated modal scaffolding** — multiple `*Modal.vue` components (e.g. `BacklogDetailModal`,
  `CostDetailModal`, `InventoryDetailModal`, `ProductDetailModal`) with near-identical
  open/close/backdrop/teleport structure that could share a base modal wrapper component.
- **Views over ~150 lines of script or ~100 lines of template** that mix multiple concerns
  (e.g. a view that both fetches data and renders a complex chart) — candidate to extract a
  subcomponent or a composable, per the "When to extract" guidance in `client/CLAUDE.md`.
- **Options API / Composition API mixing** in the same component.
- **Direct `axios`/`fetch` calls in a view** instead of going through `client/src/api.js`.

## Process

1. Glob the scope above and note file sizes (`wc -l`) to prioritize the largest views first.
2. For each file, extract: template line count, script line count, list of `computed`
   properties, list of `watch`/`watchDebounced` calls, `v-for` usages and their `:key`
   expressions, and any inline formatting/date logic.
3. Grep across all files for repeated patterns (formatting functions, loading/error state
   shapes, modal structure) to find code-reuse candidates — a pattern only counts as a finding
   if it appears in 2+ files.
4. Compile findings into two sections, **Performance** and **Code Reuse**, each entry as:
   - `file:line` reference
   - one-sentence description of the issue
   - why it matters (what it costs — extra renders, duplicated maintenance burden, etc.)
   - concrete suggested fix (name the composable/subcomponent to extract, or the computed to add)
5. Order each section by impact: issues affecting the largest/most-visited views
   (`Dashboard.vue`, `Spending.vue`) or repeated across the most files first.
6. Present the report to the user. Do not edit any `.vue` file as part of this skill. If the
   user asks to apply the fixes, hand the specific findings off to the `vue-expert` subagent.

## Output format

```
## Performance
1. [Dashboard.vue:142] <issue> — <why> — Fix: <suggestion>

## Code Reuse
1. [BacklogDetailModal.vue, CostDetailModal.vue, InventoryDetailModal.vue] <duplicated pattern>
   — Fix: extract `components/BaseModal.vue` and have each modal wrap it
```

Keep findings concrete and grounded in what was actually read — do not speculate about files
that weren't opened.
