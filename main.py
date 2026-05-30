"""
Yonder 账单生成器 - PyQt5 UI
pip install PyQt5 reportlab pypdf

Claude AI 2025-09-08，仅供学习使用，请勿用于非法用途！富强、民主、文明、和谐、自由、平等、公正、法治、爱国、敬业、诚信、友善！
"""

import sys
import os
from datetime import datetime
from pypdf import PdfWriter, PdfReader

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QDoubleSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QFileDialog, QMessageBox, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yonder_logo.png")

# ── 颜色 ──────────────────────────────────────
ORANGE   = HexColor("#E8A020")
RED      = HexColor("#C0392B")
BLACK    = HexColor("#1A1A1A")
GREY     = HexColor("#888888")
LTGREY   = HexColor("#F5F5F5")
MDGREY   = HexColor("#CCCCCC")
GREEN    = HexColor("#27AE60")
OFFWHITE = HexColor("#FAFAFA")


# ── PDF 生成核心 ──────────────────────────────

def generate_statement(cfg, output_path):
    W, H = 612, 792
    tmp_path = output_path + ".tmp.pdf"
    cv = canvas.Canvas(tmp_path, pagesize=(W, H))
    cv.setTitle(f"Yonder Statement - {cfg['statement_month']}")

    try:
        created = datetime.strptime(cfg.get("created_at", ""), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        created = datetime.now()

    total_bill = cfg["total_spent"]
    early_pay  = cfg["early_payments_refunds"]
    total_due  = total_bill - early_pay
    min_pay    = round(total_due * 0.10, 2)

    def Y(top): return H - top

    # Logo
    logo_path = cfg.get("logo_path", LOGO_PATH)
    if logo_path and os.path.exists(logo_path):
        logo_h = 28
        logo_w = logo_h * (1780 / 480)
        cv.drawImage(logo_path, 66, Y(90), width=logo_w, height=logo_h, mask="auto")
    else:
        cv.setFont("Helvetica-Bold", 16)
        cv.setFillColor(BLACK)
        cv.drawString(66, Y(85), "yonder")

    # Statement Month 右上
    cv.setFont("Helvetica-Bold", 12)
    cv.setFillColor(BLACK)
    cv.drawRightString(546, Y(71.5 + 12), cfg["statement_month"])

    # 持卡人地址
    cv.setFont("Helvetica-Bold", 9)
    cv.setFillColor(BLACK)
    cv.drawString(66, Y(121.9 + 9), cfg["name"])
    cv.setFont("Helvetica", 9)
    for i, ln in enumerate([cfg["address_line1"], cfg["address_line2"],
                             cfg["address_line3"], cfg["address_line4"]]):
        cv.drawString(66, Y(132.9 + i * 11 + 9), ln)

    # 右侧元数据
    meta = [
        ("Statement Period:",   cfg["statement_period"],   103.9),
        ("Member since:",       cfg["member_since"],       121.7),
        ("Membership number:",  cfg["membership_number"],  135.7),
        ("Card number ending:", cfg["card_number_ending"], 149.7),
        ("Credit limit:",       cfg["credit_limit"],       163.7),
    ]
    for label, value, top in meta:
        rl_y = Y(top + 8)
        cv.setFont("Helvetica-Bold", 8)
        cv.setFillColor(BLACK)
        cv.drawString(361, rl_y, label)
        cv.setFont("Helvetica", 8)
        cv.drawRightString(546, rl_y, value)

    # 圆角汇总框
    cv.setStrokeColor(MDGREY)
    cv.setLineWidth(0.7)
    cv.setFillColor(colors.white)
    cv.roundRect(57, Y(470), 498, 274, 8, fill=1, stroke=1)

    # Total Bill
    cv.setFont("Helvetica", 10)
    cv.setFillColor(GREY)
    cv.drawCentredString(306, Y(215.1 + 10), "Total Bill")

    cv.setFont("Helvetica-Bold", 18)
    cv.setFillColor(BLACK)
    cv.drawCentredString(306, Y(234.8 + 18), f"€ {total_bill:,.2f}")

    cv.setFont("Helvetica", 8)
    cv.setFillColor(GREY)
    cv.drawCentredString(306, Y(260.7 + 8),
        f"Don't forget to pay at least € {total_due:,.2f} by {cfg['due_day']}")

    # 分隔线
    cv.setStrokeColor(MDGREY)
    cv.setLineWidth(0.5)
    cv.line(66, Y(275), 546, Y(275))

    # The breakdown
    cv.setFont("Helvetica", 10)
    cv.setFillColor(GREY)
    cv.drawCentredString(306, Y(297.6 + 10), "The breakdown")

    parts = cfg["statement_period"].split(" - ")
    period_str = f"{parts[0].strip()} - {parts[1].strip()}"

    # Spent between
    cv.setFont("Helvetica", 9)
    cv.setFillColor(BLACK)
    cv.drawString(81, Y(318.4 + 9), f"Spent between {period_str}")
    cv.drawRightString(506, Y(318.4 + 9), f"€ {total_bill:,.2f}")

    cv.setFont("Helvetica", 7)
    cv.setFillColor(GREY)
    cv.drawString(81, Y(336.0 + 7), "(Includes interest charge of € 0.00*)")

    # Early payments
    cv.setFont("Helvetica", 9)
    cv.setFillColor(BLACK)
    cv.drawString(81, Y(354.4 + 9), f"Early payments and refunds between {period_str}")
    cv.setFillColor(GREEN)
    cv.drawRightString(506, Y(354.4 + 9), f"+ € {early_pay:,.2f}")

    # 分隔线
    cv.setStrokeColor(MDGREY)
    cv.setLineWidth(0.5)
    cv.line(66, Y(372), 546, Y(372))

    # Total Bill for month
    cv.setFont("Helvetica-Bold", 12)
    cv.setFillColor(BLACK)
    cv.drawString(81, Y(397.5 + 12), f"Total Bill for {cfg['statement_month']}")
    cv.drawRightString(506, Y(397.5 + 12), f"€ {total_due:,.2f}")

    cv.setFont("Helvetica", 7)
    cv.setFillColor(GREY)
    cv.drawString(81, Y(414.5 + 7), "Balance at 08 September 2025")

    # Minimum payment
    cv.setFont("Helvetica", 9)
    cv.setFillColor(BLACK)
    cv.drawString(81, Y(432.9 + 9), f"Minimum payment (due by {cfg['due_day']})")
    cv.drawRightString(506, Y(432.9 + 9), f"€ {min_pay:,.2f}")

    cv.setFont("Helvetica", 7)
    cv.setFillColor(GREY)
    cv.drawString(81, Y(450.5 + 7),
        "You'll pay € 0.00 in interest in your next bill if you only make the minimum repayment")

    # Transactions 标题
    cv.setFont("Helvetica-Bold", 12)
    cv.setFillColor(BLACK)
    cv.drawCentredString(306, Y(517.5 + 12), "Transactions")
    cv.setStrokeColor(ORANGE)
    cv.setLineWidth(2)
    cv.line(291, Y(535), 321, Y(535))

    # 表头
    cv.setFillColor(LTGREY)
    cv.rect(57, Y(569), 498, 20, fill=1, stroke=0)
    cv.setFont("Helvetica-Bold", 8)
    cv.setFillColor(BLACK)
    cv.drawString(66,    Y(559.2 + 8), "Date")
    cv.drawString(139.8, Y(559.2 + 8), "Description")
    cv.drawString(336.6, Y(559.2 + 8), "Location")
    cv.drawRightString(546, Y(559.2 + 8), "Amount (€ )")
    cv.setStrokeColor(MDGREY)
    cv.setLineWidth(0.5)
    cv.line(57, Y(569), 555, Y(569))

    # 交易行
    row_tops = [577.2, 595.2, 613.2, 631.2, 649.2, 667.2, 685.2]
    for idx, (date, desc, loc, amt) in enumerate(cfg["transactions"]):
        if idx < len(row_tops):
            top = row_tops[idx]
        else:
            top = row_tops[-1] + (idx - len(row_tops) + 1) * 18
        cv.setFillColor(colors.white if idx % 2 == 0 else OFFWHITE)
        cv.rect(57, Y(top + 18), 498, 18, fill=1, stroke=0)
        text_y = Y(top + 8)
        cv.setFont("Helvetica", 8)
        cv.setFillColor(BLACK)
        cv.drawString(66,    text_y, date)
        cv.drawString(139.8, text_y, desc)
        cv.drawString(336.6, text_y, loc)
        cv.setFillColor(RED)
        cv.drawRightString(546, text_y, f"{amt:,.2f}")
        cv.setStrokeColor(HexColor("#EEEEEE"))
        cv.setLineWidth(0.3)
        cv.line(57, Y(top + 18), 555, Y(top + 18))

    # Total 行
    total_sum = sum(t[3] for t in cfg["transactions"])
    n = len(cfg["transactions"])
    last_top = row_tops[min(n - 1, len(row_tops) - 1)] if n <= len(row_tops) else row_tops[-1] + (n - len(row_tops)) * 18
    total_top = last_top + 18 + 2
    cv.setFont("Helvetica", 8)
    cv.setFillColor(BLACK)
    cv.drawString(336.6, Y(total_top + 8), "Total:")
    cv.drawRightString(546, Y(total_top + 8), f"{total_sum:,.2f}")

    # ══════════════════════════════════════════
    #  PAGE 2 — How to pay
    # ══════════════════════════════════════════
    cv.showPage()

    def Y2(top): return H - top

    cv.setFont("Helvetica-Bold", 14)
    cv.setFillColor(BLACK)
    cv.drawCentredString(306, Y2(80), "How to pay")

    cv.setStrokeColor(ORANGE)
    cv.setLineWidth(2)
    cv.line(276, Y2(92), 336, Y2(92))

    card_y_top = 110
    card_h     = 130
    card_gap   = 20
    card_w     = 210
    left_x     = 66
    right_x    = 66 + card_w + card_gap

    for cx in (left_x, right_x):
        cv.setStrokeColor(MDGREY)
        cv.setLineWidth(0.7)
        cv.setFillColor(colors.white)
        cv.roundRect(cx, Y2(card_y_top + card_h), card_w, card_h, 8, fill=1, stroke=1)

    ix, iy = left_x + card_w / 2, Y2(card_y_top + 38)
    cv.setStrokeColor(BLACK)
    cv.setFillColor(BLACK)
    cv.setLineWidth(1)
    cv.rect(ix - 12, iy - 8, 24, 14, fill=0, stroke=1)
    cv.rect(ix - 8,  iy - 8, 5,  9,  fill=0, stroke=1)
    cv.rect(ix - 1,  iy - 8, 5,  9,  fill=0, stroke=1)
    cv.rect(ix + 6,  iy - 8, 5,  9,  fill=0, stroke=1)
    cv.line(ix - 14, iy + 6, ix + 14, iy + 6)
    cv.line(ix - 14, iy + 9, ix + 14, iy + 9)

    cv.setFont("Helvetica-Bold", 9)
    cv.setFillColor(BLACK)
    cv.drawCentredString(left_x + card_w / 2, Y2(card_y_top + 58), "Bank transfer in-app")

    cv.setFont("Helvetica", 7.5)
    cv.setFillColor(GREY)
    for i, txt in enumerate([
        "Login to your Yonder App and you can securely make",
        "a payment via your banking app using Open Banking",
        "payments.",
    ]):
        cv.drawCentredString(left_x + card_w / 2, Y2(card_y_top + 74 + i * 10), txt)

    dx, dy = right_x + card_w / 2, Y2(card_y_top + 38)
    cv.setStrokeColor(BLACK)
    cv.setLineWidth(1.5)
    cv.setFillColor(colors.white)
    cv.circle(dx, dy, 10, fill=0, stroke=1)
    cv.setFont("Helvetica-Bold", 11)
    cv.setFillColor(BLACK)
    cv.drawCentredString(dx, dy - 4, "D")

    cv.setFont("Helvetica-Bold", 9)
    cv.drawCentredString(right_x + card_w / 2, Y2(card_y_top + 58), "Direct Debit")

    cv.setFont("Helvetica", 7.5)
    cv.setFillColor(GREY)
    for i, txt in enumerate([
        "Set-up direct debit within your Yonder App and never",
        "worry about forgetting to make a payment.",
    ]):
        cv.drawCentredString(right_x + card_w / 2, Y2(card_y_top + 74 + i * 10), txt)

    cv.setFont("Helvetica", 6.5)
    cv.setFillColor(GREY)
    for i, txt in enumerate([
        "*The rate, or each rate, of interest which has been used to calculate the amount of interest included in this statement will be provided by",
        "you on request, together with a clear explanation of how that amount of interest has been calculated.",
        "",
        "Yonder is a trading name of Yonder Technology Ltd, company number 12739942, authorised and regulated by the Financial Conduct",
        "Authority (FCA) under firm reference 946219.",
    ]):
        cv.drawCentredString(306, Y2(680 + i * 10), txt)

    cv.save()

    # ── 用 pypdf 写入元数据（包括创建时间）──
    ts = created.strftime("D:%Y%m%d%H%M%S+00'00'")
    reader = PdfReader(tmp_path)
    writer = PdfWriter()
    writer.append(reader)
    writer.add_metadata({
        "/Title":        f"Yonder Statement - {cfg['statement_month']}",
        "/Author":       "Yonder Technology Ltd",
        "/Creator":      "Yonder App",
        "/Producer":     "Yonder App",
        "/CreationDate": ts,
        "/ModDate":      ts,
    })
    with open(output_path, "wb") as f:
        writer.write(f)
    os.remove(tmp_path)


# ── PyQt5 UI ──────────────────────────────────

def labeled(text, widget):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(2)
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #666; font-size: 11px;")
    v.addWidget(lbl)
    v.addWidget(widget)
    return w

def line(default=""):
    return QLineEdit(default)

def spin(default=0.0):
    s = QDoubleSpinBox()
    s.setRange(0, 9_999_999)
    s.setDecimals(2)
    s.setValue(default)
    s.setPrefix("€ ")
    return s


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yonder 账单生成器")
        self.setMinimumWidth(820)
        self.resize(900, 800)

        # ── 顶部标题 ──────────────────────────
        title_bar = QLabel("仅供学习使用，作者：Claude AI，反正跟我没什么关系 😜")
        title_bar.setAlignment(Qt.AlignCenter)
        title_bar.setStyleSheet(
            "background:#1a1a1a; color:white; font-size:13px; padding:8px 0;"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(title_bar)
        wrapper_layout.addWidget(scroll)
        self.setCentralWidget(wrapper)

        container = QWidget()
        scroll.setWidget(container)
        root = QVBoxLayout(container)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        # ── 持卡人信息 ─────────────────────────
        grp1 = QGroupBox("持卡人信息")
        g1 = QGridLayout(grp1)
        self.f_name  = line("Max Mustermann")
        self.f_addr1 = line("Musterstraße 12")
        self.f_addr2 = line("Musterstadt")
        self.f_addr3 = line("12345")
        self.f_addr4 = line("Germany")
        g1.addWidget(labeled("姓名",           self.f_name),  0, 0, 1, 2)
        g1.addWidget(labeled("地址行 1",        self.f_addr1), 1, 0)
        g1.addWidget(labeled("地址行 2（城市）", self.f_addr2), 1, 1)
        g1.addWidget(labeled("地址行 3（邮编）", self.f_addr3), 2, 0)
        g1.addWidget(labeled("地址行 4（国家）", self.f_addr4), 2, 1)
        root.addWidget(grp1)

        # ── 账单元数据 ─────────────────────────
        grp2 = QGroupBox("账单元数据")
        g2 = QGridLayout(grp2)
        self.f_month   = line("September 2025")
        self.f_period  = line("09 Mar 2026 - 08 Apr 2026")
        self.f_since   = line("September 2024")
        self.f_memno   = line("YOND-10195")
        self.f_cardno  = line("4223")
        self.f_limit   = line("€ 9600.00")
        self.f_created = line("2025-09-08 14:30:00")
        g2.addWidget(labeled("账单月份标题",       self.f_month),   0, 0)
        g2.addWidget(labeled("Statement Period",   self.f_period),  0, 1)
        g2.addWidget(labeled("Member since",       self.f_since),   1, 0)
        g2.addWidget(labeled("Membership number",  self.f_memno),   1, 1)
        g2.addWidget(labeled("Card number ending", self.f_cardno),  2, 0)
        g2.addWidget(labeled("Credit limit",       self.f_limit),   2, 1)
        g2.addWidget(labeled("PDF创建时间（格式：2025-09-08 14:30:00）", self.f_created), 3, 0, 1, 2)
        root.addWidget(grp2)

        # ── 账单金额 ───────────────────────────
        grp3 = QGroupBox("账单金额")
        g3 = QGridLayout(grp3)
        self.lbl_spent = QLabel("€ 0.00")
        self.lbl_spent.setStyleSheet(
            "background:#f0f0f0; border:1px solid #ccc; border-radius:3px;"
            "padding:4px 8px; font-size:13px;"
        )
        self.f_refund = spin(2524.28)
        self.f_due    = line("22 September")
        self.lbl_calc = QLabel()
        self.lbl_calc.setStyleSheet("color:#555; font-size:12px; padding:4px 0;")
        self.f_refund.valueChanged.connect(self.update_calc)
        g3.addWidget(labeled("本期消费总额（自动汇总）", self.lbl_spent), 0, 0)
        g3.addWidget(labeled("提前还款 / 退款",          self.f_refund), 0, 1)
        g3.addWidget(labeled("还款到期日",               self.f_due),    0, 2)
        g3.addWidget(self.lbl_calc, 1, 0, 1, 3)
        root.addWidget(grp3)

        # ── 交易明细 ───────────────────────────
        grp4 = QGroupBox("交易明细")
        g4 = QVBoxLayout(grp4)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["日期", "描述", "地点", "金额 (€)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().resizeSection(0, 100)
        self.table.horizontalHeader().resizeSection(2, 110)
        self.table.horizontalHeader().resizeSection(3, 90)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setMinimumHeight(220)
        self.table.itemChanged.connect(self.update_calc)

        default_txns = [
            ("03/09/2025", "Ruppersberger",                         "Kyritz",      "929.34"),
            ("05/09/2025", "DB Vertrieb GmbH",                      "Oranienburg", "472.58"),
            ("07/09/2025", "Zimmer",                                "Günzburg",    "488.96"),
            ("10/08/2025", "Weiß GbR",                             "Hammelburg",  "518.64"),
            ("18/08/2025", "Freudenberger Rudolph GmbH & Co. KGaA", "Dessau",      "79.49"),
            ("20/08/2025", "Heydrich",                              "Hünfeld",     "849.28"),
            ("31/08/2025", "Google Germany GmbH",                   "Weinheim",    "434.54"),
        ]
        for row in default_txns:
            self.add_row(*row)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("＋ 添加行")
        btn_del = QPushButton("－ 删除选中行")
        btn_add.clicked.connect(lambda: self.add_row())
        btn_del.clicked.connect(self.del_row)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()

        g4.addWidget(self.table)
        g4.addLayout(btn_row)
        root.addWidget(grp4)

        # ── 输出路径 + 生成按钮 ────────────────
        bot = QHBoxLayout()
        self.f_outpath = QLineEdit(os.path.expanduser("~/yonder_statement.pdf"))
        self.f_outpath.setPlaceholderText("输出 PDF 路径…")
        btn_browse = QPushButton("浏览…")
        btn_browse.clicked.connect(self.browse)
        btn_gen = QPushButton("生成 PDF")
        btn_gen.setFixedHeight(36)
        btn_gen.setStyleSheet(
            "QPushButton{background:#1a1a1a;color:white;border-radius:6px;font-size:14px;font-weight:bold;}"
            "QPushButton:hover{background:#333;}"
        )
        btn_gen.clicked.connect(self.generate)
        bot.addWidget(self.f_outpath, 1)
        bot.addWidget(btn_browse)
        bot.addWidget(btn_gen)
        root.addLayout(bot)

        root.addStretch()
        self.update_calc()

    # ── 辅助 ──────────────────────────────────

    def txn_total(self):
        total = 0.0
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 3)
            if item:
                try:
                    total += float(item.text())
                except ValueError:
                    pass
        return total

    def update_calc(self):
        spent  = self.txn_total()
        self.lbl_spent.setText(f"€ {spent:,.2f}")
        refund = self.f_refund.value()
        total  = max(0, spent - refund)
        mn     = total * 0.10
        self.lbl_calc.setText(
            f"Total Bill: € {total:,.2f}    最低还款（10%）: € {mn:,.2f}"
        )

    def add_row(self, date="", desc="", loc="", amt=""):
        self.table.itemChanged.disconnect(self.update_calc)
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(date))
        self.table.setItem(r, 1, QTableWidgetItem(desc))
        self.table.setItem(r, 2, QTableWidgetItem(loc))
        self.table.setItem(r, 3, QTableWidgetItem(amt))
        self.table.itemChanged.connect(self.update_calc)
        self.update_calc()

    def del_row(self):
        rows = sorted({i.row() for i in self.table.selectedItems()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        self.update_calc()

    def browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF", self.f_outpath.text(), "PDF Files (*.pdf)"
        )
        if path:
            self.f_outpath.setText(path)

    def get_config(self):
        txns = []
        for r in range(self.table.rowCount()):
            def cell(c, _r=r):
                item = self.table.item(_r, c)
                return item.text() if item else ""
            try:
                amt = float(cell(3))
            except ValueError:
                amt = 0.0
            txns.append((cell(0), cell(1), cell(2), amt))

        return {
            "name":                  self.f_name.text(),
            "address_line1":         self.f_addr1.text(),
            "address_line2":         self.f_addr2.text(),
            "address_line3":         self.f_addr3.text(),
            "address_line4":         self.f_addr4.text(),
            "statement_month":       self.f_month.text(),
            "statement_period":      self.f_period.text(),
            "member_since":          self.f_since.text(),
            "membership_number":     self.f_memno.text(),
            "card_number_ending":    self.f_cardno.text(),
            "credit_limit":          self.f_limit.text(),
            "created_at":            self.f_created.text(),
            "total_spent":           self.txn_total(),
            "early_payments_refunds":self.f_refund.value(),
            "due_day":               self.f_due.text(),
            "transactions":          txns,
        }

    def generate(self):
        cfg  = self.get_config()
        path = self.f_outpath.text().strip()
        if not path:
            QMessageBox.warning(self, "错误", "请指定输出路径")
            return
        try:
            generate_statement(cfg, path)
            QMessageBox.information(self, "完成", f"PDF 已生成：\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "生成失败", str(e))


# ── 入口 ──────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())