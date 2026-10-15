---
name: BMC Agent
description: A file navigator workbench for local BMC test engineering.
colors:
  ground: "#f5f7fa"
  surface: "#ffffff"
  layer: "#edf1f6"
  ink: "#162537"
  muted: "#526477"
  line: "#d7dfe8"
  accent: "#2358b8"
  selected: "#e8effc"
  good: "#176341"
  good-bg: "#eaf5ed"
  bad: "#a32632"
  bad-bg: "#fceef0"
  warn: "#77520a"
  warn-bg: "#fff4d9"
  dark-ground: "#15202d"
  dark-surface: "#1b2939"
  dark-layer: "#233448"
  dark-ink: "#e8eff8"
  dark-muted: "#b1c0d2"
  dark-line: "#3a4d64"
  dark-accent: "#a6c5ff"
  dark-selected: "#294365"
  dark-good: "#9cd8b0"
  dark-good-bg: "#203c31"
  dark-bad: "#ffacb5"
  dark-bad-bg: "#482c37"
  dark-warn: "#f6d081"
  dark-warn-bg: "#403825"
  dark-primary-text: "#142030"
typography:
  headline:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-.02em"
  title:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 650
  body:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "14px"
    lineHeight: 1.6
  label:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: ".9rem"
    fontWeight: 600
  code:
    fontFamily: "Consolas, Courier New, monospace"
    fontSize: ".86rem"
    lineHeight: 1.6
rounded:
  control: "6px"
  compact: "4px"
spacing:
  control-gap: "8px"
  field-gap: "18px"
  section-gap: "24px"
  desktop-inset: "32px"
  mobile-inset: "16px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 10px"
  navigation-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "9px 10px"
  status-passed:
    backgroundColor: "{colors.good-bg}"
    textColor: "{colors.good}"
    rounded: "{rounded.compact}"
    padding: "3px 7px"
  container:
    backgroundColor: "{colors.ground}"
    rounded: "{rounded.control}"
    padding: "20px"
---

# Design System: BMC Agent

## Overview

**Creative North Star: "File navigator workbench"**

Cool navigation ground and a clear working surface support dense engineering tasks. Restrained blue selections and thin separators make ownership and current location visible.

Compact labelled controls, searchable lists and progressive detail define the visual character. The operating system font stack is intentional under the established Operate direction.

**Key Characteristics:**
- Persistent ownership and location
- Compact labelled controls
- Paired light and dark semantic colors
- Flat panes with restrained selected states

## Colors

### Primary

Workbench Blue identifies actions, links and focus. Selection Wash identifies selected navigation, the active case, running status and informational surfaces.

### Neutral

Navigation Ground supports navigation, forms, table headings and logs. Working Surface supports the main pane and controls. Layer supplies hover and pending states. Ink, Muted Ink and Separator distinguish content, supporting text and boundaries.

### Semantic states

Good, bad and warn foreground/background pairs accompany Passed, Failed and stale/caution labels. Dark counterparts retain the same semantic roles. Dark primary buttons use the dedicated dark-primary-text foreground. Frontmatter is normative; CSS properties select the active theme.

**The Selection Coherence Rule.** The highlighted source or evidence row always describes the adjacent detail pane. Scope checkboxes remain a separate selection.

## Typography

Segoe UI with Arial and sans-serif fallbacks is the shared interface face. Consolas with Courier New and monospace fallbacks is reserved for Python source and logs. System interface typography is permitted for this Operate surface.

Headline identifies pages, title identifies sections and label identifies editable fields. Mobile page headlines become 1.55rem. Supporting text uses .9rem and 1.55 line height; status labels use .82rem and table headings .86rem. Prose is capped at 72ch. Numeric tables and counts use tabular figures. There is no separate display treatment.

## Layout

A sticky global bar (62px) precedes a two-pane shell with navigation (260px) and a flexible workspace. Navigation scrolls independently. Desktop workspace padding is 26px 32px 50px. Breadcrumbs precede headings and their actions.

Detail panes split a case browser (minimum 240px, 36%) from an editor. Two-column fields use the field-gap token. At 1100px navigation becomes 230px, workspace padding becomes 24px and fields become one column. At 760px the shell stacks, navigation becomes a toggled 280px overlay and workspace padding is 20px 16px 40px. Headings stack and case lists are capped at 240px. Tables scroll horizontally. Standard controls have minimum heights of 36px desktop and 40px mobile; compact controls use 30px and 36px.

## Elevation & Depth

Resting work surfaces use tonal differences and single-pixel separators. Toasts, dialogs and the mobile navigator share the overlay shadow in the sidecar. Dialog backdrops dim the workspace. Button and link color transitions run for .16s with ease-out only without a reduced-motion preference.

**The Flat Workspace Rule.** Resting work panes use tone and thin separators; shadows identify transient overlays.

## Shapes

Controls, split panes, notices and overlays share the control radius. Status badges and the brand tile use compact rounding. Table and tab boundaries remain straight. Inline SVG line icons complement visible labels or accessible names.

## Components

### Buttons

Compact labelled controls use separator borders and semibold type. Primary uses accent and surface, with the dedicated dark foreground. Secondary hover uses layer; danger actions use bad text. Disabled controls have .55 opacity. Keyboard focus uses a two-pixel accent outline with three-pixel offset.

### Inputs / Fields

Working surface, separator border and control radius frame inputs. Placeholders use muted and the caret uses accent. Visible labels precede fields, with help after them. Source fields use code typography and horizontal scrolling. Inputs share the keyboard focus outline.

### Navigation

Global links, tree rows and case rows use tonal selection. Tree ownership is indented in 14px increments. Tabs identify selection with accent underline. Tree nodes expose current-page state and case rows expose pressed state. Mobile navigation opens above the workspace.

### Chips

Status badges pair semantic foreground/background colors with compact rounding and semibold type. Pending uses layer and muted; running uses selection and accent; stale uses caution. These indicate state rather than filtering.

### Cards / Containers

Inline forms, empty states and logs use navigation ground and control rounding. Detail panes use separator outlines and an internal divider. Resting containers have no ambient shadow.

### Source and evidence split

A searchable case list and adjacent detail pane form the signature component. Its selected row and detail heading identify the same Test Case. Source uses monospace; evidence wraps long lines and scrolls within a bounded region.

## Do's and Don'ts

### Do:

- Do pair foreground and background status colors and retain readable state labels.
- Do preserve visible keyboard focus and reduce motion when requested.
- Do keep selected navigation, selected detail and breadcrumbs coherent.

### Don't:

- Don't use status color as the sole indication of a result.
- Don't add decorative shadows to resting work panes.
- Don't replace labelled engineering controls with unexplained icons.

Task workspace amendment (2026-10-14): global navigation contains Projects and Test Case Repository. Connection settings uses the existing form tokens inside a Task tab, with a disabled fieldset while that Task executes. Other Task environments stay independent.

Desktop-only support amendment (2026-10-14): the user explicitly deferred mobile support. Current design/review targets desktop browser layouts. Historical mobile typography, overlay and breakpoint descriptions above document existing CSS only; they are not current acceptance requirements. Review desktop at 1440x900 and 1920x900. Do not remove existing narrow-width CSS merely to reflect this scope decision.

Task management increment (2026-10-14): global navigation is Projects, Task management and Test Case Repository. The Task information page uses an existing-token table and planned-date Gantt below it. CRUD appears as a labelled form above the list; deletion uses the existing confirmation dialog. Desktop-only; other workbench layout is unchanged.

Repository exclusive function page (2026-10-14): entering Test Case Repository shows its full-width list without the Project navigator. Add imports one .py, View shows metadata/defaults/source read-only, and Remove confirms the selected source version. Removing a Repository row does not change independent Plan copies, source generations, parameters, Task scope or evidence. Returning to the function resets an old preview so the list is the default view.
