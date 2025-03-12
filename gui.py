import tkinter as tk
import re
import os
import subprocess
import sqlite3
from pathlib import Path
from collections import namedtuple
from tkinter import ttk
from tkinter import filedialog
from datetime import datetime, timedelta, date

from db_util import DB
from machine_data import MachineData, AbutmentType, Diameter

BASE_DIR: Path = Path(__file__).resolve().parent
ERP_DIR: Path = Path(r"\\192.168.1.100\Trubox\####ERP_RM####")
MACHINE_DIR: Path = BASE_DIR / "machines"
OUTPUT_DIR: Path = BASE_DIR / "output"

FOOTER_TEXT = """
M2
M99


$2

M2
M99

"""


def date_as_path(date=None) -> Path:
    if date is None:
        date = datetime.now().date()
    _day = f"D{'0' + str(date.day) if date.day < 10 else str(date.day)}"
    _month = f"M{'0' + str(date.month) if date.month < 10 else str(date.month)}"
    _year = f"Y{str(date.year)}"
    return Path(_year, _month, _day)


def get_previous_workday_all_nc_path() -> Path:
    current_date: date = datetime.now().date()
    previous_date: date = current_date - timedelta(days=1)
    if datetime.weekday(current_date) == 0:
        previous_date = current_date - timedelta(days=3)

    return ERP_DIR / date_as_path(previous_date) / Path("1. CAM/3. NC files/ALL")


class CNCFormatter(tk.Frame):
    def __init__(self, parent, db: DB, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.db: DB = db
        self.line_regex: re.Pattern = re.compile(
            r"(?P<machine>[0-9]{2})_[0-9]{1}_[0-9]{3}\s+(?P<pg_id>[0-9]{4})(?![0-9a-zA-Z])"
        )

        self.cnc_data_label: tk.Label = tk.Label(
            self, text="Paste Data Below", font="Arial 11 bold"
        )

        self.nc_file_path: tk.StringVar = tk.StringVar(
            self, value=str(get_previous_workday_all_nc_path())
        )
        self.folder_selection_frame: tk.Frame = tk.Frame(self)
        self.folder_selection_frame.grid_columnconfigure(0, weight=1)
        self.prg_folder_path_entry: ttk.Entry = ttk.Entry(
            self.folder_selection_frame, textvariable=self.nc_file_path
        )
        self.prg_folder_path_entry.insert(0, "./")
        self.add_files_btn: tk.Button = tk.Button(
            self.folder_selection_frame,
            text="Select PRG Folder",
            command=self.select_nc_file_folder,
        )
        self.prg_folder_path_entry.grid(row=2, column=0, sticky="nswe")
        self.add_files_btn.grid(row=2, column=1)

        self.cnc_data_textarea: tk.Text = tk.Text(self)
        self.cnc_data_textarea.tag_configure(
            "error",
            background="#f7b0b0",
            foreground="#000000",
            selectbackground="#0078d7",
            selectforeground="#ffffff",
        )
        self.cnc_data_textarea.event_delete("<<Paste>>", "<Control-V>")
        self.cnc_data_textarea.bind("<Control-V>", self.on_paste)

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
        self.cnc_data_textarea.grid(
            row=1, column=0, sticky="nsew", padx=5, pady=5, columnspan=2
        )
        self.y_scroll.grid(row=1, column=1, sticky="ns")
        self.folder_selection_frame.grid(row=2, columnspan=2, sticky="nsew", padx=5)
        self.cnc_process_data_btn.grid(
            row=3, column=0, sticky="we", padx=5, pady=5, columnspan=2
        )

        if os.name == "nt":
            self.cnc_data_textarea.bind("<Button-3>", self.on_right_click)
        else:
            self.cnc_data_textarea.bind("<Button-2>", self.on_right_click)

    def select_nc_file_folder(self) -> None:
        nc_file_path = filedialog.askdirectory(
            initialdir=get_previous_workday_all_nc_path()
        )
        self.nc_file_path.set(nc_file_path)

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
            line_regex: re.Match | None = self.line_regex.match(line)
            if line_regex:
                machine_number = line_regex.group("machine")
                pg_id = line_regex.group("pg_id")
                if not machines.get(machine_number):
                    machines[machine_number] = [pg_id]
                else:
                    machines[machine_number].append(pg_id)

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

            machine_settings_file: Path = MACHINE_DIR.joinpath(f"{int(machine)}.txt")
            if machine_settings_file.exists():
                with open(machine_settings_file) as machine_file:
                    content = machine_file.read()

                file.write(content)

    def is_valid(self, line_text: str) -> bool:
        if re.match(r"\s+[\n]?", line_text) or line_text == "":
            return True

        line_regex: re.Match | None = self.line_regex.match(line_text)

        if not line_regex:
            return False

        return True

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


class AbutmentTypeChoice(tk.Frame):
    def __init__(
        self,
        parent,
        title: str | None = None,
        values: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)

        if values is None:
            self.values: list[str] = []
        else:
            self.values = values

        self.grid_columnconfigure(0, weight=1)
        if title is not None:
            tk.Label(self, text=title, background="#FFFFFF", anchor="w").grid(
                row=0, column=0, sticky="we"
            )
        for i, value in enumerate(self.values):
            tk.Checkbutton(
                self,
                text=f"{value}",
                onvalue=True,
                offvalue=False,
                anchor="w",
                background="#FFFFFF",
            ).grid(row=i + 1, column=0, sticky="we")


class MachineSettings(tk.Frame):
    def __init__(self, parent, db: DB, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.bind("<<field_edited>>", parent.update_machine)

        self.circle_choice = tk.StringVar(value="")
        self.abutment_choice = tk.StringVar(value="")

        self.circle_frame = tk.Frame(self)
        self.circle_lbl = tk.Label(
            self.circle_frame, text="Supported Diameter", anchor="w"
        )
        self.circle_dropdown = ttk.Combobox(
            self.circle_frame,
            values=["Ø10", "Ø14"],
            state="readonly",
            textvariable=self.circle_choice,
        )
        self.circle_dropdown.bind("<<ComboboxSelected>>", self.on_field_edit)
        self.circle_lbl.pack(side=tk.TOP, anchor="w")
        self.circle_dropdown.pack(side=tk.LEFT)

        self.abutment_choice_frame = tk.Frame(self)
        self.abutment_choice_lbl = tk.Label(
            self.abutment_choice_frame, text="Supported Abutments", anchor="w"
        )
        self.abutment_choice_dropdown = ttk.Combobox(
            self.abutment_choice_frame,
            values=["DS", "ASC", "AOT & T-L", "AOT PLUS"],
            state="readonly",
            textvariable=self.abutment_choice,
        )
        self.abutment_choice_dropdown.bind("<<ComboboxSelected>>", self.on_field_edit)
        self.abutment_choice_lbl.pack(side=tk.TOP, anchor="w")
        self.abutment_choice_dropdown.pack(side=tk.LEFT)

        self.text_frame = tk.Frame(self)
        self.text_frame_lbl = tk.Label(self.text_frame, text="Ending Machine Code")
        self.text_frame.grid_columnconfigure(0, weight=1)
        self.text_frame.grid_rowconfigure(1, weight=1)
        self.textbox = tk.Text(self.text_frame)
        self.y_scroll: ttk.Scrollbar = ttk.Scrollbar(
            self.text_frame, orient="vertical", command=self.textbox.yview
        )
        self.textbox["yscrollcommand"] = self.y_scroll.set

        self.text_frame_lbl.grid(row=0, column=0, sticky="w")
        self.textbox.grid(row=1, column=0, sticky="nsew")
        self.y_scroll.grid(row=1, column=1, sticky="ns")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.circle_frame.grid(row=0, column=0, sticky="nswe", padx=5, pady=5)
        self.abutment_choice_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.text_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        self.textbox.event_delete("<<Paste>>", "<Control-V>")
        self.textbox.bind("<Control-V>", self.on_paste)

        self.textbox.bind("<<Cut>>", self.on_cut)
        self.textbox.bind("<<Copy>>", self.on_copy)
        self.textbox.bind("<KeyRelease>", self.on_field_edit)

        if os.name == "nt":
            self.textbox.bind("<Button-3>", self.on_right_click)
        else:
            self.textbox.bind("<Button-2>", self.on_right_click)

    def populate(self, machine_data: MachineData) -> None:
        match machine_data.supported_diameter:
            case Diameter.PI10:
                self.circle_choice.set("Ø10")
            case Diameter.PI14:
                self.circle_choice.set("Ø14")

        match machine_data.supported_abutment:
            case AbutmentType.DS:
                self.abutment_choice.set("DS")
            case AbutmentType.ASC:
                self.abutment_choice.set("ASC")
            case AbutmentType.AOT_AND_TLOC:
                self.abutment_choice.set("AOT & T-L")
            case AbutmentType.AOT_PLUS:
                self.abutment_choice.set("AOT PLUS")

        self.textbox.delete("1.0", "end")
        self.textbox.insert("end", machine_data.ending_machine_code)

    def on_field_edit(self, *args) -> None:
        self.event_generate("<<field_edited>>")

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
            self.on_field_edit()

    def on_copy(self, event=None) -> None:
        if self.textbox.tag_ranges("sel"):
            selected_text: str = self.textbox.get("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(selected_text)

    def on_paste(self, event=None) -> None:
        clipboard_text: str = self.clipboard_get()
        clipboard_text += "\n"
        if self.textbox.tag_ranges("sel"):
            self.textbox.delete("sel.first", "sel.last")
        self.textbox.insert("current", clipboard_text)
        self.on_field_edit()


class MachineTab(tk.Frame):
    def __init__(self, parent, db: DB, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.db: DB = db

        self.add_machine_btn: tk.Button = tk.Button(
            self, text="+ Add Machine", command=self.add_machine
        )
        self.listbox = tk.Listbox(self, width=10, exportselection=False)
        self.machine_settings = MachineSettings(self, db)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.add_machine_btn.grid(row=0, column=0, sticky="nsew")
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.machine_settings.grid(row=0, column=1, rowspan=2, sticky="nsew")

        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.listbox.bind("<Button-1>", self.on_listbox_click)
        # self.textbox.bind("<KeyRelease>", self.on_textbox_edit)

        self.bind("<<field_edited>>", self.update_machine)

        if os.name == "nt":
            self.listbox.bind("<Button-3>", self.on_listbox_right_click)
        else:
            self.listbox.bind("<Button-2>", self.on_listbox_right_click)

        self.populate_machine_listbox()

    def on_listbox_click(self, event) -> None:
        if self.listbox.curselection():
            self.listbox.activate(self.listbox.curselection())

    def on_listbox_select(self, event) -> None:
        if self.listbox.curselection():
            selected_item: str = self.listbox.get(self.listbox.curselection())
            machine_number: int = int(selected_item.split(" ")[1])
            machine_data: MachineData | None = self.db.get_machine_by_machine_number(
                machine_number
            )
            if machine_data:
                self.machine_settings.populate(machine_data)

    def populate_machine_listbox(self) -> None:
        for machine in self.db.get_all_machines():
            self.listbox.insert(tk.END, f"Machine {machine.machine_number}")

    def add_machine(self) -> None:
        machine_count: int = len(self.db.get_all_machines())
        self.db.add_machine(
            MachineData(machine_count + 1, Diameter.PI10, AbutmentType.DS, "")
        )
        self.listbox.insert("end", f"Machine {machine_count + 1}")
        self.db.con.commit()

    def update_machine(self, event) -> None:
        current_selection = self.listbox.curselection()

        if not current_selection:
            return

        selected_item: str = self.listbox.get(current_selection)
        machine_number: int = int(selected_item.split(" ")[1])

        diameter: Diameter = Diameter.PI10
        abutment_type: AbutmentType = AbutmentType.DS
        match self.machine_settings.circle_choice.get():
            case "Ø10":
                diameter = Diameter.PI10
            case "Ø14":
                diameter = Diameter.PI14
        
        match self.machine_settings.abutment_choice.get():
            case "DS":
                abutment_type = AbutmentType.DS
            case "ASC":
                abutment_type = AbutmentType.ASC
            case "AOT & T-L":
                abutment_type = AbutmentType.AOT_AND_TLOC
            case "AOT PLUS":
                abutment_type = AbutmentType.AOT_PLUS
        
        machine_data: MachineData = MachineData(machine_number, diameter, abutment_type, self.machine_settings.textbox.get('1.0', 'end'))
        self.db.update_machine(machine_data)
        self.db.con.commit()

    def delete_machine(self, event=None) -> None:
        current_selection = self.listbox.curselection()

        if not current_selection:
            return

        selected_item: str = self.listbox.get(current_selection)
        machine_number: int = int(selected_item.split(" ")[1])
        machine_data: MachineData | None = self.db.get_machine_by_machine_number(
            machine_number
        )
        if machine_data:
            self.db.delete_machine(machine_data)
            self.listbox.delete(current_selection)
            self.db.con.commit()

    # def on_textbox_edit(self, event=None) -> None:
    #     if self.listbox.curselection():
    #         selected_item = self.listbox.get(self.listbox.curselection())
    #         file_name = selected_item.split(" ")[1] + ".txt"
    #         with open(MACHINE_DIR / file_name, "w+") as file:
    #             file.write(self.textbox.get("1.0", "end"))

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


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.db = DB()

        self.iconbitmap(BASE_DIR.joinpath("resources/bitmap.ico"))
        self.title("CNC Formatter")
        self.option_add("*Font", "Arial 11")
        self.geometry("400x400")

        self.tabmenu: ttk.Notebook = ttk.Notebook(self)
        self.tabmenu.add(
            CNCFormatter(self, self.db), text="Process Data", sticky="nsew"
        )
        self.tabmenu.add(MachineTab(self, self.db), text="Machines")

        self.tabmenu.pack(expand=True, fill=tk.BOTH)
