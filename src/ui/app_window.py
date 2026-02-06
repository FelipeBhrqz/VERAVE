"""CustomTkinter UI for Electoral Auditor."""

from __future__ import annotations

import traceback
from tkinter import filedialog

import customtkinter as ctk

from ..core.csv_loader import load_csv
from ..core.comparator import compare_results
from ..core.pdf_parser import parse_pdf


class AppWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Electoral Auditor")
        self.geometry("900x600")

        self.pdf_path_var = ctk.StringVar()
        self.csv_path_var = ctk.StringVar()

        self._build_layout()

    def _build_layout(self) -> None:
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        pdf_label = ctk.CTkLabel(container, text="Subir Reporte PDF")
        pdf_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        pdf_entry = ctk.CTkEntry(container, textvariable=self.pdf_path_var, width=600)
        pdf_entry.grid(row=1, column=0, sticky="we", padx=(0, 8))

        pdf_button = ctk.CTkButton(container, text="Buscar", command=self._browse_pdf)
        pdf_button.grid(row=1, column=1, sticky="e")

        csv_label = ctk.CTkLabel(container, text="Subir Datos CSV")
        csv_label.grid(row=2, column=0, sticky="w", pady=(16, 8))

        csv_entry = ctk.CTkEntry(container, textvariable=self.csv_path_var, width=600)
        csv_entry.grid(row=3, column=0, sticky="we", padx=(0, 8))

        csv_button = ctk.CTkButton(container, text="Buscar", command=self._browse_csv)
        csv_button.grid(row=3, column=1, sticky="e")

        run_button = ctk.CTkButton(container, text="Continuar", command=self._run_validation)
        run_button.grid(row=4, column=0, pady=(20, 20), sticky="w")

        self.result_box = ctk.CTkTextbox(container, height=300)
        self.result_box.grid(row=5, column=0, columnspan=2, sticky="nsew")

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(5, weight=1)

        self.result_box.tag_config("ok", foreground="#22c55e")
        self.result_box.tag_config("error", foreground="#ef4444")
        self.result_box.tag_config("summary", foreground="#38bdf8")
        self.result_box.tag_config("phase", foreground="#38bdf8")

    def _browse_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.pdf_path_var.set(path)

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            self.csv_path_var.set(path)

    def _run_validation(self) -> None:
        pdf_path = self.pdf_path_var.get().strip()
        csv_path = self.csv_path_var.get().strip()

        self.result_box.delete("1.0", "end")

        if not pdf_path or not csv_path:
            self._append_result("❌ Debes seleccionar un PDF y un CSV.\n", "error")
            return

        try:
            pdf_result = parse_pdf(pdf_path)
            csv_result = load_csv(csv_path, pdf_result.vuelta)
            comparison = compare_results(pdf_result, csv_result)

            for item in comparison.items:
                if item.is_header:
                    self._append_result(item.message + "\n", "phase")
                    continue
                tag = "ok" if item.ok else "error"
                self._append_result(item.message + "\n", tag)

            if comparison.halted:
                self._append_result("\nProceso detenido por inconsistencia.\n", "summary")
                return
        except Exception:
            error_message = traceback.format_exc()
            self._append_result("❌ Error durante la validación:\n", "error")
            self._append_result(error_message + "\n", "error")

    def _append_result(self, text: str, tag: str) -> None:
        self.result_box.insert("end", text, tag)
        self.result_box.see("end")
