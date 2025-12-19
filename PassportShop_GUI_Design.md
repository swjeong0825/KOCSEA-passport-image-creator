# PassportShop — Tkinter GUI Design (Step-by-step)

This document describes a practical, modular plan to build a **Tkinter GUI** around the existing **non-GUI pipeline** in `passport_photo.py`, while preserving output quality.

---

## 1) Build Steps (Step name + what you implement)

### Step 0 — Project skeleton + app state
**Goal:** set up a clean structure so the GUI doesn’t become spaghetti.

**Deliverables**
- Folders:
  - `src/passportshop/ui/`
  - `src/passportshop/app/`
  - `src/passportshop/core/`
  - `src/passportshop/validation/`
- `AppState` object holding:
  - `input_path: str | None`
  - `original_pil: PIL.Image | None`
  - `processed_pil: PIL.Image | None`
  - `processed_temp_path: str | None`
  - `params: ProcessingParams`
  - `validation_report: ValidationReport | None`

---

### Step 1 — Window shell + layout
**Goal:** a runnable UI with placeholders and disabled buttons.

**Deliverables**
- Main window: title + icon (optional)
- Top toolbar: **Upload**, **Process**, **Validate**, **Save/Export**, **Reset**
- Two image previews: Original + Processed
- Right-side panel: settings and validation results
- Status bar at bottom

---

### Step 2 — Upload photo + preview
**Goal:** choose a file and show it in the original preview pane.

**Deliverables**
- `filedialog.askopenfilename(...)` to select image
- Load with Pillow and apply EXIF orientation (same behavior as current script)
- Render preview using `PIL.ImageTk.PhotoImage`
- Enable **Process** button

**UX**
- Show basic image info (filename, resolution)
- If file load fails, show a user-friendly error dialog

---

### Step 3 — Auto crop + background fix (use existing pipeline)
**Goal:** click **Process** to generate a 600×600 passport-style photo.

**Deliverables**
- Call the existing function:
  - `process_passport_photo(input_path, temp_output_path, size, head_ratio, remove_background)`
- Reload processed file into `processed_pil` for preview
- Enable **Validate** and **Save/Export**

**Important**
- Run processing in a background thread to avoid freezing the UI
- Show a progress indicator (indeterminate progress bar)

---

### Step 4 — Validate compliance + report
**Goal:** click **Validate** to produce a pass/fail list with metrics and suggestions.

**Validation report format**
- For each rule: ✅/❌ + short detail message
- Include computed metrics (e.g., head ratio)

**Initial rules (practical)**
- **Size:** image is exactly `size × size` (default 600×600)
- **Head ratio:** (chin→forehead) / image height is in an acceptable range (e.g., 0.50–0.69)
- **Centering:** nose x close to image center (tolerance-based)
- **Background whiteness:** border pixels “near-white” percentage
- **Lighting heuristics:** luminance mean + highlight clipping + shadow variance (best-effort)

**Deliverables**
- `ValidationReport` rendered in UI (Treeview checklist)
- “Copy report” button (copies text to clipboard)

---

### Step 5 — Save / Export
**Goal:** user saves the processed photo and optionally a validation report.

**Deliverables**
- `asksaveasfilename(...)` for output path
- Save as JPEG/PNG; for JPEG use high quality settings
- Optional: export `report.json` next to the image

---

### Step 6 — Polish + guardrails
**Goal:** smooth usability and good failure handling.

**Deliverables**
- Friendly error messages (e.g., “No face detected”)
- “Reset” clears state & UI
- Keyboard shortcuts:
  - Upload: `Ctrl/Cmd+O`
  - Process: `Ctrl/Cmd+R`
  - Save: `Ctrl/Cmd+S`
- Tooltips and inline “Fix suggestions” for failed rules
- Optional “Advanced” section (toggle)

---

## 2) Proposed UI Screen Structure (Tkinter widgets)

### Root window
- `tk.Tk()`
- `ttk.Style()` (use system theme)
- Geometry: resizable; configure grid weights

### Top toolbar (`ttk.Frame`)
- `ttk.Button("Upload")`
- `ttk.Button("Process")` (disabled until upload)
- `ttk.Button("Validate")` (disabled until processed)
- `ttk.Button("Save/Export")` (disabled until processed)
- `ttk.Button("Reset")`
- `ttk.Progressbar(mode="indeterminate")` (hidden until processing)

### Main area (`ttk.PanedWindow`, horizontal)
**Left pane: Original**
- `ttk.LabelFrame("Original")`
- `tk.Canvas` for image preview
- `ttk.Label` for file + resolution metadata

**Right pane: Processed + Controls**
- `ttk.Notebook` with tabs:
  - **Processed** tab:
    - `ttk.LabelFrame("Processed Preview")`
    - `tk.Canvas` for processed preview
    - `ttk.LabelFrame("Settings")`
      - `ttk.Spinbox` size (default 600)
      - `ttk.Entry` or `ttk.Scale` head_ratio (default 0.62)
      - `ttk.Checkbutton` “White background (rembg)”
      - `ttk.Button` “Restore defaults”
  - **Validation** tab:
    - `ttk.Treeview` with columns: Rule | Status | Details
    - `ttk.Button` “Copy report”

### Status bar
- `ttk.Label` (“Ready”, “Processing…”, error text)

---

## 3) ASCII Wireframe

```
+------------------------------------------------------------------+
| PassportShop                                                     |
| [Upload] [Process] [Validate] [Save/Export] [Reset]   (Prog: __ ) |
+------------------------------------------------------------------+
|  Original                               |  Right Pane            |
| +------------------------------+        | +----------------------+ |
| | (Canvas: original preview)   |        | | Tabs: [Processed|Val]| |
| |                              |        | +----------------------+ |
| +------------------------------+        | | Processed Preview     | |
| | File: face1.jpg              |        | | +------------------+ | |
| | Size: 4032x3024              |        | | | Canvas preview   | | |
| +------------------------------+        | | +------------------+ | |
|                                         | | Settings            | |
|                                         | |  Size [600]         | |
|                                         | |  Head ratio [0.62]  | |
|                                         | |  [x] White bg       | |
|                                         | +----------------------+ |
|                                         | Validation tab:        |
|                                         | +----------------------+ |
|                                         | | Rule    | ✅/❌ | ... | |
|                                         | | Size    | ✅   | ... | |
|                                         | | Head    | ✅   | ... | |
|                                         | | Lighting| ❌   | ... | |
|                                         | +----------------------+ |
+------------------------------------------------------------------+
| Status: Ready                                                    |
+------------------------------------------------------------------+
```

---

## 4) Workflow Diagram (sequence)

```
User -> UI -> Controller -> Pipeline -> Validator

1) Upload
   User clicks Upload
   UI opens file dialog
   Controller loads image -> AppState.original_pil
   UI updates original preview; enables Process

2) Process
   User clicks Process
   Controller runs pipeline in background thread:
     process_passport_photo(input_path, temp_output_path, params...)
   Controller loads output -> AppState.processed_pil
   UI updates processed preview; enables Validate + Save

3) Validate
   User clicks Validate
   Controller calls Validator(processed_pil, metadata)
   UI displays report (✅/❌ + details)

4) Save/Export
   User clicks Save
   UI opens save dialog
   Controller saves processed image (and optional report)
   UI shows “Saved”
```

---

## 5) Temp output path vs in-memory processing

### Recommended approach (simple + reliable with current script)
**Use a temp output file while the user is previewing**, then save/export to user-selected path later.

**Why**
- Your current pipeline function writes to an output path.
- Temp file makes it easy to preserve the existing logic.

**Pattern**
- `processed_temp_path = <os temp dir>/passportshop/preview.jpg`
- Overwrite that file every time user clicks Process
- Load it into memory (`processed_pil`) for preview + validation

### Alternative (best long-term)
Refactor pipeline to return `PIL.Image` and metadata, so preview/validate stays in-memory.
Only write to disk when user saves.

---

## 6) UX + accessibility recommendations

### Make failures actionable
- On a failed rule, show a single specific suggestion:
  - “Lighting too dark: move near a window, avoid backlight”
  - “Background not white: use a plain wall”

### Don’t freeze the UI
- Processing/validation can be slow; run in a worker thread
- Use a progress bar + disable buttons while running

### Keyboard + focus
- Shortcuts: Upload (Cmd/Ctrl+O), Process (Cmd/Ctrl+R), Save (Cmd/Ctrl+S)
- Ensure tab order is logical: toolbar -> settings -> report

### Advanced controls (optional)
- “Advanced” toggle for:
  - head ratio adjustment
  - background toggle
  - small manual nudges (recenter face) when auto-crop is slightly off

### “Reset” and “Restore defaults”
- Reset clears current session, previews, and validation report
- Defaults restore: size=600, head_ratio=0.62, remove_bg=True

---

## 7) Suggested implementation checkpoints

- ✅ Checkpoint A: window opens, layout renders
- ✅ Checkpoint B: Upload loads and previews original
- ✅ Checkpoint C: Process outputs temp file and previews processed
- ✅ Checkpoint D: Validate shows a report list
- ✅ Checkpoint E: Save exports final image + report
