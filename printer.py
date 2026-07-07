import os
import platform
import subprocess

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from settings import get_company, get_db_setting
from billing import get_sale_bill, get_entries_for_consolidated_bill
from receipt import get_receipt
from reports import get_customer_statement
from database import get_connection

NAVY = colors.HexColor("#1a237e")
LIGHT_NAVY = colors.HexColor("#e8eaf6")
GREY = colors.HexColor("#757575")
LIGHT_GREY = colors.HexColor("#f5f5f5")
BORDER = colors.HexColor("#cccccc")
WHITE = colors.white
BLACK = colors.black

MARGIN_LR = 12*mm
MARGIN_TOP = 8*mm
MARGIN_BOTTOM = 10*mm
USABLE_WIDTH = A4[0] - 2*MARGIN_LR
HALF_WIDTH = USABLE_WIDTH / 2

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_output")


def _find_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.otf",
        os.path.expandvars(r"%WINDIR%\Fonts\Arial.ttf"),
        os.path.expandvars(r"%WINDIR%\Fonts\Calibri.ttf"),
        os.path.expandvars(r"%WINDIR%\Fonts\segoeui.ttf"),
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        os.path.join(ASSETS_DIR, "DejaVuSans.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _download_dejavu() -> str:
    bundled = os.path.join(ASSETS_DIR, "DejaVuSans.ttf")
    if os.path.exists(bundled):
        return bundled
    url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
    try:
        os.makedirs(ASSETS_DIR, exist_ok=True)
        print(f"[printer] Downloading DejaVuSans ...")
        from urllib.request import urlopen
        with urlopen(url, timeout=30) as resp:
            data = resp.read()
        with open(bundled, "wb") as f:
            f.write(data)
        return bundled
    except Exception as e:
        print(f"[printer] Font download failed: {e}")
        return ""


def _try_register_font() -> str:
    path = _find_font()
    if not path:
        path = _download_dejavu()
    if path:
        try:
            pdfmetrics.registerFont(TTFont("AppFont", path))
            return "AppFont"
        except Exception:
            pass
    return "Helvetica"


FONT_NAME = _try_register_font()


def _amount_in_words(amount: float) -> str:
    if amount == 0:
        return "Zero Rupees Only"

    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
             "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def _under_1000(n):
        res = ""
        if n >= 100:
            res += units[n // 100] + " Hundred "
            n %= 100
        if 10 < n < 20:
            res += teens[n - 10] + " "
        else:
            if n >= 20:
                res += tens[n // 10] + " "
                n %= 10
            if n > 0:
                res += units[n] + " "
        return res.strip()

    amt = int(round(amount))
    if amt >= 10000000:
        return "Very Large Amount"

    words = ""
    if amt >= 100000:
        lakhs = amt // 100000
        words += _under_1000(lakhs) + " Lakh "
        amt %= 100000
    if amt >= 1000:
        thousands = amt // 1000
        words += _under_1000(thousands) + " Thousand "
        amt %= 1000
    if amt > 0:
        words += _under_1000(amt)

    return words.strip() + " Rupees Only"


def _header_block(company: dict) -> Table:
    USABLE = 186*mm
    rows = []

    rows.append([Paragraph(
        company.get("name", "").upper(),
        ParagraphStyle("H1", fontName=FONT_NAME, fontSize=16, alignment=TA_CENTER,
                        spaceBefore=4, spaceAfter=2, textColor=NAVY, leading=20),
    )])

    addr = company.get("address", "")
    if addr:
        rows.append([Paragraph(
            addr.replace("\n", "<br/>"),
            ParagraphStyle("H2", fontName=FONT_NAME, fontSize=8.5, alignment=TA_CENTER,
                            leading=12, textColor=BLACK),
        )])

    rows.append([HRFlowable(width="60%", thickness=0.5, color=NAVY, spaceAfter=2, spaceBefore=2)])

    reg_parts = []
    if company.get("phone"):
        reg_parts.append(f"Phone: {company['phone']}")
    if company.get("email"):
        reg_parts.append(f"Email: {company['email']}")
    if reg_parts:
        rows.append([Paragraph(
            " | ".join(reg_parts),
            ParagraphStyle("Reg", fontName=FONT_NAME, fontSize=7.5, alignment=TA_CENTER,
                            textColor=GREY, leading=10),
        )])

    tbl = Table(rows, colWidths=[USABLE])
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _title_band(text: str) -> Table:
    band = Table(
        [[Paragraph(text, ParagraphStyle(
            "Band", fontName=FONT_NAME, fontSize=14, alignment=TA_CENTER,
            textColor=WHITE, spaceBefore=2, spaceAfter=2,
        ))]],
        colWidths=[USABLE_WIDTH],
    )
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return band


def _info_pair(label: str, value: str) -> list:
    return [
        Paragraph(f"<b>{label}</b>",
                  ParagraphStyle("IL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
        Paragraph(value,
                  ParagraphStyle("IV", fontName=FONT_NAME, fontSize=9, textColor=BLACK)),
    ]


def generate_bill_pdf(bill_id: int, output_path: str | None = None) -> str:
    bill = get_sale_bill(bill_id)
    if not bill:
        raise ValueError(f"Sale bill {bill_id} not found")

    company = get_company()

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        safe_no = bill['bill_no'].replace("/", "_")
        output_path = os.path.join(PDF_DIR, f"bill_{safe_no}.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    elements = []

    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    elements.append(_title_band("SALE BILL"))
    elements.append(Spacer(1, 4*mm))

    left_rows = [
        _info_pair("Bill No", f"<b>{bill['bill_no']}</b>"),
        _info_pair("Date", f"<b>{bill['bill_date']}</b>"),
    ]
    if bill.get("vehicle_no"):
        left_rows.append(_info_pair("Vehicle No", f"<b>{bill['vehicle_no']}</b>"))
    left_tbl = Table(left_rows, colWidths=[32*mm, 56*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    cust_lines = [f"<b>{bill['customer_name']}</b>"]
    if bill.get("customer_mobile"):
        cust_lines.append(f"Mobile: {bill['customer_mobile']}")
    cust_text = "<br/>".join(cust_lines)

    right_rows = [
        [Paragraph("<b>Bill To</b>",
                   ParagraphStyle("BL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
         Paragraph(cust_text,
                   ParagraphStyle("BV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))],
    ]
    right_tbl = Table(right_rows, colWidths=[20*mm, 68*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    hdr = ["#", "Product", "Gross Wt", "Tare Wt", "Net Wt", "Rate", "Amount"]
    cw = [7*mm, 50*mm, 22*mm, 22*mm, 22*mm, 22*mm, 28*mm]

    data = [hdr]
    data.append([
        "1",
        bill.get("product_name", ""),
        f"{bill['gross_weight']:.2f}",
        f"{bill['tare_weight']:.2f}",
        f"{bill['net_weight']:.2f}",
        f"{bill['rate']:.2f}",
        f"{bill['amount']:.2f}",
    ])
    data.append(["", "", "", "", "", "", ""])
    data.append(["", "", "", "", "", "Total Amount", f"{bill['amount']:.2f}"])

    total_n = 2
    total_start = -total_n

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, total_start - 1), 0.3, BORDER),
        ("LINEABOVE", (0, total_start), (-1, total_start), 0.6, NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4*mm))

    words = bill.get("amount_in_words") or _amount_in_words(bill["amount"])
    aw_tbl = Table(
        [[Paragraph("<b>Amount in Words:</b>",
                     ParagraphStyle("AWL", fontName=FONT_NAME, fontSize=9, textColor=NAVY)),
          Paragraph(words,
                     ParagraphStyle("AWV", fontName=FONT_NAME, fontSize=9, textColor=NAVY, leading=13))]],
        colWidths=[30*mm, 132*mm],
    )
    aw_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(aw_tbl)
    elements.append(Spacer(1, 1*mm))

    bank_parts = []
    if company.get("bank_name"):
        bank_parts.append(f"Bank: {company['bank_name']}")
    if company.get("bank_account"):
        bank_parts.append(f"A/C: {company['bank_account']}")
    if company.get("bank_ifsc"):
        bank_parts.append(f"IFSC: {company['bank_ifsc']}")
    if bank_parts:
        bank_text = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(bank_parts)
        bk_tbl = Table(
            [[Paragraph("<b>Bank Details:</b>",
                         ParagraphStyle("BKL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(bank_text,
                         ParagraphStyle("BKV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[26*mm, 136*mm],
        )
        bk_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(bk_tbl)
        elements.append(Spacer(1, 0.5*mm))

    cname = company.get("name", "Ragumani Transport & Fire Woods Suppliers")
    terms_text = get_db_setting("terms",
        "1. All disputes subject to local jurisdiction.\n"
        "2. Payment due within 15 days from bill date.\n"
        "3. Goods once sold will not be taken back.")
    terms_html = terms_text.replace("\n", "<br/>")

    terms_tbl = Table(
        [[Paragraph("<b>Terms &amp; Conditions</b>",
                     ParagraphStyle("TL", fontName=FONT_NAME, fontSize=8, textColor=GREY)),
          Paragraph(terms_html,
                     ParagraphStyle("TV", fontName=FONT_NAME, fontSize=8, textColor=BLACK, leading=11))]],
        colWidths=[28*mm, 66*mm],
    )
    terms_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
    ]))

    sig_text = (
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[80*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    bottom = Table([[terms_tbl, sig_tbl]], colWidths=[94*mm, 92*mm])
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(bottom)
    elements.append(Spacer(1, 3*mm))

    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a computer-generated bill.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


def generate_consolidated_bill_pdf(
    customer_id: int, customer_name: str, date_from: str, date_to: str,
    output_path: str | None = None,
) -> str:
    company = get_company()
    entries = get_entries_for_consolidated_bill(customer_id, date_from, date_to)

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        safe_name = customer_name.replace(" ", "_")[:20]
        output_path = os.path.join(PDF_DIR, f"invoice_{safe_name}_{date_from}_{date_to}.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    elements = []

    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    elements.append(_title_band("CONSOLIDATED INVOICE"))
    elements.append(Spacer(1, 4*mm))

    left_rows = [
        _info_pair("Customer", f"<b>{customer_name}</b>"),
        _info_pair("Period", f"<b>{date_from}</b> to <b>{date_to}</b>"),
    ]
    left_tbl = Table(left_rows, colWidths=[28*mm, 60*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    total_entries = len(entries)
    total_net = sum(e["net_weight"] for e in entries)
    total_amount = sum(e["amount"] for e in entries)
    right_rows = [
        _info_pair("Total Entries", f"<b>{total_entries}</b>"),
        _info_pair("Total Net Wt", f"<b>{total_net:.2f} Kg</b>"),
    ]
    right_tbl = Table(right_rows, colWidths=[24*mm, 64*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    hdr = ["#", "Date", "Vehicle", "Gross", "Tare", "Net Wt", "Amount"]
    cw = [7*mm, 28*mm, 32*mm, 22*mm, 20*mm, 24*mm, 28*mm]

    data = [hdr]
    for i, e in enumerate(entries, 1):
        data.append([
            str(i),
            e["bill_date"],
            e.get("vehicle_no", ""),
            f"{e['gross_weight']:.2f}",
            f"{e['tare_weight']:.2f}",
            f"{e['net_weight']:.2f}",
            f"{e['amount']:.2f}",
        ])
    data.append(["", "", "", "", "", "", ""])
    data.append(["", "", "", "", "", "Total Amount", f"{total_amount:.2f}"])

    total_n = 2
    total_start = -total_n

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, total_start - 1), 0.3, BORDER),
        ("LINEABOVE", (0, total_start), (-1, total_start), 0.6, NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]
    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4*mm))

    words = _amount_in_words(total_amount)
    aw_tbl = Table(
        [[Paragraph("<b>Amount in Words:</b>",
                     ParagraphStyle("AWL", fontName=FONT_NAME, fontSize=9, textColor=NAVY)),
          Paragraph(words,
                     ParagraphStyle("AWV", fontName=FONT_NAME, fontSize=9, textColor=NAVY, leading=13))]],
        colWidths=[30*mm, 132*mm],
    )
    aw_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(aw_tbl)
    elements.append(Spacer(1, 1*mm))

    bank_parts = []
    if company.get("bank_name"):
        bank_parts.append(f"Bank: {company['bank_name']}")
    if company.get("bank_account"):
        bank_parts.append(f"A/C: {company['bank_account']}")
    if company.get("bank_ifsc"):
        bank_parts.append(f"IFSC: {company['bank_ifsc']}")
    if bank_parts:
        bank_text = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(bank_parts)
        bk_tbl = Table(
            [[Paragraph("<b>Bank Details:</b>",
                         ParagraphStyle("BKL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(bank_text,
                         ParagraphStyle("BKV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[26*mm, 136*mm],
        )
        bk_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(bk_tbl)
        elements.append(Spacer(1, 0.5*mm))

    cname = company.get("name", "Ragumani Transport & Fire Woods Suppliers")
    terms_text = get_db_setting("terms",
        "1. All disputes subject to local jurisdiction.\n"
        "2. Payment due within 15 days from bill date.\n"
        "3. Goods once sold will not be taken back.")
    terms_html = terms_text.replace("\n", "<br/>")

    terms_tbl = Table(
        [[Paragraph("<b>Terms &amp; Conditions</b>",
                     ParagraphStyle("TL", fontName=FONT_NAME, fontSize=8, textColor=GREY)),
          Paragraph(terms_html,
                     ParagraphStyle("TV", fontName=FONT_NAME, fontSize=8, textColor=BLACK, leading=11))]],
        colWidths=[28*mm, 66*mm],
    )
    terms_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
    ]))

    sig_text = (
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[80*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    bottom = Table([[terms_tbl, sig_tbl]], colWidths=[94*mm, 92*mm])
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(bottom)
    elements.append(Spacer(1, 3*mm))

    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a computer-generated invoice.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


def generate_statement_pdf(
    customer_id: int, customer_name: str, date_from: str, date_to: str,
    output_path: str | None = None,
) -> str:
    company = get_company()
    stmt = get_customer_statement(customer_id, customer_name, date_from, date_to)

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        safe_name = customer_name.replace(" ", "_")[:20]
        output_path = os.path.join(
            PDF_DIR, f"statement_{safe_name}_{date_from}_{date_to}.pdf"
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    elements = []

    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    elements.append(_title_band("CUSTOMER STATEMENT"))
    elements.append(Spacer(1, 4*mm))

    # Info block
    left_rows = [
        _info_pair("Customer", f"<b>{customer_name}</b>"),
        _info_pair("Period", f"<b>{date_from}</b> to <b>{date_to}</b>"),
        _info_pair(
            "Opening Balance",
            f"<b>{stmt['opening_balance']:,.2f}</b>",
        ),
    ]
    left_tbl = Table(left_rows, colWidths=[30*mm, 58*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    total_sale = sum(t['debit'] for t in stmt['transactions'])
    total_recv = sum(t['credit'] for t in stmt['transactions'])
    right_rows = [
        _info_pair("Total Sales", f"<b>{total_sale:,.2f}</b>"),
        _info_pair("Total Received", f"<b>{total_recv:,.2f}</b>"),
        _info_pair(
            "Closing Balance",
            f"<b>{stmt['closing_balance']:,.2f}</b>",
        ),
    ]
    right_tbl = Table(right_rows, colWidths=[26*mm, 62*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    # Transaction table
    hdr = ["Date", "Description", "Vehicle", "Net Wt", "Amount", "Received", "Balance"]
    cw = [22*mm, 34*mm, 24*mm, 20*mm, 24*mm, 24*mm, 24*mm]

    data = [hdr]

    # Opening balance row
    data.append([
        "",
        Paragraph("<b>Opening Balance</b>",
                   ParagraphStyle("OB", fontName=FONT_NAME, fontSize=8)),
        "", "", "", "",
        f"{stmt['opening_balance']:,.2f}",
    ])

    total_sale = 0
    total_recv = 0
    for t in stmt["transactions"]:
        if t["type"] == "Bill":
            desc = f"Sale - {t['ref_no']}"
            vehicle = t.get("vehicle_no", "")
            net_wt = f"{t.get('net_weight', 0):,.2f}"
            amount = f"{t['debit']:,.2f}"
            received = ""
            total_sale += t["debit"]
        else:
            desc = f"Payment - {t['ref_no']}"
            vehicle = ""
            net_wt = ""
            amount = ""
            received = f"{t['credit']:,.2f}"
            total_recv += t["credit"]
        data.append([
            t["tx_date"], desc, vehicle, net_wt, amount, received,
            f"{t['balance']:,.2f}",
        ])

    # Totals row
    data.append(["", "", "", "", "", "", ""])
    data.append([
        "",
        Paragraph("<b>Total</b>",
                   ParagraphStyle("TTL", fontName=FONT_NAME, fontSize=9)),
        "", "",
        f"{total_sale:,.2f}" if total_sale else "",
        f"{total_recv:,.2f}" if total_recv else "",
        "",
    ])

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, -3), 0.3, BORDER),
        ("LINEABOVE", (0, -2), (-1, -2), 0.6, NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_NAVY),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4*mm))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a computer-generated statement.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


def generate_receipt_pdf(receipt_id: int, output_path: str | None = None) -> str:
    rec = get_receipt(receipt_id)
    if not rec:
        raise ValueError(f"Receipt {receipt_id} not found")

    company = get_company()

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        output_path = os.path.join(
            PDF_DIR,
            f"receipt_{rec['receipt_no'].replace('/', '_')}.pdf",
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    elements = []

    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    elements.append(_title_band("PAYMENT RECEIPT"))
    elements.append(Spacer(1, 4*mm))

    left_rows = [
        _info_pair("Receipt No", f"<b>{rec['receipt_no']}</b>"),
        _info_pair("Date", f"<b>{rec['receipt_date']}</b>"),
        _info_pair("Against Bill", f"<b>{rec.get('bill_no') or 'N/A'}</b>"),
        _info_pair("Payment Mode", f"<b>{rec.get('mode', 'Cash')}</b>"),
    ]
    if rec.get("reference_no"):
        left_rows.append(_info_pair("Reference No", rec["reference_no"]))
    left_tbl = Table(left_rows, colWidths=[30*mm, 58*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    cust_lines = [f"<b>{rec['customer_name']}</b>"]
    if rec.get("customer_mobile"):
        cust_lines.append(f"Mobile: {rec['customer_mobile']}")
    cust_text = "<br/>".join(cust_lines)
    right_rows = [
        [Paragraph("<b>Received From</b>",
                    ParagraphStyle("BL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
         Paragraph(cust_text,
                    ParagraphStyle("BV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))],
    ]
    right_tbl = Table(right_rows, colWidths=[24*mm, 64*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    amt_label = Paragraph("<b>Amount Received</b>",
                          ParagraphStyle("AmtLabel", fontName=FONT_NAME, fontSize=12,
                                          alignment=TA_CENTER, textColor=NAVY))
    amt_band = Table([[amt_label]], colWidths=[100*mm])
    amt_band.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 1.5, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_NAVY),
    ]))
    amt_wrap = Table([[amt_band]], colWidths=[176*mm])
    amt_wrap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(amt_wrap)
    elements.append(Spacer(1, 2*mm))

    elements.append(Paragraph(
        f"₹ {rec['amount']:,.2f}",
        ParagraphStyle("BigAmt", fontName=FONT_NAME, fontSize=28,
                        alignment=TA_CENTER, textColor=NAVY, spaceBefore=2, spaceAfter=2),
    ))
    words = rec.get("amount_in_words") or _amount_in_words(rec["amount"])
    elements.append(Paragraph(
        f"<i>{words}</i>",
        ParagraphStyle("Words", fontName=FONT_NAME, fontSize=10,
                        alignment=TA_CENTER, textColor=GREY, spaceAfter=6*mm),
    ))

    if rec.get("notes"):
        nt = Table(
            [[Paragraph("<b>Notes:</b>",
                         ParagraphStyle("NL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(rec["notes"],
                         ParagraphStyle("NV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[24*mm, 138*mm],
        )
        nt.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(nt)
        elements.append(Spacer(1, 6*mm))

    cname = company.get("name", "Ragumani Transport & Fire Woods Suppliers")
    sig_text = (
        f"Thank you for your payment!<br/><br/><br/>"
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[90*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(sig_tbl)
    elements.append(Spacer(1, 4*mm))

    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a computer-generated receipt.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


def generate_blank_invoice_pdf(
    bill_no: str = "",
    bill_date: str = "",
    output_path: str | None = None,
) -> str:
    company = get_company()

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        safe_no = bill_no.replace("/", "_") if bill_no else "blank"
        output_path = os.path.join(PDF_DIR, f"blank_bill_{safe_no}.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    elements = []

    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    elements.append(_title_band("BLANK BILL  (Handwritten)"))
    elements.append(Spacer(1, 4*mm))

    left_rows = [
        _info_pair("Bill No",
                   f"<b>{bill_no}</b>  ____________________" if bill_no
                   else "____________________"),
        _info_pair("Date",
                   f"<b>{bill_date}</b>  ____________________" if bill_date
                   else "____________________"),
        _info_pair("Vehicle No", "____________________"),
    ]
    left_tbl = Table(left_rows, colWidths=[32*mm, 56*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    blank_cust = ("Name: _____________________________<br/>"
                  "Mobile: ___________________________")
    right_rows = [
        [Paragraph("<b>Bill To</b>",
                   ParagraphStyle("BL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
         Paragraph(blank_cust,
                   ParagraphStyle("BV", fontName=FONT_NAME, fontSize=9, textColor=BLACK, leading=16))],
    ]
    right_tbl = Table(right_rows, colWidths=[20*mm, 68*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    hdr = ["#", "Product", "Gross Wt", "Tare Wt", "Net Wt", "Rate", "Amount"]
    cw = [7*mm, 50*mm, 22*mm, 22*mm, 22*mm, 22*mm, 28*mm]

    data = [hdr]
    for i in range(1, 6):
        data.append([str(i), "", "", "", "", "", ""])

    data.append(["", "", "", "", "", "", ""])
    data.append(["", "", "", "", "", "Total Amount", "__________"])

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, -7), 0.3, BORDER),
        ("LINEABOVE", (0, -2), (-1, -2), 0.6, NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4*mm))

    aw_tbl = Table(
        [[Paragraph("<b>Amount in Words:</b>",
                     ParagraphStyle("AWL", fontName=FONT_NAME, fontSize=9, textColor=NAVY)),
          Paragraph("_______________________________________________________",
                     ParagraphStyle("AWV", fontName=FONT_NAME, fontSize=9, textColor=NAVY, leading=13))]],
        colWidths=[30*mm, 132*mm],
    )
    aw_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(aw_tbl)
    elements.append(Spacer(1, 1*mm))

    bank_parts = []
    if company.get("bank_name"):
        bank_parts.append(f"Bank: {company['bank_name']}")
    if company.get("bank_account"):
        bank_parts.append(f"A/C: {company['bank_account']}")
    if company.get("bank_ifsc"):
        bank_parts.append(f"IFSC: {company['bank_ifsc']}")
    if bank_parts:
        bank_text = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(bank_parts)
        bk_tbl = Table(
            [[Paragraph("<b>Bank Details:</b>",
                         ParagraphStyle("BKL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(bank_text,
                         ParagraphStyle("BKV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[26*mm, 136*mm],
        )
        bk_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(bk_tbl)
        elements.append(Spacer(1, 0.5*mm))

    cname = company.get("name", "Ragumani Transport & Fire Woods Suppliers")
    terms_text = get_db_setting("terms",
        "1. All disputes subject to local jurisdiction.\n"
        "2. Payment due within 15 days from bill date.\n"
        "3. Goods once sold will not be taken back.")
    terms_html = terms_text.replace("\n", "<br/>")

    terms_tbl = Table(
        [[Paragraph("<b>Terms &amp; Conditions</b>",
                     ParagraphStyle("TL", fontName=FONT_NAME, fontSize=8, textColor=GREY)),
          Paragraph(terms_html,
                     ParagraphStyle("TV", fontName=FONT_NAME, fontSize=8, textColor=BLACK, leading=11))]],
        colWidths=[28*mm, 66*mm],
    )
    terms_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
    ]))

    sig_text = (
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[80*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    bottom = Table([[terms_tbl, sig_tbl]], colWidths=[94*mm, 92*mm])
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(bottom)
    elements.append(Spacer(1, 3*mm))

    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a blank bill form for handwritten use.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


def open_pdf(filepath: str):
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
    except Exception as e:
        print(f"[printer] Could not open PDF: {e}")
