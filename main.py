import ttkbootstrap as tb
from ttkbootstrap.scrolled import ScrolledText
from datetime import datetime

class ScriptManager:
    def __init__(self, root):
        self.root = root
        self.root.title("FA Script Manager")
        self.root.geometry("1200x800")

        # Define the 3x2 Grid layout
        self.root.columnconfigure((0, 1, 2), weight=1, uniform='column')
        self.root.rowconfigure((0, 1), weight=1, uniform='row')

        self.create_cell_1()  # Script Selection
        self.create_cell_2()  # Config 1
        self.create_cell_3()  # Log 1
        self.create_cell_4()  # Global Dashboard
        self.create_cell_5()  # Config 2 (Multi-unit)
        self.create_cell_6()  # Log 2

    def log_message(self, widget, text):
        now = datetime.now().strftime("%H:%M:%S")
        widget.insert('end', f"[{now}] {text}\n")
        widget.see('end')

    # --- Cell 1: Script Selection ---
    def create_cell_1(self):
        frame = tb.Labelframe(self.root, text=" 1. Script Selection ", bootstyle="primary", padding=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        scripts = ["Database Backup", "API Stress Test", "UI Automation", "Data Cleanup"]
        for script in scripts:
            tb.Checkbutton(frame, text=script, bootstyle="round-toggle").pack(anchor="w", pady=5)

        tb.Button(frame, text="Load Custom Script", bootstyle="outline-primary").pack(fill="x", pady=10)

    # --- Cell 2: Config Panel 1 ---
    def create_cell_2(self):
        frame = tb.Labelframe(self.root, text=" 2. Config Unit A ", bootstyle="info", padding=10)
        frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        tb.Label(frame, text="Username:").pack(anchor="w")
        tb.Entry(frame).pack(fill="x", pady=5)

        tb.Label(frame, text="Timeout (sec):").pack(anchor="w")
        tb.Spinbox(frame, from_=1, to=60).pack(fill="x", pady=5)

        tb.Button(frame, text="▶ Run Unit A", bootstyle="success",
                  command=lambda: self.log_message(self.log1, "Unit A Started...")).pack(fill="x", pady=10)

    # --- Cell 3: Log Panel 1 ---
    def create_cell_3(self):
        frame = tb.Labelframe(self.root, text=" 3. Output Log A ", bootstyle="secondary", padding=10)
        frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        self.log1 = ScrolledText(frame, height=10, autohide=True)
        self.log1.pack(fill="both", expand=True)

    # --- Cell 4: Global Dashboard (Idea) ---
    def create_cell_4(self):
        frame = tb.Labelframe(self.root, text=" 4. Global Stats ", bootstyle="warning", padding=10)
        frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Progress Bar Example
        tb.Label(frame, text="Total Progress:").pack(anchor="w")
        pb = tb.Progressbar(frame, bootstyle="warning-striped", value=65)
        pb.pack(fill="x", pady=10)

        # Quick Stats Buttons
        btn_frame = tb.Frame(frame)
        btn_frame.pack(fill="x")
        tb.Button(btn_frame, text="HALT ALL", bootstyle="danger").pack(side="left", padx=5, expand=True, fill="x")
        tb.Button(btn_frame, text="REPORT", bootstyle="secondary").pack(side="left", padx=5, expand=True, fill="x")

    # --- Cell 5: Config Panel 2 (Parallel Run) ---
    def create_cell_5(self):
        frame = tb.Labelframe(self.root, text=" 5. Config Unit B (Multi) ", bootstyle="info", padding=10)
        frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        tb.Label(frame, text="Parallel Threads:").pack(anchor="w")
        tb.Scale(frame, bootstyle="info", value=2).pack(fill="x", pady=10)

        tb.Checkbutton(frame, text="Synchronize Logs", bootstyle="square-toggle").pack(anchor="w")

        tb.Button(frame, text="▶ Run Unit B", bootstyle="success",
                  command=lambda: self.log_message(self.log2, "Unit B Parallel Task Started...")).pack(fill="x", pady=10)

    # --- Cell 6: Log Panel 2 ---
    def create_cell_6(self):
        frame = tb.Labelframe(self.root, text=" 6. Output Log B ", bootstyle="secondary", padding=10)
        frame.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)
        self.log2 = ScrolledText(frame, height=10, autohide=True)
        self.log2.pack(fill="both", expand=True)

if __name__ == "__main__":
    # Themes: 'superhero', 'darkly', 'flatly', 'journal', etc.
    app_root = tb.Window(themename="superhero")
    gui = ScriptManager(app_root)
    app_root.mainloop()
