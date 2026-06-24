#!/usr/bin/env python3
"""
Monzo Bank Statement Generator
Pixel-perfect replica with editable fields and transaction management
"""

import sys
import os
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QGroupBox, QDateEdit, QDateTimeEdit,
    QHeaderView, QComboBox, QFrame, QScrollArea, QSplitter, QSpinBox,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDate, QDateTime
from PyQt6.QtGui import QFont, QColor, QPalette

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# ── PDF page dimensions (points, same as original) ──────────────────────────
PAGE_W, PAGE_H = 612, 792

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monzo_logo.png")


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


# ── Font registration ─────────────────────────────────────────────────────────
def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Script directory — fonts are bundled alongside the .py file
    BASE = os.path.dirname(os.path.abspath(__file__))

    # Prefer bundled fonts (work on all platforms)
    # Fall back to system paths on Linux/macOS if bundles are missing
    candidates = {
        "CarlitoBold": [
            os.path.join(BASE, "Carlito-Bold.ttf"),
            "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
        ],
        "Carlito": [
            os.path.join(BASE, "Carlito-Regular.ttf"),
            "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
        ],
        "LibSans": [
            os.path.join(BASE, "LiberationSans-Regular.ttf"),
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
        "LibSansBold": [
            os.path.join(BASE, "LiberationSans-Bold.ttf"),
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
    }
    for name, paths in candidates.items():
        for path in paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                break
        else:
            raise FileNotFoundError(
                f"Font '{name}' not found. Please place the .ttf files "
                f"in the same folder as this script:\n"
                f"  Carlito-Bold.ttf, Carlito-Regular.ttf,\n"
                f"  LiberationSans-Bold.ttf, LiberationSans-Regular.ttf"
            )

_register_fonts()


# ── PDF Generation ───────────────────────────────────────────────────────────
def generate_pdf(data: dict, output_path: str):
    """Generate a pixel-perfect Monzo statement PDF."""
    from reportlab.lib.utils import simpleSplit

    c = canvas.Canvas(output_path, pagesize=(PAGE_W, PAGE_H))

    # Helper: convert pdfplumber 'top' coord to ReportLab y
    def y(top): return PAGE_H - top

    # ── Logo ──────────────────────────────────────────────────────────────────
    # Original: x0=59, top=60.35, width=155.25, height=34.7
    if os.path.exists(LOGO_PATH):
        c.drawImage(LOGO_PATH, 59, y(95.05), width=155.25, height=34.7,
                    preserveAspectRatio=True)

    # ── "Statement" — Carlito-Bold 18pt, baseline at top=67.0 ────────────────
    c.setFont("CarlitoBold", 18)
    c.setFillColorRGB(0, 0, 0)
    c.drawRightString(552.6, y(85.0), "Statement")

    # ── Date range — LiberationSans-Bold 12pt, top=93.7 ──────────────────────
    c.setFont("LibSansBold", 12)
    c.setFillColorRGB(0, 0, 0)
    c.drawRightString(552.6, y(105.7), f"{data['date_from']} - {data['date_to']}")

    # ── Name — LiberationSans-Bold 10pt, top=121.1 ───────────────────────────
    c.setFont("LibSansBold", 10)
    c.drawString(59.5, y(131.1), data['name'].upper())

    # ── Address — LiberationSans 10pt, first line top=134.6, leading=11.5 ────
    c.setFont("LibSans", 10)
    addr_lines = data['address'].split('\n')
    addr_top = 134.6
    for line in addr_lines:
        c.drawString(59.5, y(addr_top + 10), line)
        addr_top += 11.5

    # ── Right col: £420.75 (total balance) — LibSansBold 10pt, top=121.1 ────
    total_balance = data['total_balance']
    c.setFont("LibSansBold", 10)
    c.drawRightString(552.6, y(131.1), f"\xa3{total_balance:.2f}")

    # "Total balance" — LibSans 10pt, top=134.6
    c.setFont("LibSans", 10)
    c.setFillColorRGB(0, 0, 0)
    c.drawRightString(552.6, y(144.6), "Total balance")

    # "(Including pots)" — LibSans 7pt, top=148.2, gray
    c.setFont("LibSans", 7)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawRightString(552.6, y(155.2), "(Including pots)")
    c.setFillColorRGB(0, 0, 0)

    # ── £420.75 (balance held with Monzo) — LibSansBold 10pt, top=182.5 ─────
    c.setFont("LibSansBold", 10)
    c.drawRightString(552.6, y(192.5), f"\xa3{total_balance:.2f}")

    # "Balance held with Monzo" — LibSans 7pt, top=196.2
    c.setFont("LibSans", 7)
    c.drawRightString(552.6, y(203.2), "Balance held with Monzo")

    # ── -£273.75 — LiberationSans 14pt, top=222.6 ────────────────────────────
    c.setFont("LibSans", 14)
    c.drawRightString(552.6, y(236.6), f"-\xa3{abs(data['total_outgoings']):.2f}")

    # "Total outgoings" — LibSans 10pt, top=239.0
    c.setFont("LibSans", 10)
    c.drawRightString(552.6, y(249.0), "Total outgoings")

    # ── +£206.09 — Carlito (regular) 14pt, top=266.1 ─────────────────────────
    c.setFont("Carlito", 14)
    c.drawRightString(552.6, y(280.1), f"+\xa3{abs(data['total_incomes']):.2f}")

    # "Total incomes" — LibSans 10pt, top=283.0
    c.setFont("LibSans", 10)
    c.drawRightString(552.6, y(293.0), "Total incomes")

    # ── "Issued on:" — Carlito-Bold 11pt, top=310.2 ──────────────────────────
    c.setFont("CarlitoBold", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawRightString(552.6, y(321.2), f"Issued on: {data['issued_on']}")

    # ── Separator line — light gray 1.5pt, top=338.15 ────────────────────────
    c.setStrokeColorRGB(0.851, 0.851, 0.851)
    c.setLineWidth(1.5)
    c.line(54, y(338.15), 558, y(338.15))

    # ── Table header — Carlito-Bold 11pt ─────────────────────────────────────
    # "Date" and "Description" sit on the bottom line (top=378.9)
    # "(GBP)" sits on a line above (top≈368), "Amount"/"Balance" on bottom line
    c.setFont("CarlitoBold", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(59.5,  y(389.9), "Date")
    c.drawString(149.5, y(389.9), "Description")
    # "(GBP)" label on the line above
    c.drawRightString(449.3, y(378.4), "(GBP)")
    c.drawRightString(552.6, y(378.4), "(GBP)")
    # "Amount" / "Balance" on the bottom line
    c.drawRightString(449.3, y(389.9), "Amount")
    c.drawRightString(552.6, y(389.9), "Balance")

    # Header underline — medium gray 1.5pt, top=393.45
    c.setStrokeColorRGB(0.502, 0.502, 0.502)
    c.setLineWidth(1.5)
    c.line(54, y(393.45), 558, y(393.45))

    # ── Transaction rows ──────────────────────────────────────────────────────
    # Exact row baseline tops from pdfplumber:
    # date col: 400.3, 427.1, 453.9, 480.7  (LibSans 11pt)
    # desc col: 399.6, 426.5, 453.3, 480.1  (LibSans 12pt)
    # amount col: 399.6/425.2, ...           (LibSans 12pt / Carlito 14pt for positives)
    # balance col: 399.6, 426.5, ...         (LibSans 12pt)
    # Row baseline for date: top=400.3, step=26.8
    DATE_TOP   = 400.3
    DESC_TOP   = 399.6
    ROW_STEP   = 26.8

    transactions = data['transactions']
    for i, txn in enumerate(transactions):
        date_y = y(DATE_TOP + i * ROW_STEP + 11)
        desc_y = y(DESC_TOP + i * ROW_STEP + 12)

        # Date — LibSans 11pt
        c.setFont("LibSans", 11)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(59.5, date_y, txn['date'])

        # Description — LibSans 12pt
        c.setFont("LibSans", 12)
        c.drawString(149.5, desc_y, txn['description'])

        # Amount — LibSans 12pt for negatives, Carlito 14pt for positives
        amount = txn['amount']
        if amount < 0:
            amt_str = f"-{abs(amount):.2f}"
            c.setFont("LibSans", 12)
            c.drawRightString(449.3, desc_y, amt_str)
        else:
            amt_str = f"{amount:.2f}"
            # Carlito 14pt sits slightly higher — match original top=425.2 offset
            carlito_y = y(DESC_TOP + i * ROW_STEP + 14)
            c.setFont("Carlito", 14)
            c.drawRightString(449.3, carlito_y, amt_str)

        # Balance — LibSans 12pt
        c.setFont("LibSans", 12)
        c.drawRightString(552.6, desc_y, f"{txn['balance']:.2f}")

        # Dashed separator — placed at DESC_TOP + i*26.88 + 20.88 (exact from original)
        sep_pt = DESC_TOP + i * ROW_STEP + 20.88
        c.setStrokeColorRGB(0.749, 0.749, 0.749)
        c.setLineWidth(0.5)
        c.setDash([0.5, 1], 0)
        c.line(54, y(sep_pt), 558, y(sep_pt))
        c.setDash([], 0)

    # Extra separator after last row at DESC_TOP + n*26.88 + 20.88
    extra_sep = DESC_TOP + len(transactions) * ROW_STEP + 20.88
    c.setStrokeColorRGB(0.749, 0.749, 0.749)
    c.setLineWidth(0.5)
    c.setDash([0.5, 1], 0)
    c.line(54, y(extra_sep), 558, y(extra_sep))
    c.setDash([], 0)

    # ── Disclaimer — LibSans 9pt, first line top=518.5, leading=10.4 ─────────
    disclaimer = (
        "Monzo Bank Limited (https://monzo.com) is a company registered in England "
        "No. 9446231. Registered Office: 38 Finsbury Square, London, EC 2A 1PX. "
        "Monzo Bank Ltd is authorized by the Prudential Regulation Authority and "
        "regulated by the Financial Conduct Authority and the Prudential Regulation "
        "Authority. Our Financial Services Register number is 730427."
    )
    c.setFont("LibSans", 9)
    c.setFillColorRGB(0, 0, 0)
    # Use the exact line-break positions from the original (width=499pt)
    disc_lines = simpleSplit(disclaimer, "LibSans", 9, 499)
    disc_y = y(518.5 + 9)   # baseline = top + font_size
    for line in disc_lines:
        c.drawString(59.5, disc_y, line)
        disc_y -= 10.4

    # ── Page footer — LibSans 9pt, top=702.9 ─────────────────────────────────
    c.setFont("LibSans", 9)
    c.drawRightString(553.4, y(711.9), "Page 1 of 1")

    c.save()

    # ── Patch PDF metadata (CreationDate / ModDate) via pypdf ────────────────
    if data.get('creation_datetime'):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject, create_string_object
        dt = data['creation_datetime']
        tz_offset = dt.utcoffset()
        if tz_offset is None:
            tz_str = "Z"
        else:
            total_secs = int(tz_offset.total_seconds())
            sign = "+" if total_secs >= 0 else "-"
            total_secs = abs(total_secs)
            tz_str = f"{sign}{total_secs//3600:02d}'{(total_secs%3600)//60:02d}'"
        pdf_date = dt.strftime("D:%Y%m%d%H%M%S") + tz_str

        reader = PdfReader(output_path)
        writer = PdfWriter()
        writer.append(reader)
        writer.add_metadata({
            "/CreationDate": pdf_date,
            "/Creator": "Monzo Bank Limited",
            "/Producer": "Monzo Bank Limited",
        })
        # Explicitly remove ModDate so it doesn't appear in file properties
        info = writer._info
        if info and "/ModDate" in info:
            del info.indirect_reference.pdf.objects[info.indirect_reference]
        # Safer approach: overwrite info dict directly
        from pypdf.generic import DictionaryObject, NameObject, create_string_object
        new_info = DictionaryObject()
        new_info[NameObject("/CreationDate")] = create_string_object(pdf_date)
        new_info[NameObject("/Creator")]      = create_string_object("Monzo Bank Limited")
        new_info[NameObject("/Producer")]     = create_string_object("Monzo Bank Limited")
        writer._info = writer._add_object(new_info)
        import tempfile, shutil
        tmp = output_path + ".tmp"
        with open(tmp, "wb") as f:
            writer.write(f)
        shutil.move(tmp, output_path)


# ── UI ────────────────────────────────────────────────────────────────────────
STYLE = """
QMainWindow { background: #f5f5f5; }
QGroupBox {
    font-weight: bold;
    font-size: 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
    background: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #333;
}
QLineEdit, QDateEdit, QDoubleSpinBox, QTextEdit {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    background: white;
}
QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border-color: #e85d2a;
}
QPushButton {
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton#primary {
    background: #e85d2a;
    color: white;
    border: none;
}
QPushButton#primary:hover { background: #d04e1f; }
QPushButton#secondary {
    background: #f0f0f0;
    color: #333;
    border: 1px solid #ccc;
}
QPushButton#secondary:hover { background: #e0e0e0; }
QPushButton#danger {
    background: #fff0f0;
    color: #cc0000;
    border: 1px solid #ffcccc;
}
QPushButton#danger:hover { background: #ffe0e0; }
QTableWidget {
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 12px;
    background: white;
    gridline-color: #eee;
}
QTableWidget::item { padding: 4px 8px; }
QHeaderView::section {
    background: #f8f8f8;
    border: none;
    border-bottom: 1px solid #ddd;
    padding: 6px 8px;
    font-weight: bold;
    font-size: 11px;
}
QLabel#sectionLabel {
    font-size: 11px;
    color: #666;
}
"""


class MonzoGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monzo Statement Generator")
        self.setMinimumSize(860, 700)
        self.resize(960, 780)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._load_defaults()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Title bar
        title_row = QHBoxLayout()
        icon_lbl = QLabel("🏦")
        icon_lbl.setFont(QFont("", 20))
        title_lbl = QLabel("Monzo Statement Generator")
        title_lbl.setFont(QFont("", 16, QFont.Weight.Bold))
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        gen_btn = QPushButton("⬇  Generate PDF")
        gen_btn.setObjectName("primary")
        gen_btn.setFixedHeight(36)
        gen_btn.clicked.connect(self._generate)
        title_row.addWidget(gen_btn)
        root.addLayout(title_row)

        # Two-column layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)
        splitter.addWidget(left)

        # ── Personal Info ────────────────────────────────────────────────────
        info_box = QGroupBox("Personal Information")
        info_form = QVBoxLayout(info_box)
        info_form.setSpacing(8)

        def field_row(label, widget):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("sectionLabel")
            lbl.setFixedWidth(90)
            row.addWidget(lbl)
            row.addWidget(widget)
            return row

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. JOHN SMITH")
        info_form.addLayout(field_row("Full Name:", self.name_edit))

        # Multi-line address — press Enter for each new line
        addr_row = QHBoxLayout()
        addr_lbl = QLabel("Address:")
        addr_lbl.setObjectName("sectionLabel")
        addr_lbl.setFixedWidth(90)
        addr_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        addr_lbl.setContentsMargins(0, 4, 0, 0)
        from PyQt6.QtWidgets import QTextEdit
        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText(
            "One line per row, e.g.:\n123 High Street\nLondon, EC1A 1BB\nUnited Kingdom"
        )
        self.address_edit.setFixedHeight(80)
        self.address_edit.setAcceptRichText(False)
        addr_row.addWidget(addr_lbl)
        addr_row.addWidget(self.address_edit)
        info_form.addLayout(addr_row)

        left_layout.addWidget(info_box)

        # ── Date Info ────────────────────────────────────────────────────────
        date_box = QGroupBox("Statement Dates")
        date_form = QVBoxLayout(date_box)
        date_form.setSpacing(8)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("MMM d, yyyy")
        date_form.addLayout(field_row("From:", self.date_from))

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("MMM d, yyyy")
        date_form.addLayout(field_row("To:", self.date_to))

        self.issued_on = QDateEdit()
        self.issued_on.setCalendarPopup(True)
        self.issued_on.setDisplayFormat("MMM d, yyyy")
        date_form.addLayout(field_row("Issued On:", self.issued_on))

        # PDF metadata CreationDate
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #eee;")
        date_form.addWidget(sep)

        meta_lbl = QLabel("PDF File Metadata")
        meta_lbl.setObjectName("sectionLabel")
        meta_lbl.setStyleSheet("font-weight: bold; color: #555; padding: 2px 0;")
        date_form.addWidget(meta_lbl)

        self.creation_datetime = QDateTimeEdit()
        self.creation_datetime.setCalendarPopup(True)
        self.creation_datetime.setDisplayFormat("yyyy-MM-dd  HH:mm:ss")
        self.creation_datetime.setDateTime(QDateTime.currentDateTime())
        date_form.addLayout(field_row("CreationDate:", self.creation_datetime))

        left_layout.addWidget(date_box)

        # ── Summary figures (auto or override) ───────────────────────────────
        summary_box = QGroupBox("Statement Summary (auto-calculated)")
        summary_layout = QVBoxLayout(summary_box)
        summary_layout.setSpacing(8)

        self.lbl_total_balance = QLabel("Total Balance (incl. pots): £0.00")
        self.lbl_total_balance.setFont(QFont("", 11, QFont.Weight.Bold))
        self.lbl_outgoings = QLabel("Total Outgoings: £0.00")
        self.lbl_incomes = QLabel("Total Incomes: £0.00")
        summary_layout.addWidget(self.lbl_total_balance)
        summary_layout.addWidget(self.lbl_outgoings)
        summary_layout.addWidget(self.lbl_incomes)

        note = QLabel("ℹ  Balance is calculated by replaying transactions from opening balance.")
        note.setObjectName("sectionLabel")
        note.setWordWrap(True)
        summary_layout.addWidget(note)

        self.opening_balance = QDoubleSpinBox()
        self.opening_balance.setRange(-999999, 999999)
        self.opening_balance.setDecimals(2)
        self.opening_balance.setPrefix("£")
        self.opening_balance.valueChanged.connect(self._recalculate)
        summary_layout.addLayout(field_row("Opening Bal.:", self.opening_balance))

        left_layout.addWidget(summary_box)
        left_layout.addStretch()

        # Right panel – Transactions
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)
        splitter.addWidget(right)

        txn_label = QLabel("Transactions")
        txn_label.setFont(QFont("", 13, QFont.Weight.Bold))
        right_layout.addWidget(txn_label)

        # Toolbar
        toolbar = QHBoxLayout()
        add_btn = QPushButton("＋ Add Row")
        add_btn.setObjectName("secondary")
        add_btn.clicked.connect(self._add_row)
        del_btn = QPushButton("✕ Delete Selected")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_selected)
        up_btn = QPushButton("▲")
        up_btn.setObjectName("secondary")
        up_btn.setFixedWidth(36)
        up_btn.clicked.connect(self._move_up)
        dn_btn = QPushButton("▼")
        dn_btn.setObjectName("secondary")
        dn_btn.setFixedWidth(36)
        dn_btn.clicked.connect(self._move_down)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(del_btn)
        toolbar.addWidget(up_btn)
        toolbar.addWidget(dn_btn)
        toolbar.addStretch()
        right_layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Date", "Description", "Amount (£)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._recalculate)
        right_layout.addWidget(self.table)

        hint = QLabel("Amount: positive = income (e.g. 71.70), negative = outgoing (e.g. -134.03)")
        hint.setObjectName("sectionLabel")
        right_layout.addWidget(hint)

        splitter.setSizes([340, 580])

    def _load_defaults(self):
        self.name_edit.setText("John Smith")
        self.address_edit.setPlainText("2 Upper Gilmore Terrace\nEdinburgh\nEH3 9NN\nUnited Kingdom")
        self.date_from.setDate(QDate(2026, 5, 1))
        self.date_to.setDate(QDate(2026, 5, 31))
        self.issued_on.setDate(QDate(2026, 5, 31))
        self.creation_datetime.setDateTime(QDateTime(QDate(2026, 5, 31), self.creation_datetime.time()))

        self.opening_balance.setValue(488.41)

        default_txns = [
            ("16/05/2026", "Transfer to Savings Pot", -134.03),
            ("19/05/2026", "Transfer from Savings Pot", 71.70),
            ("21/05/2026", "Transfer from Savings Pot", 134.39),
            ("24/05/2026", "Transfer to Savings Pot", -139.72),
        ]
        for d, desc, amt in default_txns:
            self._add_row(d, desc, str(amt))
        self._recalculate()

    def _add_row(self, date="", desc="", amount=""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(date or "01/06/2026"))
        self.table.setItem(row, 1, QTableWidgetItem(desc or "Transfer"))
        self.table.setItem(row, 2, QTableWidgetItem(amount or "0.00"))
        self.table.scrollToBottom()

    def _delete_selected(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self._recalculate()

    def _move_up(self):
        row = self.table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self.table.selectRow(row - 1)

    def _move_down(self):
        row = self.table.currentRow()
        if row < self.table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self.table.selectRow(row + 1)

    def _swap_rows(self, r1, r2):
        for col in range(3):
            a = self.table.item(r1, col)
            b = self.table.item(r2, col)
            ta = a.text() if a else ""
            tb = b.text() if b else ""
            self.table.setItem(r1, col, QTableWidgetItem(tb))
            self.table.setItem(r2, col, QTableWidgetItem(ta))
        self._recalculate()

    def _recalculate(self):
        opening = self.opening_balance.value()
        balance = opening
        total_in = 0.0
        total_out = 0.0

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            try:
                amt = float(item.text()) if item else 0.0
            except ValueError:
                amt = 0.0
            balance += amt
            if amt >= 0:
                total_in += amt
            else:
                total_out += abs(amt)

        self.lbl_total_balance.setText(f"Total Balance (incl. pots): £{balance:.2f}")
        self.lbl_outgoings.setText(f"Total Outgoings: £{total_out:.2f}")
        self.lbl_incomes.setText(f"Total Incomes: £{total_in:.2f}")

    def _get_data(self):
        opening = self.opening_balance.value()
        balance = opening
        total_in = 0.0
        total_out = 0.0
        transactions = []

        for row in range(self.table.rowCount()):
            date_item = self.table.item(row, 0)
            desc_item = self.table.item(row, 1)
            amt_item = self.table.item(row, 2)
            date_str = date_item.text() if date_item else ""
            desc_str = desc_item.text() if desc_item else ""
            try:
                amt = float(amt_item.text()) if amt_item else 0.0
            except ValueError:
                amt = 0.0
            balance += amt
            if amt >= 0:
                total_in += amt
            else:
                total_out += abs(amt)
            transactions.append({"date": date_str, "description": desc_str,
                                  "amount": amt, "balance": round(balance, 2)})

        def fmt_date_numeric(qd: QDate):
            # DD/MM/YYYY for the statement date range header
            d = qd.toPyDate()
            return d.strftime("%d/%m/%Y")

        def fmt_date_text(qd: QDate):
            # "Jul 31, 2026" for "Issued on:" line
            d = qd.toPyDate()
            return d.strftime("%b ") + str(d.day) + d.strftime(", %Y")

        address = self.address_edit.toPlainText().strip()

        return {
            "name": self.name_edit.text().strip() or "UNKNOWN",
            "address": address,
            "date_from": fmt_date_numeric(self.date_from.date()),
            "date_to": fmt_date_numeric(self.date_to.date()),
            "issued_on": fmt_date_text(self.issued_on.date()),
            "total_balance": round(balance, 2),
            "total_outgoings": round(total_out, 2),
            "total_incomes": round(total_in, 2),
            "transactions": transactions,
            "creation_datetime": self.creation_datetime.dateTime().toPyDateTime(),
        }

    def _generate(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "No Transactions", "Please add at least one transaction.")
            return

        # Default save location: user's Desktop (works on Windows/Linux/macOS)
        import pathlib
        default_dir = str(pathlib.Path.home() / "Desktop")
        default_path = os.path.join(default_dir, "Monzo_Statement.pdf")

        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", default_path, "PDF Files (*.pdf)"
        )
        if not path:
            return

        try:
            data = self._get_data()
            generate_pdf(data, path)
            QMessageBox.information(self, "Success",
                                    f"Statement saved to:\n{path}")
        except PermissionError:
            QMessageBox.critical(self, "Permission Denied",
                                 f"Cannot write to:\n{path}\n\n"
                                 f"Please choose a different location (e.g. Desktop or Documents).")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{e}")
            raise


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MonzoGenerator()
    win.show()
    sys.exit(app.exec())