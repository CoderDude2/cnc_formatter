import tkinter as tk
import re
import os
import subprocess
from pathlib import Path
from collections import namedtuple
from tkinter import ttk

BASE_DIR: Path = Path(__file__).resolve().parent
MACHINE_DIR: Path = BASE_DIR / "machines"
OUTPUT_DIR: Path = BASE_DIR / "output"

MachineData = namedtuple("MachineData", "machine pg_id")

FOOTER_TEXT = """
M2
M99


$2

M2
M99

"""


class CNCFormatter(tk.Frame):
    def __init__(self) -> None:
        super().__init__()

        self.line_regex: re.Pattern = re.compile(
            r"(?P<machine>[0-9]{2})_[0-9]{1}_[0-9]{3}\s+(?P<pg_id>[0-9]{4})(?![0-9a-zA-Z])"
        )

        self.cnc_data_label: tk.Label = tk.Label(
            self, text="Paste Data Below", font="Arial 11 bold"
        )

        self.cnc_data_textarea: tk.Text = tk.Text(self)
        self.cnc_data_textarea.tag_configure(
            "error",
            background="#f7b0b0",
            foreground="#000000",
            selectbackground="#0078d7",
            selectforeground="#ffffff",
        )
        self.cnc_data_textarea.bind("<<Paste>>", self.on_paste)

        self.y_scroll: ttk.Scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.cnc_data_textarea.yview
        )
        self.cnc_data_textarea["yscrollcommand"] = self.y_scroll.set

        self.cnc_process_data_btn: tk.Button = tk.Button(
            self,
            text="Process",
            background="#47c9a4",
            foreground="#000000",
            command=self.process_text,
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.cnc_data_label.grid(row=0, column=0, sticky="we", columnspan=2)
        self.cnc_data_textarea.grid(row=1, column=0, sticky="nsew")
        self.y_scroll.grid(row=1, column=1, sticky="ns")
        self.cnc_process_data_btn.grid(
            row=2, column=0, sticky="we", padx=5, pady=5, columnspan=2
        )

        if os.name == "nt":
            self.cnc_data_textarea.bind("<Button-3>", self.on_right_click)
        else:
            self.cnc_data_textarea.bind("<Button-2>", self.on_right_click)

    def process_text(self) -> None:
        for file in OUTPUT_DIR.iterdir():
            if file.is_file():
                os.remove(file)

        lines: list[str] = self.cnc_data_textarea.get("1.0", "end").splitlines()
        machines: dict[str, list[str]] = dict()
        for i, line in enumerate(lines):
            if not self.is_valid(line):
                self.insert_error(i + 1)
                return

            self.remove_error(i + 1)
            machine_data: MachineData | None = self.get_machine_data(line)
            if machine_data:
                if not machines.get(machine_data.machine):
                    machines[machine_data.machine] = [machine_data.pg_id]
                else:
                    machines[machine_data.machine].append(machine_data.pg_id)

        self.cnc_data_textarea.delete("1.0", "end")
        for k, v in machines.items():
            self.create_machine_file(k, v)
        self.open_output_folder()

    def create_machine_file(self, machine: str, pg_ids: list[str]) -> None:
        machine_file_path: Path = OUTPUT_DIR.joinpath(f"{int(machine)}.prg")
        machine_file_path.touch()

        header: str = f"O{int(machine)}(FOR INPUT           )\n$1\n"
        with machine_file_path.open("w+") as file:
            file.write(header)

            num: int = 501
            while num < 505:
                file.write(f"#{num}=\nG4 U0.5\n")
                num += 1

            for pg_id in pg_ids:
                file.write(f"#{num}={pg_id}\nG4 U0.5\n")
                num += 1

            while num < 600:
                file.write(f"#{num}=\nG4 U0.5\n")
                num += 1

            file.write(FOOTER_TEXT)

    def is_valid(self, line_text: str) -> bool:
        if re.match(r"\s+[\n]?", line_text) or line_text == "":
            return True

        line_regex: re.Match | None = self.line_regex.match(line_text)

        if not line_regex:
            return False

        return True

    def get_machine_data(self, line_text: str) -> MachineData | None:
        line_regex: re.Match | None = self.line_regex.match(line_text)
        if line_regex:
            return MachineData(line_regex.group("machine"), line_regex.group("pg_id"))
        return None

    def insert_error(self, line_index: int) -> None:
        line_count: tuple[int] | None = self.cnc_data_textarea.count(
            "1.0", "end", "lines"
        )
        if line_count and line_index < line_count[0]:
            line_text: str = self.cnc_data_textarea.get(
                f"{line_index}.0", f"{line_index}.end"
            )
            if "<-- Incorrect Format" not in line_text and line_text != "\n":
                self.cnc_data_textarea.insert(
                    f"{line_index}.end", " <-- Incorrect Format"
                )
                self.cnc_data_textarea.tag_add(
                    "error", f"{line_index}.0 linestart", f"{line_index}.0 lineend"
                )
            self.cnc_data_textarea.see(f"{line_index}.0")

    def remove_error(self, line_index: int) -> None:
        tags = self.cnc_data_textarea.tag_names(f"{line_index}.0")
        if tags and "error" not in tags:
            return

        text: str = self.cnc_data_textarea.get(
            f"{line_index}.0 linestart", f"{line_index}.0 lineend"
        )
        line_match: re.Match | None = self.line_regex.match(text)

        if line_match:
            self.cnc_data_textarea.replace(
                f"{line_index}.0 linestart",
                f"{line_index}.0 lineend",
                line_match.group(0),
            )

    def open_output_folder(self) -> None:
        subprocess.Popen(rf"explorer {OUTPUT_DIR}", shell=False) 

    def on_right_click(self, event) -> None:
        rightClickMenu = tk.Menu(self, tearoff=False)
        rightClickMenu.add_command(label="Cut", font="Arial 10", command=self.on_cut)
        rightClickMenu.add_command(label="Copy", font="Arial 10", command=self.on_copy)
        rightClickMenu.add_command(
            label="Paste", font="Arial 10", command=self.on_paste
        )
        rightClickMenu.tk_popup(event.x_root, event.y_root)

    def on_cut(self, event=None) -> None:
        if self.cnc_data_textarea.tag_ranges("sel"):
            selected_text: str = self.cnc_data_textarea.get("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.cnc_data_textarea.delete("sel.first", "sel.last")

    def on_copy(self, event=None) -> None:
        if self.cnc_data_textarea.tag_ranges("sel"):
            selected_text: str = self.cnc_data_textarea.get("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(selected_text)

    def on_paste(self, event=None) -> None:
        clipboard_text: str = self.clipboard_get()
        clipboard_text += "\n"
        if self.cnc_data_textarea.tag_ranges("sel"):
            self.cnc_data_textarea.delete("sel.first", "sel.last")
        self.cnc_data_textarea.insert("current", clipboard_text)


class MachineSettings(tk.Frame):
    def __init__(self) -> None:
        super().__init__()
        super().__init__()

        self.add_machine_btn: tk.Button = tk.Button(
            self, text="+ Add Machine", command=self.add_machine
        )
        self.listbox = tk.Listbox(self, width=10, exportselection=False)
        self.textbox = tk.Text(self)

        self.y_scroll: ttk.Scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.textbox.yview
        )
        self.textbox["yscrollcommand"] = self.y_scroll.set

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.add_machine_btn.grid(row=0, column=0, sticky="nsew")
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.textbox.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.y_scroll.grid(row=0, column=2, sticky="ns", rowspan=2)

        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.listbox.bind("<Button-1>", self.on_listbox_click)
        self.textbox.bind("<KeyRelease>", self.on_textbox_edit)
        self.textbox.bind("<<Paste>>", self.on_paste)
        self.textbox.bind("<<Cut>>", self.on_cut)
        self.textbox.bind("<<Copy>>", self.on_copy)

        if os.name == "nt":
            self.textbox.bind("<Button-3>", self.on_right_click)
            self.listbox.bind("<Button-3>", self.on_listbox_right_click)
        else:
            self.textbox.bind("<Button-2>", self.on_right_click)
            self.listbox.bind("<Button-2>", self.on_listbox_right_click)

        self.get_machines()

    def on_listbox_click(self, event) -> None:
        if self.listbox.curselection():
            self.listbox.activate(self.listbox.curselection())

    def on_listbox_select(self, event) -> None:
        if self.listbox.curselection():
            self.textbox.delete("1.0", "end")
            selected_item: str = self.listbox.get(self.listbox.curselection())
            file_name = selected_item.split(" ")[1] + ".txt"
            with open(BASE_DIR / "machines" / file_name, "r") as file:
                contents = file.read()
            self.textbox.insert("end", contents)

    def get_machines(self) -> None:
        files = list(MACHINE_DIR.iterdir())
        files = sorted(files, key=lambda file: int(file.stem))
        for file in files:
            self.listbox.insert(tk.END, f"Machine {file.stem}")

    def add_machine(self) -> None:
        file_count: int = len(list(MACHINE_DIR.iterdir()))
        file_name = MACHINE_DIR / f"{file_count + 1}.txt"
        file_name.touch()
        self.listbox.insert("end", f"Machine {file_count + 1}")

    def delete_machine(self, event=None) -> None:
        if self.listbox.curselection():
            file_name = (
                self.listbox.get(self.listbox.curselection()).split(" ")[1] + ".txt"
            )
            (MACHINE_DIR / file_name).unlink()
            self.listbox.delete(self.listbox.curselection())

    def on_textbox_edit(self, event=None) -> None:
        if self.listbox.curselection():
            selected_item = self.listbox.get(self.listbox.curselection())
            file_name = selected_item.split(" ")[1] + ".txt"
            with open(MACHINE_DIR / file_name, "w+") as file:
                file.write(self.textbox.get("1.0", "end"))

    def on_listbox_right_click(self, event) -> None:
        if self.listbox.get(0, "end"):
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.listbox.nearest(event.y))
            self.listbox.activate(self.listbox.nearest(event.y))
            rightClickMenu = tk.Menu(self, tearoff=False)
            rightClickMenu.add_command(
                label="Delete", font="Arial 10", command=self.delete_machine
            )
            rightClickMenu.tk_popup(event.x_root, event.y_root)

    def on_right_click(self, event) -> None:
        rightClickMenu = tk.Menu(self, tearoff=False)
        rightClickMenu.add_command(label="Cut", font="Arial 10", command=self.on_cut)
        rightClickMenu.add_command(label="Copy", font="Arial 10", command=self.on_copy)
        rightClickMenu.add_command(
            label="Paste", font="Arial 10", command=self.on_paste
        )
        rightClickMenu.tk_popup(event.x_root, event.y_root)

    def on_cut(self, event=None) -> None:
        if self.textbox.tag_ranges("sel"):
            selected_text: str = self.textbox.get("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.textbox.delete("sel.first", "sel.last")
            self.on_textbox_edit()

    def on_copy(self, event=None) -> None:
        if self.textbox.tag_ranges("sel"):
            selected_text: str = self.textbox.get("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.on_textbox_edit()

    def on_paste(self, event=None) -> None:
        clipboard_text: str = self.clipboard_get()
        clipboard_text += "\n"
        if self.textbox.tag_ranges("sel"):
            self.textbox.delete("sel.first", "sel.last")
        self.textbox.insert("current", clipboard_text)
        self.on_textbox_edit()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.iconbitmap(BASE_DIR.joinpath("resources/bitmap.ico"))
        self.title("CNC Formatter")
        self.option_add("*Font", "Arial 11")
        self.geometry("300x400")

        self.tabmenu: ttk.Notebook = ttk.Notebook(self)
        self.tabmenu.add(CNCFormatter(), text="Process Data", sticky="nsew")
        self.tabmenu.add(MachineSettings(), text="Machines")

        self.tabmenu.pack(expand=True, fill=tk.BOTH)
