import tkinter as tk
import re
from pathlib import Path
from collections import namedtuple

BASE_DIR: Path = Path(__file__).resolve().parent
MachineData = namedtuple("MachineData", "machine pg_id")

FOOTER_TEXT = """
M2
M99


$2

M2
M99

$0
A2-LE-2-20-12-P-M
#814=0000014000
#815=0000005000
#816=0000001000
#817=0002500000
#822=0000000010
#824=-000001000
#818=0000060000
#819=0000001000
#918=0000000000
#821=0000000000
#921=0000000000
#919=0000000000
#922=0000000000
#990=0004136000
#991=0000055000
#992=0000067000
#893=0000000000
#25974=0004050000
#25975=0004058000
#25976=0004058000
#25977=0000000000
#25978=0000000000
#25979=0000000000
#25980=0000000000
%"""

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CNC Formatter")
        self.option_add("*Font", "Arial 11")
        self.geometry("300x400")

        self.event_delete("<<Paste>>", "<Control-v>")

        self.line_regex: re.Pattern = re.compile(
            r"(?P<machine>[0-9]{2})_[0-9]{1}_[0-9]{3}\s+(?P<pg_id>[0-9]{4})(?![0-9a-zA-Z])"
        )

        self.cnc_data_label: tk.Label = tk.Label(
            self, text="Paste Data Below", font="Arial 15"
        )

        self.cnc_data_textarea: tk.Text = tk.Text(self)
        self.cnc_data_textarea.tag_configure(
            "error",
            background="#f7b0b0",
            foreground="#000000",
            selectbackground="#0078d7",
            selectforeground="#ffffff",
        )
        self.cnc_data_textarea.bind("<Control-v>", self.on_paste)

        self.cnc_process_data_btn: tk.Button = tk.Button(
            self,
            text="Process",
            background="#47c9a4",
            foreground="#000000",
            command=self.process_text,
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.cnc_data_label.grid(row=0, column=0, sticky="we")
        self.cnc_data_textarea.grid(row=1, column=0, sticky="nsew")
        self.cnc_process_data_btn.grid(row=2, column=0, sticky="we", padx=5, pady=5)

    def process_text(self) -> None:
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

        self.cnc_data_textarea.delete('1.0', 'end')
        for k,v in machines.items():
            self.create_machine_file(k, v)
    
    def create_machine_file(self, machine: str, pg_ids: list[str]) -> None:
        machine_file_path:Path = BASE_DIR.joinpath(f"output/1{int(machine)}.prg")
        machine_file_path.touch()

        header: str = (f"O1{int(machine)}(FOR INPUT           )\n$1\n")
        with machine_file_path.open('w+') as file:
            file.write(header)

            for i in range(4):
                file.write(f'#50{i+1}=\nG4 U0.5\n')

            num: int = 505
            for pg_id in pg_ids:
                file.write(f'#{num}={pg_id}\nG4 U0.5\n')
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

    def open_output_folder(self) -> None: ...

    def on_paste(self, event) -> None:
        clipboard_text: str = self.clipboard_get()
        clipboard_text += "\n"
        if self.cnc_data_textarea.tag_ranges("sel"):
            self.cnc_data_textarea.delete("sel.first", "sel.last")
        self.cnc_data_textarea.insert("current", clipboard_text)
