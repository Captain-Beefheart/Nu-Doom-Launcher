#!/usr/bin/env python3
"""DOOM Mod Launcher — a single-window GUI for launching DOOM source ports with an
IWAD and any number of PWAD/.pk3 mods.

Pick a source port (add/remove exes from a small library), point it at an IWAD
folder and a mods folder, select one IWAD and any number of mods, then Launch.
The constructed command line is shown before you launch so you can verify it.

Pure standard library (tkinter) — no dependencies.
"""

import json
import os
import shlex
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "DOOM Mod Launcher"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".doom_mod_launcher.json")

# File extensions we treat as IWADs / mods (matched case-insensitively).
IWAD_EXTS = (".wad", ".iwad")
MOD_EXTS = (".wad", ".pk3", ".pk7", ".pke", ".ipk3", ".deh", ".bex", ".zip")
# Mods with these extensions are passed via -deh instead of -file.
DEH_EXTS = (".deh", ".bex")


class LauncherConfig:
    """Load/save persisted settings as a small JSON file in the user's home dir."""

    DEFAULTS = {
        "source_ports": [],     # list of full paths to source-port exes
        "selected_port": "",    # currently selected port path
        "iwad_folder": "",
        "mods_folder": "",
        "extra_args": "",
    }

    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                for key in self.DEFAULTS:
                    if key in loaded:
                        self.data[key] = loaded[key]
        except (FileNotFoundError, ValueError, OSError):
            pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
        except OSError as exc:
            # Non-fatal: the app still works, settings just won't persist.
            print(f"Could not save config: {exc}", file=sys.stderr)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value


def scan_folder(folder, exts):
    """Return a sorted list of filenames in *folder* whose extension is in *exts*."""
    if not folder or not os.path.isdir(folder):
        return []
    exts = tuple(e.lower() for e in exts)
    names = []
    try:
        for name in os.listdir(folder):
            if name.lower().endswith(exts) and os.path.isfile(os.path.join(folder, name)):
                names.append(name)
    except OSError:
        return []
    names.sort(key=str.lower)
    return names


class LauncherApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.cfg = LauncherConfig()
        self.grid(row=0, column=0, sticky="nsew")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        # State: port display-name -> full path (display names are the full paths).
        self._build_widgets()
        self._load_state_into_widgets()
        self.update_command_preview()

    # ---------------------------------------------------------------- UI build
    def _build_widgets(self):
        self.columnconfigure(0, weight=1)
        # Two list panels share the vertical stretch.
        self.rowconfigure(2, weight=1)

        # --- Source-port row -------------------------------------------------
        port_frame = ttk.LabelFrame(self, text="Source Port", padding=8)
        port_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        port_frame.columnconfigure(1, weight=1)

        ttk.Label(port_frame, text="Source:").grid(row=0, column=0, padx=(0, 6))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            port_frame, textvariable=self.port_var, state="readonly"
        )
        self.port_combo.grid(row=0, column=1, sticky="ew")
        self.port_combo.bind("<<ComboboxSelected>>", self._on_port_selected)

        ttk.Button(port_frame, text="Add Source Port", command=self.add_source_port).grid(
            row=0, column=2, padx=(6, 0)
        )
        ttk.Button(port_frame, text="Delete Source Port", command=self.delete_source_port).grid(
            row=0, column=3, padx=(6, 0)
        )

        # --- Folders row -----------------------------------------------------
        folder_frame = ttk.Frame(self)
        folder_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        folder_frame.columnconfigure(1, weight=1)
        folder_frame.columnconfigure(3, weight=1)

        ttk.Label(folder_frame, text="IWAD folder:").grid(row=0, column=0, padx=(0, 6))
        self.iwad_folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.iwad_folder_var, state="readonly").grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Button(folder_frame, text="Set…", command=self.set_iwad_folder).grid(
            row=0, column=2, padx=6
        )

        ttk.Label(folder_frame, text="Mods folder:").grid(row=0, column=3, padx=(12, 6), sticky="e")
        # place mods controls on their own sub-columns
        folder_frame.columnconfigure(4, weight=1)
        self.mods_folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.mods_folder_var, state="readonly").grid(
            row=0, column=4, sticky="ew"
        )
        ttk.Button(folder_frame, text="Set…", command=self.set_mods_folder).grid(
            row=0, column=5, padx=(6, 0)
        )

        # --- Lists (IWAD single-select | Mods multi-select) ------------------
        lists_frame = ttk.Frame(self)
        lists_frame.grid(row=2, column=0, sticky="nsew")
        lists_frame.rowconfigure(1, weight=1)
        lists_frame.columnconfigure(0, weight=1)
        lists_frame.columnconfigure(1, weight=1)

        # IWAD panel
        iwad_panel = ttk.LabelFrame(lists_frame, text="IWAD  (select one)", padding=6)
        iwad_panel.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 4))
        iwad_panel.rowconfigure(0, weight=1)
        iwad_panel.columnconfigure(0, weight=1)
        self.iwad_list = tk.Listbox(iwad_panel, selectmode=tk.BROWSE, exportselection=False)
        self.iwad_list.grid(row=0, column=0, sticky="nsew")
        iwad_sb = ttk.Scrollbar(iwad_panel, orient="vertical", command=self.iwad_list.yview)
        iwad_sb.grid(row=0, column=1, sticky="ns")
        self.iwad_list.configure(yscrollcommand=iwad_sb.set)
        self.iwad_list.bind("<<ListboxSelect>>", lambda e: self.update_command_preview())

        # Mods panel
        mods_panel = ttk.LabelFrame(
            lists_frame, text="Mods — PWAD / .pk3  (select any number)", padding=6
        )
        mods_panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(4, 0))
        mods_panel.rowconfigure(0, weight=1)
        mods_panel.columnconfigure(0, weight=1)
        self.mods_list = tk.Listbox(
            mods_panel, selectmode=tk.EXTENDED, exportselection=False
        )
        self.mods_list.grid(row=0, column=0, sticky="nsew")
        mods_sb = ttk.Scrollbar(mods_panel, orient="vertical", command=self.mods_list.yview)
        mods_sb.grid(row=0, column=1, sticky="ns")
        self.mods_list.configure(yscrollcommand=mods_sb.set)
        self.mods_list.bind("<<ListboxSelect>>", lambda e: self.update_command_preview())

        # Load-order controls for the mods list (order matters in Doom).
        order_bar = ttk.Frame(mods_panel)
        order_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(order_bar, text="▲ Move Up", command=lambda: self._move_mod(-1)).pack(
            side="left"
        )
        ttk.Button(order_bar, text="▼ Move Down", command=lambda: self._move_mod(1)).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(order_bar, text="Clear selection", command=self._clear_mod_selection).pack(
            side="right"
        )

        # --- Extra args + command preview + Launch ---------------------------
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        bottom.columnconfigure(1, weight=1)

        ttk.Label(bottom, text="Extra parameters:").grid(row=0, column=0, sticky="w")
        self.extra_var = tk.StringVar()
        extra_entry = ttk.Entry(bottom, textvariable=self.extra_var)
        extra_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 6))
        extra_entry.bind("<KeyRelease>", lambda e: self.update_command_preview())

        ttk.Label(bottom, text="Command:").grid(row=1, column=0, sticky="nw")
        self.cmd_text = tk.Text(bottom, height=3, wrap="word", state="disabled")
        self.cmd_text.grid(row=1, column=1, sticky="ew")
        ttk.Button(bottom, text="Copy", command=self._copy_command).grid(
            row=1, column=2, sticky="n", padx=(6, 0)
        )

        launch_btn = ttk.Button(bottom, text="  Launch  ", command=self.launch)
        launch_btn.grid(row=2, column=0, columnspan=3, pady=(8, 0))

    # ------------------------------------------------------ state <-> widgets
    def _load_state_into_widgets(self):
        self._refresh_port_combo()
        self.iwad_folder_var.set(self.cfg["iwad_folder"])
        self.mods_folder_var.set(self.cfg["mods_folder"])
        self.extra_var.set(self.cfg["extra_args"])
        self.refresh_iwad_list()
        self.refresh_mods_list()

    def _refresh_port_combo(self):
        ports = self.cfg["source_ports"]
        self.port_combo["values"] = ports
        selected = self.cfg["selected_port"]
        if selected in ports:
            self.port_var.set(selected)
        elif ports:
            self.port_var.set(ports[0])
            self.cfg["selected_port"] = ports[0]
        else:
            self.port_var.set("")

    # --------------------------------------------------------- source ports
    def add_source_port(self):
        path = filedialog.askopenfilename(
            title="Select source-port executable",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")],
        )
        if not path:
            return
        path = os.path.normpath(path)
        ports = self.cfg["source_ports"]
        if path not in ports:
            ports.append(path)
        self.cfg["selected_port"] = path
        self.cfg.save()
        self._refresh_port_combo()
        self.update_command_preview()

    def delete_source_port(self):
        current = self.port_var.get()
        if not current:
            return
        if not messagebox.askyesno(
            "Delete Source Port",
            f"Remove this source port from the list?\n\n{current}\n\n"
            "(This only removes it from the launcher — the file is not deleted.)",
        ):
            return
        ports = self.cfg["source_ports"]
        if current in ports:
            ports.remove(current)
        self.cfg["selected_port"] = ports[0] if ports else ""
        self.cfg.save()
        self._refresh_port_combo()
        self.update_command_preview()

    def _on_port_selected(self, _event=None):
        self.cfg["selected_port"] = self.port_var.get()
        self.cfg.save()
        self.update_command_preview()

    # -------------------------------------------------------------- folders
    def set_iwad_folder(self):
        folder = filedialog.askdirectory(
            title="Select IWAD folder", initialdir=self.cfg["iwad_folder"] or None
        )
        if not folder:
            return
        self.cfg["iwad_folder"] = os.path.normpath(folder)
        self.cfg.save()
        self.iwad_folder_var.set(self.cfg["iwad_folder"])
        self.refresh_iwad_list()
        self.update_command_preview()

    def set_mods_folder(self):
        folder = filedialog.askdirectory(
            title="Select mods folder (PWADs / .pk3)",
            initialdir=self.cfg["mods_folder"] or None,
        )
        if not folder:
            return
        self.cfg["mods_folder"] = os.path.normpath(folder)
        self.cfg.save()
        self.mods_folder_var.set(self.cfg["mods_folder"])
        self.refresh_mods_list()
        self.update_command_preview()

    # ---------------------------------------------------------------- lists
    def refresh_iwad_list(self):
        self.iwad_list.delete(0, tk.END)
        for name in scan_folder(self.cfg["iwad_folder"], IWAD_EXTS):
            self.iwad_list.insert(tk.END, name)

    def refresh_mods_list(self):
        self.mods_list.delete(0, tk.END)
        for name in scan_folder(self.cfg["mods_folder"], MOD_EXTS):
            self.mods_list.insert(tk.END, name)

    def _move_mod(self, direction):
        """Move the currently selected mod(s) up or down to control load order."""
        sel = list(self.mods_list.curselection())
        if not sel:
            return
        items = list(self.mods_list.get(0, tk.END))
        # Process in an order that avoids clobbering when moving multiple items.
        indices = sel if direction < 0 else list(reversed(sel))
        new_selection = []
        for idx in indices:
            target = idx + direction
            if target < 0 or target >= len(items):
                new_selection.append(idx)
                continue
            items[idx], items[target] = items[target], items[idx]
            new_selection.append(target)
        self.mods_list.delete(0, tk.END)
        for name in items:
            self.mods_list.insert(tk.END, name)
        for idx in new_selection:
            self.mods_list.selection_set(idx)
        self.mods_list.activate(new_selection[0] if new_selection else 0)
        self.update_command_preview()

    def _clear_mod_selection(self):
        self.mods_list.selection_clear(0, tk.END)
        self.update_command_preview()

    # ----------------------------------------------------- command building
    def selected_iwad_path(self):
        sel = self.iwad_list.curselection()
        if not sel:
            return None
        name = self.iwad_list.get(sel[0])
        return os.path.join(self.cfg["iwad_folder"], name)

    def selected_mod_paths(self):
        folder = self.cfg["mods_folder"]
        return [
            os.path.join(folder, self.mods_list.get(i))
            for i in self.mods_list.curselection()
        ]

    def build_command(self):
        """Return the argument list to launch, or None if no source port is set."""
        port = self.port_var.get()
        if not port:
            return None
        args = [port]

        iwad = self.selected_iwad_path()
        if iwad:
            args += ["-iwad", iwad]

        mods = self.selected_mod_paths()
        files = [m for m in mods if not m.lower().endswith(DEH_EXTS)]
        dehs = [m for m in mods if m.lower().endswith(DEH_EXTS)]
        if files:
            args += ["-file"] + files
        if dehs:
            args += ["-deh"] + dehs

        extra = self.extra_var.get().strip()
        if extra:
            try:
                args += shlex.split(extra, posix=False)
            except ValueError:
                args += extra.split()
        return args

    def update_command_preview(self):
        args = self.build_command()
        self.cmd_text.configure(state="normal")
        self.cmd_text.delete("1.0", tk.END)
        if args:
            self.cmd_text.insert("1.0", subprocess.list2cmdline(args))
        else:
            self.cmd_text.insert("1.0", "(add and select a source port to build a command)")
        self.cmd_text.configure(state="disabled")

    def _copy_command(self):
        args = self.build_command()
        if not args:
            return
        self.clipboard_clear()
        self.clipboard_append(subprocess.list2cmdline(args))

    # --------------------------------------------------------------- launch
    def launch(self):
        args = self.build_command()
        if not args:
            messagebox.showwarning(
                APP_TITLE, "Add and select a source port first."
            )
            return
        port = args[0]
        if not os.path.isfile(port):
            messagebox.showerror(
                APP_TITLE, f"Source-port executable not found:\n{port}"
            )
            return

        # Persist the current extra args before launching.
        self.cfg["extra_args"] = self.extra_var.get()
        self.cfg.save()

        try:
            subprocess.Popen(args, cwd=os.path.dirname(port) or None)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Failed to launch:\n{exc}")


def main():
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("760x520")
    root.minsize(620, 420)
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
