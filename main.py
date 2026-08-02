import asyncio
import sys

from textual.app import App
from textual.containers import Horizontal, ScrollableContainer
from textual.css.query import NoMatches
from textual.widgets import Button, DirectoryTree, Footer, Header, Input, Label, RichLog


class NavigableInput(Input):
    config_key: str | None = None

    def on_key(self, event):
        if event.key == "down":
            event.prevent_default()
            self.screen.focus_next()
        elif event.key == "up":
            event.prevent_default()
            self.screen.focus_previous()

    def on_input_changed(self, event: Input.Changed):
        self.set_class(not self.value.strip(), "empty-input")


class NavigableButton(Button):
    def on_key(self, event):
        if event.key == "up":
            event.prevent_default()
            self.screen.focus_previous()


class FilteredTree(DirectoryTree):
    def filter_paths(self, paths):
        for path in paths:
            if path.name == "configs":
                continue
            if path.is_file():
                if path.suffix != ".py":
                    continue
                if path.name == "__init__.py":
                    continue
            yield path


class FSM(App):
    CSS_PATH = "style.tcss"

    selected_script_path = None

    def compose(self):
        yield Header()
        with Horizontal():
            yield FilteredTree("src/scripts", id="tree")
            yield ScrollableContainer(id="input-container")
            yield RichLog(id="output-log", highlight=True, markup=True)
        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        self.selected_script_path = event.path
        config_path = event.path.parent / "configs" / f"{event.path.stem}_config.py"

        container = self.query_one("#input-container", ScrollableContainer)

        container.query(NavigableInput).remove()
        container.query(Label).remove()
        container.query(Button).remove()

        if config_path.exists():
            try:
                lines = config_path.read_text().splitlines()
                for line in lines:
                    clean_line = line.strip()
                    if clean_line:
                        if "=" in clean_line:
                            name, value = clean_line.split("=", 1)
                            container.mount(Label(f"{name.strip()}"))
                            inp = NavigableInput(
                                value=value.strip(),
                                placeholder=f"Default: {value.strip()}",
                            )
                            inp.config_key = name.strip()
                            container.mount(inp)
                        else:
                            container.mount(NavigableInput(value=clean_line))
            except OSError as e:
                container.mount(Label(f"Error reading file: {e}"))
        else:
            container.mount(Label(f"Config not found at: {config_path}"))

        container.mount(NavigableButton("Run", variant="success", id="run-btn"))
        self.update_run_button()

        first_input = container.query(NavigableInput).first()
        if first_input:
            first_input.focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "run-btn":
            self.run_worker(self.execute_script())

    async def execute_script(self):
        if not self.selected_script_path:
            return

        log = self.query_one("#output-log", RichLog)
        log.clear()
        log.write(f"Starting {self.selected_script_path.name}...\n")

        config_path = (
            self.selected_script_path.parent
            / "configs"
            / f"{self.selected_script_path.stem}_config.py"
        )
        if config_path.exists():
            container = self.query_one("#input-container")
            inputs = container.query(NavigableInput)

            try:
                with open(config_path, "w") as f:
                    for inp in inputs:
                        if inp.config_key:
                            f.write(f"{inp.config_key} = {inp.value}\n")
                        else:
                            f.write(f"{inp.value}\n")
            except OSError as e:
                log.write(f"[bold red]Error saving config: {e}[/]\n")
                return

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                str(self.selected_script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            if process.stdout:
                current_line = b""
                while True:
                    chunk = await process.stdout.read(1024)
                    if not chunk:
                        break

                    for i in range(len(chunk)):
                        char = chunk[i : i + 1]
                        if char == b"\r":
                            if current_line:
                                self.sub_title = current_line.decode(
                                    errors="replace"
                                ).strip()
                                current_line = b""
                        elif char == b"\n":
                            log.write(current_line.decode(errors="replace").strip())
                            current_line = b""
                        else:
                            current_line += char

                if current_line:
                    log.write(current_line.decode(errors="replace").strip())

            return_code = await process.wait()
            self.sub_title = ""
            log.write(f"\n[bold green]Finished with exit code {return_code}[/]")
        except OSError as e:
            log.write(f"[bold red]Execution error: {e}[/]")

    def update_run_button(self):
        try:
            btn = self.query_one("#run-btn", Button)
            any_empty = any(not inp.value.strip() for inp in self.query(NavigableInput))
            btn.disabled = any_empty
        except NoMatches:
            pass

    def on_input_changed(self, event: Input.Changed):
        self.update_run_button()


if __name__ == "__main__":
    app = FSM()
    app.run()
