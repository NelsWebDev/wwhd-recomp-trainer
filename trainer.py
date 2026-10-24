#!/usr/bin/env python3
"""Wind Waker HD trainer for Cemu on macOS."""

from __future__ import annotations

import ctypes
import ctypes.util
import math
import os
import re
import struct
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


OFFSETS = {
    "player_x": 0x1046CD48,
    "player_y": 0x1046CD50,
    "player_z": 0x1046CD4C,
    "max_health": 0x145B7B80,
    "health": 0x145B7B82,
    "rupees_ui": 0x10474C5E,
    "rupees": 0x145B7B84,
    "rupee_capacity": 0x145B7B92,
    "max_stamina": 0x145B7B93,
    "stamina": 0x145B7B94,
    "breath": 0x10474BFE,
    "sword": 0x145B7C34,
    "shield": 0x145B7C35,
    "bracelet": 0x145B7C36,
    "pirate_charm": 0x145B7C37,
    "hero_amulet": 0x145B7C38,
    "triforce": 0x145B7C3E,
    "pearls": 0x145B7C3F,
    "map_charts": 0x145B7C54,
    "map_grid": 0x145B7C84,
    "triforce_charts": 0x145B7CC5,
    "beedle_points": 0x145B822A,
    "arrows": 0x145B7BE9,
    "bombs": 0x145B7BEA,
    "max_arrows": 0x145B7BEF,
    "max_bombs": 0x145B7BF0,
    "songs": 0x145B7C3D,
    "bow": 0x145B7BDD,
}

GEAR_FLAGS = {
    "Telescope": 0x145B7BD1,
    "Sail": 0x145B7BD2,
    "Wind Waker": 0x145B7BD3,
    "Grappling Hook": 0x145B7BD4,
    "Spoils Bag": 0x145B7BD5,
    "Boomerang": 0x145B7BD6,
    "Deku Leaf": 0x145B7BD7,
    "Tingle Bottle": 0x145B7BD8,
    "Picto Box": 0x145B7BD9,
    "Iron Boots": 0x145B7BDA,
    "Magic Armor": 0x145B7BDB,
    "Bait Bag": 0x145B7BDC,
    "Bow": 0x145B7BDD,
    "Bombs": 0x145B7BDE,
    "Delivery Bag": 0x145B7BE3,
    "Hookshot": 0x145B7BE4,
    "Skull Hammer": 0x145B7BE5,
}

SONG_NAMES = (
    "Wind's Requiem",
    "Song of Passing",
    "Command Melody",
    "Ballad of Gales",
    "Earth God's Lyric",
    "Wind God's Aria",
)

INVENTORY_ITEMS = {
    "Empty slot": 0,
    "Joy Pendant": 31,
    "Telescope": 32,
    "Tingle Bottle": 33,
    "Wind Waker": 34,
    "Picto Box": 35,
    "Spoils Bag": 36,
    "Grappling Hook": 37,
    "Deluxe Picto Box": 38,
    "Hero's Bow": 39,
    "Iron Boots": 41,
    "Magic Armor": 42,
    "Bait Bag": 44,
    "Boomerang": 45,
    "Hookshot": 47,
    "Delivery Bag": 48,
    "Bombs": 49,
    "Skull Hammer": 51,
    "Deku Leaf": 52,
    "Hero's Bow (Fire and Ice)": 53,
    "Hero's Bow (all arrows)": 54,
    "Skull Necklace": 69,
    "Boko Baba Seed": 70,
    "Golden Feather": 71,
    "Knight's Crest": 72,
    "Red Chu Jelly": 73,
    "Green Chu Jelly": 74,
    "Blue Chu Jelly": 75,
    "Empty Bottle": 80,
    "Red Potion": 81,
    "Green Potion": 82,
    "Blue Potion": 83,
    "Elixir Soup (half)": 84,
    "Elixir Soup": 85,
    "Water": 86,
    "Fairy": 87,
    "Forest Firefly": 88,
    "Forest Water": 89,
    "All-Purpose Bait": 130,
    "Hyoi Pear": 131,
    "Town Flower": 140,
    "Sea Flower": 141,
    "Exotic Flower": 142,
    "Hero's Flag": 143,
    "Big Catch Flag": 144,
    "Big Sale Flag": 145,
    "Pinwheel": 146,
    "Sickle Moon Flag": 147,
    "Skull Tower Idol": 148,
    "Fountain Idol": 149,
    "Postman Statue": 150,
    "Shop Guru Statue": 151,
    "Father's Letter": 152,
    "Note to Mom": 153,
    "Maggie's Letter": 154,
    "Moblin's Letter": 155,
    "Cabana Deed": 156,
    "Complimentary ID": 157,
    "Fill-up Coupon": 158,
}


def pack_value(value: int | float, kind: str) -> bytes:
    """Encode a value using the game's big-endian representation."""
    formats = {"u8": ">B", "u16": ">H", "f32": ">f"}
    try:
        return struct.pack(formats[kind], value)
    except (KeyError, struct.error) as exc:
        raise ValueError(f"Invalid {kind} value: {value}") from exc


def unpack_value(data: bytes, kind: str) -> int | float:
    formats = {"u8": ">B", "u16": ">H", "f32": ">f"}
    try:
        return struct.unpack(formats[kind], data)[0]
    except (KeyError, struct.error) as exc:
        raise ValueError(f"Invalid {kind} data") from exc


def find_cemu_pid() -> int | None:
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,comm="],
        check=True,
        capture_output=True,
        text=True,
    )
    matches = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) == 2 and Path(fields[1]).name.lower() == "cemu":
            matches.append(int(fields[0]))
    return matches[0] if len(matches) == 1 else None


def find_cemu_base() -> int | None:
    """Find the latest Cemu base address in its log, if one is available."""
    candidates = [
        Path.home() / "Library/Application Support/Cemu/log.txt",
        Path.home() / "Library/Application Support/Cemu/cemu/log.txt",
    ]
    for log_path in candidates:
        try:
            text = log_path.read_text(errors="replace")
        except OSError:
            continue
        addresses = re.findall(r"\bbase:\s*(0x[0-9a-f]+)", text, re.IGNORECASE)
        if addresses:
            return int(addresses[-1], 16)
    return None


class MachProcessMemory:
    """Minimal read/write access to a same-user Cemu process via Mach APIs."""

    def __init__(self) -> None:
        self._connected = False
        if sys.platform != "darwin":
            raise OSError("This memory backend is available only on macOS.")
        library = ctypes.util.find_library("System")
        if not library:
            raise OSError("Could not load the macOS System library.")
        self._lib = ctypes.CDLL(library, use_errno=True)
        self._task = ctypes.c_uint32()
        self._mach_port_deallocate = self._lib.mach_port_deallocate
        self._mach_port_deallocate.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        self._mach_port_deallocate.restype = ctypes.c_int
        self._task_for_pid = self._lib.task_for_pid
        self._task_for_pid.argtypes = [
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self._task_for_pid.restype = ctypes.c_int
        self._mach_task_self = ctypes.c_uint32.in_dll(self._lib, "mach_task_self_")
        self._read = self._lib.mach_vm_read_overwrite
        self._read.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_uint64),
        ]
        self._read.restype = ctypes.c_int
        self._write = self._lib.mach_vm_write
        self._write.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.c_uint32,
        ]
        self._write.restype = ctypes.c_int

    def connect(self, pid: int) -> None:
        self.disconnect()
        result = self._task_for_pid(
            self._mach_task_self.value, pid, ctypes.byref(self._task)
        )
        if result != 0:
            raise OSError(
                f"macOS denied access to Cemu (Mach error {result}). "
                + (
                    "Process access requires administrator rights: quit and run "
                    "'sudo python3 trainer.py' from Terminal."
                    if os.geteuid() != 0
                    else "Cemu is signed with the hardened runtime; re-sign it with "
                    "the get-task-allow entitlement (see README)."
                )
            )
        self._connected = True

    def disconnect(self) -> None:
        if self._connected:
            self._mach_port_deallocate(self._mach_task_self.value, self._task.value)
            self._connected = False

    def read(self, address: int, size: int) -> bytes:
        if not self._connected:
            raise OSError("Not connected to Cemu.")
        buffer = ctypes.create_string_buffer(size)
        copied = ctypes.c_uint64()
        result = self._read(
            self._task.value,
            address,
            size,
            ctypes.addressof(buffer),
            ctypes.byref(copied),
        )
        if result != 0 or copied.value != size:
            raise OSError(f"Could not read Cemu memory at 0x{address:X} (Mach error {result}).")
        return buffer.raw[:size]

    def write(self, address: int, data: bytes) -> None:
        if not self._connected:
            raise OSError("Not connected to Cemu.")
        buffer = ctypes.create_string_buffer(data)
        result = self._write(
            self._task.value,
            address,
            ctypes.addressof(buffer),
            len(data),
        )
        if result != 0:
            raise OSError(f"Could not write Cemu memory at 0x{address:X} (Mach error {result}).")

    def __del__(self) -> None:
        if getattr(self, "_connected", False):
            self.disconnect()


class GameMemory:
    def __init__(self, backend: MachProcessMemory, base: int) -> None:
        self.backend = backend
        self.base = base

    def read(self, offset: int, kind: str) -> int | float:
        sizes = {"u8": 1, "u16": 2, "f32": 4}
        return unpack_value(self.backend.read(self.base + offset, sizes[kind]), kind)

    def read_bytes(self, offset: int, size: int) -> bytes:
        return self.backend.read(self.base + offset, size)

    def write(self, offset: int, value: int | float, kind: str) -> None:
        self.backend.write(self.base + offset, pack_value(value, kind))

    def set_bit(self, offset: int, bit: int, enabled: bool) -> None:
        current = int(self.read(offset, "u8"))
        value = current | (1 << bit) if enabled else current & ~(1 << bit)
        self.write(offset, value, "u8")


class TrainerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Wind Waker HD Trainer · Cemu")
        self.root.geometry("780x720")
        self.root.minsize(700, 620)
        self.backend: MachProcessMemory | None = None
        self.game: GameMemory | None = None
        self.pid: int | None = None
        self.refreshing = False
        self.variables: dict[str, tk.Variable] = {}
        self.bit_sets: dict[int, tuple[tk.BooleanVar, ...]] = {}

        style = ttk.Style()
        style.configure("Title.TLabel", font=("Helvetica Neue", 20, "bold"))
        style.configure("Muted.TLabel", foreground="#6b7280")
        style.configure("Section.TLabelframe.Label", font=("Helvetica Neue", 12, "bold"))

        header = ttk.Frame(root, padding=(18, 14, 18, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Wind Waker HD", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="A macOS trainer for The Legend of Zelda: The Wind Waker HD in Cemu",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        connection = ttk.LabelFrame(root, text="Cemu connection", padding=10)
        connection.pack(fill="x", padx=18, pady=(0, 10))
        self.base_var = tk.StringVar()
        ttk.Label(connection, text="Game memory base").grid(row=0, column=0, sticky="w")
        ttk.Entry(connection, textvariable=self.base_var, width=20).grid(
            row=0, column=1, padx=(8, 12), sticky="w"
        )
        ttk.Button(connection, text="Connect / refresh", command=self.connect).grid(
            row=0, column=2, sticky="w"
        )
        self.status_var = tk.StringVar(value="Start Cemu and load Wind Waker HD, then connect.")
        ttk.Label(connection, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        connection.columnconfigure(2, weight=1)

        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        self.player_tab = ttk.Frame(self.tabs, padding=12)
        progress_page = ttk.Frame(self.tabs)
        progress_canvas = tk.Canvas(progress_page, highlightthickness=0)
        progress_scrollbar = ttk.Scrollbar(
            progress_page, orient="vertical", command=progress_canvas.yview
        )
        progress_canvas.configure(yscrollcommand=progress_scrollbar.set)
        progress_scrollbar.pack(side="right", fill="y")
        progress_canvas.pack(side="left", fill="both", expand=True)
        self.progress_tab = ttk.Frame(progress_canvas, padding=12)
        progress_window = progress_canvas.create_window(
            (0, 0), window=self.progress_tab, anchor="nw"
        )
        self.progress_tab.bind(
            "<Configure>",
            lambda _event: progress_canvas.configure(
                scrollregion=progress_canvas.bbox("all")
            ),
        )
        progress_canvas.bind(
            "<Configure>",
            lambda event: progress_canvas.itemconfigure(progress_window, width=event.width),
        )
        self.items_tab = ttk.Frame(self.tabs, padding=12)
        inventory_page = ttk.Frame(self.tabs)
        inventory_canvas = tk.Canvas(inventory_page, highlightthickness=0)
        inventory_scrollbar = ttk.Scrollbar(
            inventory_page, orient="vertical", command=inventory_canvas.yview
        )
        inventory_canvas.configure(yscrollcommand=inventory_scrollbar.set)
        inventory_scrollbar.pack(side="right", fill="y")
        inventory_canvas.pack(side="left", fill="both", expand=True)
        self.inventory_tab = ttk.Frame(inventory_canvas, padding=12)
        inventory_window = inventory_canvas.create_window(
            (0, 0), window=self.inventory_tab, anchor="nw"
        )
        self.inventory_tab.bind(
            "<Configure>",
            lambda _event: inventory_canvas.configure(
                scrollregion=inventory_canvas.bbox("all")
            ),
        )
        inventory_canvas.bind(
            "<Configure>",
            lambda event: inventory_canvas.itemconfigure(inventory_window, width=event.width),
        )
        self.tabs.add(self.player_tab, text="Player")
        self.tabs.add(progress_page, text="Progress")
        self.tabs.add(self.items_tab, text="Equipment")
        self.tabs.add(inventory_page, text="Inventory")
        self._build_player()
        self._build_progress()
        self._build_items()
        self._build_inventory()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._schedule_refresh()

    def _group(self, parent: ttk.Frame, title: str) -> ttk.LabelFrame:
        group = ttk.LabelFrame(parent, text=title, padding=10, style="Section.TLabelframe")
        group.pack(fill="x", pady=(0, 10))
        return group

    def _build_player(self) -> None:
        health = self._group(self.player_tab, "Health and stamina")
        self._number_control(health, 0, "Health (quarters)", "health", "u16", 0, 80)
        self._number_control(health, 1, "Maximum health", "max_health", "u16", 0, 80)
        ttk.Label(health, text="Stamina capacity").grid(row=2, column=0, sticky="w", pady=3)
        self.stamina_cap = tk.StringVar(value="32")
        ttk.Combobox(
            health, textvariable=self.stamina_cap, values=("0", "16", "32"),
            state="readonly", width=8,
        ).grid(row=2, column=1, sticky="w", padx=8, pady=3)
        ttk.Button(health, text="Set", command=self._set_stamina_cap).grid(row=2, column=2)
        self._number_control(health, 3, "Current stamina", "stamina", "u8", 0, 255)
        self.infinite_breath = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            health, text="Infinite underwater breath", variable=self.infinite_breath
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))
        health.columnconfigure(3, weight=1)

        rupees = self._group(self.player_tab, "Rupees")
        self._number_control(rupees, 0, "Current rupees", "rupees", "u16", 0, 5000)
        ttk.Label(rupees, text="Wallet capacity").grid(row=1, column=0, sticky="w", pady=3)
        self.wallet_cap = tk.StringVar(value="5000")
        ttk.Combobox(
            rupees, textvariable=self.wallet_cap, values=("500", "1000", "5000"),
            state="readonly", width=8,
        ).grid(row=1, column=1, sticky="w", padx=8, pady=3)
        ttk.Button(rupees, text="Set", command=self._set_wallet_cap).grid(row=1, column=2)
        self._number_control(rupees, 2, "Beedle points", "beedle_points", "u8", 0, 255)
        rupees.columnconfigure(3, weight=1)

        position = self._group(self.player_tab, "Player coordinates")
        self.position_vars = {}
        for row, axis in enumerate(("X", "Y", "Z")):
            ttk.Label(position, text=axis).grid(row=0, column=row * 2, padx=(0, 4))
            variable = tk.StringVar(value="0.000")
            self.position_vars[axis.lower()] = variable
            ttk.Entry(position, textvariable=variable, width=13).grid(
                row=0, column=row * 2 + 1, padx=(0, 10)
            )
        ttk.Button(position, text="Teleport", command=self._teleport).grid(
            row=0, column=6, padx=(4, 0)
        )
        position.columnconfigure(7, weight=1)

    def _number_control(
        self,
        parent: ttk.LabelFrame,
        row: int,
        label: str,
        key: str,
        kind: str,
        minimum: int,
        maximum: int,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        variable = tk.StringVar(value="0")
        self.variables[key] = variable
        ttk.Entry(parent, textvariable=variable, width=10).grid(
            row=row, column=1, sticky="w", padx=8, pady=3
        )
        ttk.Button(
            parent,
            text="Set",
            command=lambda: self._set_number(key, kind, minimum, maximum),
        ).grid(row=row, column=2, sticky="w", pady=3)

    def _build_progress(self) -> None:
        relics = self._group(self.progress_tab, "Relics and abilities")
        self._bit_controls(relics, "Pearls", ("Nayru", "Din", "Farore"), OFFSETS["pearls"], columns=3)
        self._bit_controls(
            relics,
            "Triforce fragments",
            tuple(f"Fragment {i}" for i in range(1, 9)),
            OFFSETS["triforce"],
            columns=4,
        )
        flags = self._group(self.progress_tab, "Unlocks")
        self._byte_controls(
            flags,
            (("Power bracelets", OFFSETS["bracelet"]),
             ("Pirate's charm", OFFSETS["pirate_charm"]),
             ("Hero's charm", OFFSETS["hero_amulet"])),
            columns=3,
        )
        sea = self._group(self.progress_tab, "Sea chart and treasure chart discoveries")
        grid = ttk.Frame(sea)
        grid.pack(anchor="w")
        self.map_vars: dict[str, tk.BooleanVar] = {}
        for row, letter in enumerate("ABCDEFG"):
            ttk.Label(grid, text=letter, width=3).grid(row=row + 1, column=0)
            for col in range(1, 8):
                name = f"{letter}{col}"
                variable = tk.BooleanVar(value=False)
                self.map_vars[name] = variable
                ttk.Checkbutton(
                    grid,
                    text=str(col),
                    variable=variable,
                    command=lambda n=name: self._set_map(n),
                ).grid(row=row + 1, column=col, padx=2)
        for col, number in enumerate(range(1, 8), 1):
            ttk.Label(grid, text=str(number)).grid(row=0, column=col)
        charts = ttk.Frame(sea)
        charts.pack(anchor="w", pady=(10, 0))
        self._bit_controls(
            charts,
            "Treasure charts (pack / bit)",
            tuple(f"{pack}/{bit}" for pack in range(1, 9) for bit in range(1, 9)),
            OFFSETS["map_charts"],
            columns=8,
        )
        self._bit_controls(
            sea,
            "Decoded Triforce charts",
            ("Chart 1", "Chart 2", "Chart 3"),
            OFFSETS["triforce_charts"],
            columns=3,
            bit_positions=(0, 2, 4),
        )

    def _build_items(self) -> None:
        combat = self._group(self.items_tab, "Weapons and ammunition")
        self._choice_control(combat, 0, "Sword", "sword", {
            "None": 0, "Hero's Sword": 1, "Master Sword (unpowered)": 3,
            "Master Sword (half power)": 7, "Master Sword (fully powered)": 15,
        })
        self._choice_control(combat, 1, "Shield", "shield", {
            "None": 0, "Hero's Shield": 1, "Mirror Shield": 3,
        })
        for row, label, key in (
            (2, "Arrow capacity", "max_arrows"),
            (3, "Bomb capacity", "max_bombs"),
            (4, "Arrows", "arrows"),
            (5, "Bombs", "bombs"),
        ):
            self._number_control(combat, row, label, key, "u8", 0, 99)

        gear = self._group(self.items_tab, "Gear unlocks")
        self.gear_vars: dict[str, tk.BooleanVar] = {}
        gear_items = tuple((name, address) for name, address in GEAR_FLAGS.items() if name != "Bow")
        for index, (name, address) in enumerate(gear_items):
            row, column = divmod(index, 3)
            variable = tk.BooleanVar(value=False)
            self.gear_vars[name] = variable
            ttk.Checkbutton(
                gear,
                text=name,
                variable=variable,
                command=lambda n=name, a=address: self._set_flag(n, a),
            ).grid(row=row, column=column, sticky="w", padx=(0, 12), pady=2)
        bow_row = (len(gear_items) + 2) // 3
        ttk.Label(gear, text="Bow").grid(row=bow_row, column=0, sticky="w", pady=3)
        self.bow_var = tk.StringVar(value="Not unlocked")
        self.bow_values = {
            "Not unlocked": 0,
            "Hero's Bow": 1,
            "Fire and Ice Arrows": 3,
            "Fire, Ice and Light Arrows": 7,
        }
        ttk.Combobox(
            gear, textvariable=self.bow_var, values=tuple(self.bow_values),
            state="readonly", width=29,
        ).grid(row=bow_row, column=1, sticky="w", padx=8, pady=3)
        ttk.Button(
            gear,
            text="Set",
            command=lambda: self._write(OFFSETS["bow"], self.bow_values[self.bow_var.get()], "u8"),
        ).grid(row=bow_row, column=2, sticky="w", pady=3)

        songs = self._group(self.items_tab, "Songs")
        self.song_vars: list[tk.BooleanVar] = []
        for index, name in enumerate(SONG_NAMES):
            variable = tk.BooleanVar(value=False)
            self.song_vars.append(variable)
            ttk.Checkbutton(
                songs,
                text=name,
                variable=variable,
                command=lambda bit=index: self._set_bit(
                    OFFSETS["songs"], bit, self.song_vars[bit].get()
                ),
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 20), pady=2)

    def _build_inventory(self) -> None:
        group = self._group(self.inventory_tab, "Inventory item slots")
        ttk.Label(
            group,
            text="Choose an item for each slot. Use a save-state before bulk changes.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.inventory_vars: list[tk.StringVar] = []
        self.inventory_item_ids = {value: label for label, value in INVENTORY_ITEMS.items()}
        for slot in range(21):
            row = slot + 1
            ttk.Label(group, text=f"Slot {slot + 1:02}").grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=2
            )
            variable = tk.StringVar(value="Empty slot")
            self.inventory_vars.append(variable)
            ttk.Combobox(
                group,
                textvariable=variable,
                values=tuple(INVENTORY_ITEMS),
                state="readonly",
                width=34,
            ).grid(row=row, column=1, sticky="w", pady=2)
            ttk.Button(
                group,
                text="Set",
                command=lambda index=slot, choice=variable: self._set_inventory_slot(
                    index, choice.get()
                ),
            ).grid(row=row, column=2, sticky="w", padx=(8, 0), pady=2)

    def _bit_controls(
        self,
        parent: ttk.Widget,
        title: str,
        labels: tuple[str, ...],
        offset: int,
        columns: int,
        bit_positions: tuple[int, ...] | None = None,
    ) -> None:
        group = ttk.LabelFrame(parent, text=title, padding=6)
        group.pack(fill="x", anchor="w", pady=(2, 4))
        variables: list[tk.BooleanVar] = []
        for index, label in enumerate(labels):
            variable = tk.BooleanVar(value=False)
            variables.append(variable)
            bit = bit_positions[index] if bit_positions else index % 8
            byte_offset = offset + (index // 8 if not bit_positions else 0)
            ttk.Checkbutton(
                group,
                text=label,
                variable=variable,
                command=lambda o=byte_offset, b=bit, v=variable: self._set_bit(
                    o, b, v.get()
                ),
            ).grid(
                row=index // columns,
                column=index % columns,
                sticky="w",
                padx=(0, 8),
                pady=1,
            )
        self.bit_sets[offset] = tuple(variables)

    def _byte_controls(
        self,
        parent: ttk.LabelFrame,
        choices: tuple[tuple[str, int], ...],
        columns: int,
    ) -> None:
        for index, (label, address) in enumerate(choices):
            variable = tk.BooleanVar(value=False)
            self.gear_vars_for_address = getattr(self, "gear_vars_for_address", {})
            self.gear_vars_for_address[address] = variable
            ttk.Checkbutton(
                parent,
                text=label,
                variable=variable,
                command=lambda a=address, v=variable: self._set_flag(
                    "Unlock", a, v.get()
                ),
            ).grid(row=index // columns, column=index % columns, sticky="w", padx=5)

    def _choice_control(
        self, parent: ttk.LabelFrame, row: int, label: str, key: str, choices: dict[str, int]
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        variable = tk.StringVar(value=next(iter(choices)))
        self.variables[key] = variable
        selector = ttk.Combobox(
            parent, textvariable=variable, values=tuple(choices), state="readonly", width=29
        )
        selector.grid(row=row, column=1, sticky="w", padx=8, pady=3)
        ttk.Button(
            parent,
            text="Set",
            command=lambda: self._write(OFFSETS[key], choices[variable.get()], "u8"),
        ).grid(row=row, column=2, sticky="w", pady=3)

    def connect(self) -> None:
        try:
            pid = find_cemu_pid()
            if pid is None:
                raise OSError("Could not find exactly one running Cemu process.")
            base_text = self.base_var.get().strip()
            base = int(base_text, 16 if not base_text.lower().startswith("0x") else 0) if base_text else find_cemu_base()
            if base is None or base <= 0:
                raise ValueError(
                    "Cemu's game memory base was not found in log.txt. Enter the base "
                    "address shown in Cemu's log, then connect again."
                )
            if base > 0xFFFFFFFFFFFFFFFF - max(OFFSETS.values()):
                raise ValueError("The base address is outside the supported address range.")
            backend = MachProcessMemory()
            backend.connect(pid)
            if self.backend is not None:
                self.backend.disconnect()
            self.backend = backend
            self.game = GameMemory(backend, base)
            self.pid = pid
            self.base_var.set(f"0x{base:X}")
            self.status_var.set(f"Connected to Cemu (PID {pid}) · base 0x{base:X}")
            self.refresh()
        except (OSError, ValueError) as exc:
            self.status_var.set(str(exc))
            messagebox.showerror("Cemu connection failed", str(exc), parent=self.root)

    def _write(self, offset: int, value: int | float, kind: str) -> None:
        if self.game is None:
            self.status_var.set("Connect to Cemu before changing game values.")
            return
        try:
            self.game.write(offset, value, kind)
            self.status_var.set(f"Updated game memory at 0x{offset:X}.")
        except (OSError, ValueError) as exc:
            self._memory_error(exc)

    def _set_number(self, key: str, kind: str, minimum: int, maximum: int) -> None:
        try:
            value = int(str(self.variables[key].get()), 10)
            if not minimum <= value <= maximum:
                raise ValueError(f"Enter a value from {minimum} to {maximum}.")
            self._write(OFFSETS[key], value, kind)
            if key == "rupees" and self.game is not None:
                self._write(OFFSETS["rupees_ui"], value, "u16")
        except ValueError as exc:
            messagebox.showerror("Invalid value", str(exc), parent=self.root)

    def _set_stamina_cap(self) -> None:
        self._write(OFFSETS["max_stamina"], int(self.stamina_cap.get()), "u8")

    def _set_wallet_cap(self) -> None:
        encoded = {"500": 0, "1000": 1, "5000": 2}[self.wallet_cap.get()]
        self._write(OFFSETS["rupee_capacity"], encoded, "u8")

    def _teleport(self) -> None:
        try:
            values = {axis: float(variable.get()) for axis, variable in self.position_vars.items()}
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError("Coordinates must be finite numbers.")
        except ValueError:
            messagebox.showerror(
                "Invalid coordinates", "Enter finite numbers for X, Y and Z.", parent=self.root
            )
            return
        for axis in ("x", "y", "z"):
            self._write(OFFSETS[f"player_{axis}"], values[axis], "f32")

    def _set_flag(self, name: str, address: int, enabled: bool | None = None) -> None:
        value = enabled
        if value is None:
            value = self.gear_vars[name].get()
        self._write(address, int(value), "u8")

    def _set_bit(self, offset: int, bit: int, enabled: bool) -> None:
        if self.game is None:
            self.status_var.set("Connect to Cemu before changing game values.")
            return
        try:
            self.game.set_bit(offset, bit, enabled)
        except (OSError, ValueError) as exc:
            self._memory_error(exc)

    def _set_map(self, name: str) -> None:
        if self.game is None:
            self.status_var.set("Connect to Cemu before changing game values.")
            return
        address = OFFSETS["map_grid"] + (ord(name[0]) - ord("A")) * 7 + int(name[1]) - 1
        unlocked = self.map_vars[name].get()
        self._write(address, 3 if unlocked and name in ("A1", "B4", "G2") else int(unlocked), "u8")

    def _set_inventory_slot(self, slot: int, choice: str) -> None:
        item_id = INVENTORY_ITEMS.get(choice)
        if item_id is None:
            messagebox.showerror("Invalid item", "Choose an item from the list.", parent=self.root)
            return
        self._write(0x145B7BBC + slot, item_id, "u8")

    def _refresh_bits(self, offset: int, variables: tuple[tk.BooleanVar, ...]) -> None:
        if self.game is None:
            return
        byte_values: dict[int, int] = {}
        for index, variable in enumerate(variables):
            byte_offset = offset + index // 8
            if byte_offset not in byte_values:
                byte_values[byte_offset] = int(self.game.read(byte_offset, "u8"))
            byte = byte_values[byte_offset]
            variable.set(bool(byte & (1 << (index % 8))))

    def refresh(self) -> None:
        if self.game is None or self.refreshing:
            return
        self.refreshing = True
        try:
            for key, kind in (
                ("health", "u16"), ("max_health", "u16"), ("stamina", "u8"),
                ("rupees", "u16"), ("beedle_points", "u8"), ("arrows", "u8"),
                ("bombs", "u8"), ("max_arrows", "u8"), ("max_bombs", "u8"),
            ):
                self.variables[key].set(str(self.game.read(OFFSETS[key], kind)))
            capacity = int(self.game.read(OFFSETS["rupee_capacity"], "u8"))
            self.wallet_cap.set({0: "500", 1: "1000", 2: "5000"}.get(capacity, "500"))
            self.stamina_cap.set(str(self.game.read(OFFSETS["max_stamina"], "u8")))
            for axis, variable in self.position_vars.items():
                variable.set(f"{float(self.game.read(OFFSETS[f'player_{axis}'], 'f32')):.3f}")
            for name, variable in self.gear_vars.items():
                value = int(self.game.read(GEAR_FLAGS[name], "u8"))
                variable.set(value != 0)
            bow_value = int(self.game.read(OFFSETS["bow"], "u8"))
            self.bow_var.set({
                0: "Not unlocked",
                1: "Hero's Bow",
                3: "Fire and Ice Arrows",
                7: "Fire, Ice and Light Arrows",
            }.get(bow_value, "Not unlocked"))
            for address, variable in self.gear_vars_for_address.items():
                variable.set(int(self.game.read(address, "u8")) != 0)
            for key in ("pearls", "triforce", "map_charts", "triforce_charts", "songs"):
                values = self.bit_sets[OFFSETS[key]]
                if key == "triforce_charts":
                    for index, variable in enumerate(values):
                        byte = int(self.game.read(OFFSETS[key], "u8"))
                        variable.set(bool(byte & (1 << (index * 2))))
                else:
                    self._refresh_bits(OFFSETS[key], values)
            map_bytes = self.game.read_bytes(OFFSETS["map_grid"], 49)
            for name, variable in self.map_vars.items():
                address = OFFSETS["map_grid"] + (ord(name[0]) - ord("A")) * 7 + int(name[1]) - 1
                variable.set(map_bytes[address - OFFSETS["map_grid"]] != 0)
            inventory_bytes = self.game.read_bytes(0x145B7BBC, len(self.inventory_vars))
            for slot, variable in enumerate(self.inventory_vars):
                item_id = inventory_bytes[slot]
                variable.set(self.inventory_item_ids.get(item_id, f"Unknown item ({item_id})"))
            if self.infinite_breath.get():
                self.game.write(OFFSETS["breath"], 900, "u16")
            self.status_var.set(f"Connected to Cemu (PID {self.pid}) · refreshed")
        except (OSError, ValueError, StopIteration) as exc:
            self._memory_error(exc)
        finally:
            self.refreshing = False

    def _memory_error(self, error: Exception) -> None:
        self.status_var.set(f"Memory access failed: {error}")
        if self.backend is not None:
            self.backend.disconnect()
        self.backend = None
        self.game = None

    def _schedule_refresh(self) -> None:
        self.refresh()
        self.root.after(1000, self._schedule_refresh)

    def close(self) -> None:
        if self.backend is not None:
            self.backend.disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TrainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
