from gui import App
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent
MACHINE_DIR: Path = BASE_DIR / "machines"
OUTPUT_DIR: Path = BASE_DIR / "output"

def main() -> None:
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir()
    
    if not MACHINE_DIR.exists():
        MACHINE_DIR.mkdir()

    app: App = App()
    app.mainloop()


if __name__ == "__main__":
    main()
