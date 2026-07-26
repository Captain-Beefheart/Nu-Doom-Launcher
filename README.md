# DOOM Mod Launcher

A single-window GUI (Python + tkinter, no dependencies) for launching DOOM
source ports with an IWAD and any number of PWAD / `.pk3` mods.

## Running

- **Double-click `DoomModLauncher.vbs`** — starts the app with `pythonw`, no console window.
- Or run `start.bat` to launch with a console attached (shows tracebacks — handy for debugging).
- Or from a shell: `python doom_launcher.pyw`

Requires Python 3 with tkinter (the MSYS2 `mingw-w64` Python has it built in).
The `.vbs` and `.bat` point at `C:\msys64\mingw64\bin\` and fall back to whatever
`python` / `pythonw` is on your PATH.

## Using it

1. **Add Source Port** — browse to a source-port `.exe` (GZDoom, Crispy, Nu-Doom,
   Woof, Chocolate Doom, …). Add as many as you like; pick the active one from the
   **Source** dropdown. **Delete Source Port** removes the selected one from the
   list (it never deletes the file itself).
2. **IWAD folder** → *Set…* — choose the folder holding your IWADs (`doom2.wad`,
   `doom.wad`, …). The **IWAD** list fills with the `.wad` files found there.
   Select exactly one.
3. **Mods folder** → *Set…* — choose the folder holding your PWADs / `.pk3` files.
   The **Mods** list fills with `.wad`, `.pk3`, `.pk7`, `.pke`, `.ipk3`, `.deh`,
   `.bex`, `.zip` files. Select any number.
   - **Load order matters** in Doom — use **▲ Move Up / ▼ Move Down** to arrange the
     selected mods. They load in top-to-bottom list order.
4. **Extra parameters** (optional) — anything else to pass to the port, e.g.
   `-skill 4 -warp 1 1 -complevel 9`.
5. The **Command** box shows the exact command line that will run. **Launch** runs it.

### How the command is built

```
<port.exe> -iwad <iwad> -file <mod1> <mod2> … -deh <patch.deh> … <extra args>
```

`.deh` / `.bex` files are passed with `-deh`; everything else selected goes under
`-file`. The IWAD folder and mods folder can be the same folder if you prefer.

## Where settings are stored

`~/.doom_mod_launcher.json` (i.e. `%USERPROFILE%\.doom_mod_launcher.json`) —
remembers your source ports, folders, and extra parameters between runs.
