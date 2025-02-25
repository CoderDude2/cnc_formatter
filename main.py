from gui import App
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    app: App = App()
    app.mainloop()


if __name__ == "__main__":
    main()
