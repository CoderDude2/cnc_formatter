import tkinter as tk


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
        self.cnc_process_data_btn: tk.Button = tk.Button(
            self, text="Process", background="#47c9a4", foreground="#000000"
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.cnc_data_label.grid(row=0, column=0, sticky="we")
        self.cnc_data_textarea.grid(row=1, column=0, sticky="nsew")
        self.cnc_process_data_btn.grid(row=2, column=0, sticky="we", padx=5, pady=5)
