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

A sticky global bar (62px) precedes a two-pane shell on Project routes, with navigation (260px) and a flexible workspace. Projects, global Tasks and Test Case Repository use a full-width workspace without that sidebar. Navigation scrolls independently. Desktop workspace padding is 26px 32px 50px. Breadcrumb/path navigation is deferred across all routes by the 2026-10-16 user decision.

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

Project navigation amendment (2026-10-15): the global labels are Projects, Tasks and Test Case Repository. Inside a Project, an inline Project: [dropdown] control precedes Project information, Test Plan, Test Report and Bug List in that order. Selected sections retain the existing tonal selection and current-page state. The default Project view opens Project information; /plans shows the existing Plan list. The /info, /reports and /bugs pages use the existing empty-state treatment pending later design. The Test Plan list omits breadcrumbs, page heading, description and Rename Project / Delete Project controls; Add Test Plan is the sole footer button below the list, including its empty state. Existing Plan detail remains unchanged. Project switching preserves the selected section. Existing Plan and Task deep links remain reachable. This ordinary desktop navigation extension adds no visual tokens or new visual identity.

### Chips

Status badges pair semantic foreground/background colors with compact rounding and semibold type. Pending uses layer and muted; running uses selection and accent; stale uses caution. These indicate state rather than filtering.

### Cards / Containers

Inline forms, empty states and logs use navigation ground and control rounding. Detail panes use separator outlines and an internal divider. Resting containers have no ambient shadow.

### Plan Matrix

The desktop Test Plan list uses columns Plan, total, completed/total, PASS, FAIL, Block, NR and Task count. Task count is an inline expansion control: it reveals a Test Case-by-Task table with a Final column directly below the Plan row. Retain readable status labels, existing semantic styles and table scrolling; missing scope uses a dash. Final and completion follow the current-membership rules in CONTEXT.md, with Block counted as completed. Add Test Plan remains below the list. This increment preserves the existing visual tokens and desktop support scope.

### Plan workspace tree

Plan detail begins with Test Plan: <name>, no description, and Rename / Delete at the right. Below it, the Repository-style tree shares folder/case, Parameters and Actions column alignment and existing controls. Folder collapse and search support navigation; plus opens the Repository copy picker for the selected Plan folder, folder-plus opens a name dialog, and trash requires confirmation. Parameters and source use a resizable side editor with existing Plan locks. Former Plan tabs and top Add / New Task controls are removed; Tasks remain accessible from global Tasks and Matrix columns. Breadcrumbs are deferred throughout the UI. Preserve the incumbent visual tokens.

### Plan source import

Import Test Case in the toolbar replaces folder Add Case icons and the previous Plan .py picker. The dialog selects Repository or a source Project/Plan and presents the target tree left, read-only source tree right. Case and complete-folder drops travel right-to-left only; reverse drops are rejected. Display versions in both lists. Conflict decisions use explicit overwrite/skip or overwrite-update/coexist/skip choices according to identity and version; cancellation makes no changes. Coexisting cases retain their names. Preserve existing tokens, desktop tree styling and clear source/target labels. This supersedes the earlier folder-plus copy-picker guidance.

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


Home / Projects navigation (2026-10-16): BMCAgent brand links to #/dashboard, which owns the existing all-project list without a sidebar. Projects links to the last valid project ID stored as bmc-last-project in browser localStorage and opens its default information page. Visiting a project or switching the dropdown updates that memory. No selection or deleted remembered project falls back to Dashboard. #/projects resolves the Projects entry for bookmarks. Tasks/Repository unchanged; breadcrumbs and deleted-project fallback use Dashboard. Read-only browser checks passed Home, selection, dropdown, reload persistence, missing-project fallback and global routes.

Test Case ordering (2026-10-19): all case-list views use folder-local natural numeric name ordering by default. A manual before/after drag stores a folder-specific custom order; folder Actions > Resorting restores automatic numbering for direct cases. Repository case-only batches and Plan case/source-case insertion support before/after anchors. Dashed allowed-area frames and active inside/upper/lower-half boxes show placement; self/cycle/locked/reverse-source targets are rejected. Source panes remain read-only. Persistent overrides are additive case_list_orders records, independent of definitions and Task evidence. See docs/status/2026-10-19-case-ordering.md.


2026-10-19 Plan import: hide the left Project navigator for the duration of import mode and give its width to the target/source workspace. Restore it whenever import mode ends, including source Close and current Case View.

2026-10-19: Case-list Actions and folder toggles scale within their existing layout boxes; preserve row/column dimensions and Parameter controls. See docs/status/2026-10-19-case-list-buttons.md.

2026-10-19: Top-level Tasks uses Schedule (default, timeline) and My Task (all-task list pending ownership) tabs. See docs/status/2026-10-19-task-workspace-tabs.md.


## Navigation update — 2026-10-20

Use a persistent 260px left sidebar and flexible right workspace on desktop. No top global navigation. Sidebar contains non-linked BMCAgent brand, Dashboard children (Project list, Task timeline), searchable Project selector with information link and Plan/Execution/Report/bug children, then Case Repository. Language and theme controls remain at the bottom. This supersedes earlier contextual sidebar visibility and import hiding rules. See docs/status/2026-10-20-sidebar-layout.md.


## Project Information — 2026-10-21

Four local sections: Basic information, Product specifications, SKU comparison, Source document. Use category selection rather than a single long form for 28 requirement categories. Keep source wording and user-entered values intact. SKU values are independent and blank means unspecified. Project information is reference data, not Task connection or executable test settings. Future import boundary and source mapping: docs/status/2026-10-21-project-information.md.
