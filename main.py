from textual.app import App
from textual.widgets import Header, Footer, DirectoryTree


class FSM(App):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self):
        yield Header()
        yield DirectoryTree("src/scripts")
        yield Footer()


if __name__ == "__main__":
    app = FSM()
    app.run()
