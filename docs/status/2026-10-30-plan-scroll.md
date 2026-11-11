# Plan scroll bounds — 2026-10-30

- Remove the obsolete 62px top-bar deduction from Plan shell height. Use the full viewport and prevent the outer workspace from scrolling.
- Keep title, Project subtitle, Plan tabs and toolbar fixed. Only the case list scrolls, with overscroll containment retained.
- Size the list to viewport bottom minus 10px, recalculating on resize/content changes. This supersedes the prior 24px Plan gap; other pages are unchanged.
- Read-only browser wheel checks passed at 1440×900 and 1440×500: list bottom 890/490px, workspace scrollTop 0, heading top unchanged at 18px. At 500px height, the list scrolled 305px while the header remained fixed. No formal data changed.
