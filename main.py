from gui import App
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent


def main() -> None:
    output_path: Path = BASE_DIR.joinpath("output")
    if not output_path.exists():
        output_path.mkdir()

    app: App = App()
    app.mainloop()


if __name__ == "__main__":
    main()
