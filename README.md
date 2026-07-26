# Nu-Doom Launcher

A single-window GUI (Python + tkinter, no dependencies) for launching DOOM
source ports with an IWAD and any number of PWAD / `.pk3` mods. Built for
[Nu-Doom](https://github.com/Captain-Beefheart/Nu-Doom), but works with any
classic-style port (Crispy, Chocolate, Woof) as well as GZDoom.

## Running

- **Double-click `Nu-Doom-Launcher.vbs`** — starts the app with `pythonw`, no console window.
- Or run `start.bat` to launch with a console attached (shows tracebacks — handy for debugging).
- Or from a shell: `python nu_doom_launcher.pyw`

Requires Python 3 with tkinter (the MSYS2 `mingw-w64` Python has it built in).
The `.vbs` and `.bat` point at `C:\msys64\mingw64\bin\` and fall back to whatever
`python` / `pythonw` is on your PATH.

## Using it

1. **Add Source Port** — browse to a source-port `.exe` (Nu-Doom, GZDoom, Crispy,
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
   - **Load WAD/PK3 with:** choose `-file` (append the PWADs after the IWAD) or
     `-merge` (merge the PWAD lumps into the IWAD's namespaces, so new sprites,
     flats and textures resolve correctly — matches Nu-Doom / Crispy / Chocolate
     WAD-merge support). `.deh` / `.bex` DeHackEd patches always load via `-deh`
     regardless of this choice.
4. **Extra parameters** (optional) — anything else to pass to the port, e.g.
   `-skill 4 -warp 1 1 -complevel 9`.
5. The **Command** box shows the exact command line that will run. **Launch** runs it.

### How the command is built

```
<port.exe> -iwad <iwad> {-file|-merge} <mod1> <mod2> … -deh <patch.deh> … <extra args>
```

`.deh` / `.bex` files are passed with `-deh`; every other selected mod is passed
with whichever of `-file` / `-merge` you chose. The IWAD folder and mods folder
can be the same folder if you prefer.

## Where settings are stored

`~/.nu_doom_launcher.json` (i.e. `%USERPROFILE%\.nu_doom_launcher.json`) —
remembers your source ports, folders, load method, and extra parameters between runs.
