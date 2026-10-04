import asyncio
import sys

import aiofiles
from textual.app import App
from textual.containers import Horizontal, ScrollableContainer
from textual.css.query import NoMatches
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
)
from textual.worker import Worker

__version__ = "0.1.9"


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
            if path.name.startswith("__"):
                continue
            if path.name == "configs":
                continue
            if path.is_file() and path.suffix != ".py":
                continue
            yield path


class AppHeader(Header):
    def compose(self):
        yield from super().compose()
        yield Static(f"v{__version__}", classes="version")


class ButtonRow(Horizontal):
    def compose(self):
        yield NavigableButton("Run", variant="success", id="run-btn")
        yield NavigableButton("Stop", variant="error", id="stop-btn", disabled=True)


class FSM(App):
    CSS_PATH = "style.tcss"

    selected_script_path = None
    worker: Worker | None = None

    def compose(self):
        yield AppHeader()
        with Horizontal():
            yield FilteredTree("src/scripts", id="tree")
            yield ScrollableContainer(id="input-container")
            yield RichLog(id="output-log", highlight=True, markup=True)
        yield Footer()

    async def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        self.selected_script_path = event.path
        config_path = event.path.parent / "configs" / f"{event.path.stem}_config.py"

        container = self.query_one("#input-container", ScrollableContainer)

        await container.remove_children()

        if config_path.exists():
            try:
                lines = config_path.read_text().splitlines()
                for line in lines:
                    clean_line = line.strip()
                    if clean_line:
                        if "=" in clean_line:
                            name, value = clean_line.split("=", 1)
                            container.mount(Label(f" {name.strip()}"))
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

        await container.mount(ButtonRow(id="button-row"))
        self.update_run_buttons()

        first_input = next(iter(container.query(NavigableInput)), None)
        if first_input is not None:
            first_input.focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "run-btn":
            self.start_script()
        elif event.button.id == "stop-btn":
            self.stop_script()

    def start_script(self):
        if not self.selected_script_path:
            return
        self.worker = self.run_worker(
            self.execute_script(),
            name="execute_script",
            group="run",
            exclusive=True,
        )
        self.update_run_buttons()

    def stop_script(self):
        if self.worker is not None and not self.worker.is_finished:
            self.worker.cancel()

    def on_worker_state_changed(self, event: Worker.StateChanged):
        if event.worker.group == "run" and event.worker.is_finished:
            self.update_run_buttons()

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
                async with aiofiles.open(config_path, "w") as f:
                    for inp in inputs:
                        if inp.config_key:
                            await f.write(f"{inp.config_key} = {inp.value}\n")
                        else:
                            await f.write(f"{inp.value}\n")
            except OSError as e:
                log.write(f"[bold red]Error saving config: {e}[/]\n")
                return

        process = None
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
            log.write(f"\n[bold green]Finished with exit code {return_code}[/]")
        except OSError as e:
            log.write(f"[bold red]Execution error: {e}[/]")
        except asyncio.CancelledError:
            log.write("\n[bold yellow]Stopped by user[/]")
            raise
        finally:
            self.sub_title = ""
            await self._terminate_process(process)

    async def _terminate_process(self, process):
        if process is None or process.returncode is not None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except asyncio.TimeoutError:
            process.kill()

    def update_run_buttons(self):
        busy = self.worker is not None and not self.worker.is_finished
        try:
            btn = self.query_one("#run-btn", Button)
            any_empty = any(not inp.value.strip() for inp in self.query(NavigableInput))
            btn.disabled = busy or any_empty
        except NoMatches:
            pass
        try:
            self.query_one("#stop-btn", Button).disabled = not busy
        except NoMatches:
            pass

    def on_input_changed(self, event: Input.Changed):
        self.update_run_buttons()


if __name__ == "__main__":
    app = FSM()
    app.run()
