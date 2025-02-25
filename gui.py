import tkinter as tk
from pathlib import Path

BASE_DIR:Path = Path(__file__).resolve().parent


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CNC Formatter")
        self.option_add("*Font", "Arial 11")
        self.geometry("300x400")

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

    def process_text(self) -> None:...

    def insert_error(self, line_index: int) -> None:
        line_count = len(self.cnc_data_textarea.get('1.0', 'end-1l').splitlines())
        if line_index < line_count:
            line_text:str = self.cnc_data_textarea.get(f'{line_index}.0', f'{line_index}.end')
            if '<-- Incorrect Format' not in line_text:
                self.cnc_data_textarea.insert(f'{line_index}.end', ' <-- Incorrect Format')
                self.cnc_data_textarea.tag_add('error', f'{line_index}.0', f'{line_index}.end')
    
    def open_output_folder(self) -> None: ...
