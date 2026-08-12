# v0 Visual Reference

Source: [v0 chat — SCRIPT+SYNC](https://v0.app/chat/script-sync-eOQYX7FpXl1)

Exported from `c:\Users\victv\Downloads\script-sync\` and kept here for pixel comparison while porting to `app.html` + `v0-theme.css`.

## Components

| File | Role |
|------|------|
| `components/script-sync/top-bar.tsx` | Header, nav, progress |
| `components/script-sync/media-panel.tsx` | Left media column |
| `components/script-sync/workspace.tsx` | Spine, take cards, script, minimap, SVG paths |
| `components/script-sync/sync-node.tsx` | Circular sync nodes |
| `components/script-sync/take-card.tsx` | Take card styling |
| `components/script-sync/script-text.tsx` | Script typography + highlight row |
| `components/script-sync/minimap.tsx` | Minimap ticks + viewport |
| `components/script-sync/bottom-bar.tsx` | Footer |
| `page.tsx` | Page layout composition |
| `globals.css` | Tailwind base tokens |

Implementation lives in `../app.html` (structure + logic) and `../v0-theme.css` (styles).
