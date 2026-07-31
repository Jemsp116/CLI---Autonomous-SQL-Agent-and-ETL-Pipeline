from __future__ import annotations

import random
import zipfile
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pdfplumber
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from invoice_agent.config import get_settings


styles = getSampleStyleSheet()


def mk(name, **kw):
	return ParagraphStyle(name, parent=styles["Normal"], **kw)


s_title = mk("T", fontSize=13, fontName="Helvetica-Bold", spaceAfter=2)
s_norm = mk("N", fontSize=9, leading=13)
s_bold = mk("NB", fontSize=9, fontName="Helvetica-Bold", leading=13)
s_sec = mk("S", fontSize=10, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=4)
s_th = mk("TH", fontSize=8, fontName="Helvetica-Bold", alignment=TA_LEFT, leading=10)
s_th_r = mk("THR", fontSize=8, fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=10)
s_td = mk("TD", fontSize=8, fontName="Helvetica", alignment=TA_LEFT, leading=11)
s_td_r = mk("TDR", fontSize=8, fontName="Helvetica", alignment=TA_RIGHT, leading=11)
s_td_b = mk("TDB", fontSize=8, fontName="Helvetica-Bold", alignment=TA_LEFT, leading=11)
s_td_br = mk("TDBR", fontSize=8, fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=11)

MARGIN = 20 * mm
USABLE = A4[0] - 2 * MARGIN
COL_W = [10 * mm, 55 * mm, 13 * mm, 12 * mm, 20 * mm, 20 * mm, 12 * mm, 18 * mm]
SUM_W = [58 * mm, 20 * mm, 30 * mm, 22 * mm, 30 * mm]
BORDER = colors.HexColor("#cccccc")
GREY_BG = colors.HexColor("#f5f5f5")
ALT_BG = colors.HexColor("#fafafa")

PRODUCTS = [
	("Apple iPhone 15 128GB Black", 55000, 85000),
	("Apple iPhone 15 Pro 256GB Titanium", 110000, 145000),
	("Samsung Galaxy S24 256GB Phantom Black", 65000, 90000),
	("OnePlus 12 256GB Silky Black", 55000, 70000),
	("Xiaomi 14 Pro 512GB White", 70000, 90000),
	("Realme GT 5 Pro 256GB Navigator Beige", 35000, 50000),
	("Vivo X100 Pro 256GB Asteroid Black", 75000, 95000),
	("Sony WH-1000XM5 Wireless Headphones", 25000, 35000),
	("Apple AirPods Pro 2nd Gen USB-C", 20000, 28000),
	("Samsung Galaxy Buds2 Pro Graphite", 10000, 16000),
	("Boat Rockerz 550 Bluetooth Headphones", 1500, 3500),
	("JBL Flip 6 Portable Bluetooth Speaker", 8000, 12000),
	("Sony Bravia 55 inch 4K OLED TV", 100000, 140000),
	("LG 43 inch 4K UHD Smart WebOS TV", 35000, 55000),
	("Samsung 65 inch QLED 4K Smart TV", 110000, 150000),
	("Apple MacBook Air M2 8GB 256GB Silver", 95000, 115000),
	("Dell XPS 13 Intel i7 16GB 512GB", 95000, 120000),
	("HP Pavilion 15 Ryzen 5 8GB 512GB", 55000, 75000),
	("Lenovo IdeaPad Slim 5 i5 16GB 512GB", 60000, 80000),
	("Asus VivoBook 16 Ryzen 7 16GB 512GB", 65000, 85000),
	("Apple iPad Air M1 64GB WiFi Space Grey", 55000, 70000),
	("Samsung Galaxy Tab S9 256GB Graphite", 65000, 85000),
	("Lenovo Tab P12 Pro 256GB Storm Grey", 35000, 50000),
	("Apple Watch Series 9 GPS 45mm Midnight", 40000, 55000),
	("Samsung Galaxy Watch6 Classic 47mm", 25000, 35000),
	("Garmin Fenix 7 Solar Multisport GPS", 65000, 85000),
	("Canon EOS R50 Mirrorless Camera Body", 60000, 80000),
	("Sony Alpha ZV-E10 Mirrorless Kit 16-50", 55000, 72000),
	("GoPro Hero 12 Black Action Camera", 35000, 45000),
	("DJI Mini 3 Pro Fly More Combo Drone", 90000, 120000),
	("Logitech MX Master 3S Wireless Mouse", 8000, 12000),
	("Keychron K8 Pro Mechanical Keyboard", 10000, 15000),
	("Dell 27 inch 4K USB-C IPS Monitor", 40000, 58000),
	("LG UltraGear 27 inch 165Hz Gaming Monitor", 28000, 40000),
	("Western Digital 2TB My Passport HDD", 5000, 8000),
	("Samsung T7 Shield 1TB Portable SSD", 8000, 12000),
	("Anker 65W GaN USB-C 3-Port Charger", 2500, 4500),
	("Belkin MagSafe 3-in-1 Wireless Charger", 6000, 10000),
	("TP-Link Archer AX73 WiFi 6 Router", 12000, 18000),
	("Philips Hue White Ambiance Starter Kit", 5000, 9000),
]

CLIENTS = [
	("Raj Electronics Pvt Ltd", "42 MG Road", "Bengaluru", "Karnataka", "560001"),
	("Sharma Tech Solutions", "15 Connaught Place", "New Delhi", "Delhi", "110001"),
	("Mumbai Gadget House", "78 Linking Road", "Mumbai", "Maharashtra", "400050"),
	("Chennai Digital Store", "23 Anna Salai", "Chennai", "Tamil Nadu", "600002"),
	("Hyderabad IT Traders", "56 Jubilee Hills", "Hyderabad", "Telangana", "500033"),
	("Kolkata Electronics Hub", "34 Park Street", "Kolkata", "West Bengal", "700016"),
	("Jaipur Smart Devices", "89 MI Road", "Jaipur", "Rajasthan", "302001"),
	("Ahmedabad Tech World", "12 CG Road", "Ahmedabad", "Gujarat", "380009"),
	("Pune Gadget Zone", "67 FC Road", "Pune", "Maharashtra", "411004"),
	("Surat Digital Mall", "45 Ring Road", "Surat", "Gujarat", "395002"),
	("Lucknow Electronics City", "23 Hazratganj", "Lucknow", "Uttar Pradesh", "226001"),
	("Kochi Mobile Hub", "11 MG Road", "Kochi", "Kerala", "682016"),
	("Bhopal Smart Tech", "78 MP Nagar", "Bhopal", "Madhya Pradesh", "462011"),
	("Indore Gadget Market", "34 Vijay Nagar", "Indore", "Madhya Pradesh", "452010"),
	("Nagpur Electronics Plaza", "56 Sitabuldi Main Road", "Nagpur", "Maharashtra", "440012"),
	("Chandigarh Tech Square", "17 Sector 17C", "Chandigarh", "Punjab", "160017"),
	("Coimbatore IT Solutions", "90 Avinashi Road", "Coimbatore", "Tamil Nadu", "641018"),
	("Vadodara Digital Zone", "25 Alkapuri Society", "Vadodara", "Gujarat", "390007"),
	("Patna Electronics Corner", "44 Fraser Road", "Patna", "Bihar", "800001"),
	("Visakhapatnam Tech City", "33 Dwaraka Nagar", "Visakhapatnam", "Andhra Pradesh", "530016"),
	("Amritsar Gadget Gallery", "12 Lawrence Road", "Amritsar", "Punjab", "143001"),
	("Nashik Smart Electronics", "67 College Road", "Nashik", "Maharashtra", "422005"),
	("Meerut Tech Market", "89 Begum Bridge Road", "Meerut", "Uttar Pradesh", "250001"),
	("Agra Electronics Store", "56 Fatehabad Road", "Agra", "Uttar Pradesh", "282001"),
	("Rajkot Mobile World", "23 Kalawad Road", "Rajkot", "Gujarat", "360005"),
	("Madurai Digital Hub", "78 Bypass Road", "Madurai", "Tamil Nadu", "625010"),
	("Ranchi Gadget Point", "34 Main Road Lalpur", "Ranchi", "Jharkhand", "834001"),
	("Guwahati Electronics City", "11 GS Road Ulubari", "Guwahati", "Assam", "781005"),
	("Dehradun Tech Store", "45 Rajpur Road", "Dehradun", "Uttarakhand", "248001"),
	("Raipur Smart Devices", "67 Pandri Main Road", "Raipur", "Chhattisgarh", "492001"),
	("Ludhiana Digital World", "89 Ferozepur Road", "Ludhiana", "Punjab", "141001"),
	("Bhubaneswar Tech Hub", "23 Janpath Nayapalli", "Bhubaneswar", "Odisha", "751022"),
	("Thiruvananthapuram Gadgets", "56 MG Road Thampanoor", "Thiruvananthapuram", "Kerala", "695001"),
	("Mysuru Electronics", "34 Dhanvantri Road", "Mysuru", "Karnataka", "570001"),
	("Mangaluru Tech Zone", "12 Balmatta Road", "Mangaluru", "Karnataka", "575001"),
	("Hubli Digital Store", "78 Lamington Road", "Hubli", "Karnataka", "580020"),
	("Varanasi Electronics Hub", "45 Sigra Main Road", "Varanasi", "Uttar Pradesh", "221010"),
	("Prayagraj Smart Tech", "67 Civil Lines", "Prayagraj", "Uttar Pradesh", "211001"),
	("Jodhpur Gadget Market", "23 Residency Road", "Jodhpur", "Rajasthan", "342001"),
	("Udaipur Electronics Plaza", "89 Hiran Magri Sector 14", "Udaipur", "Rajasthan", "313001"),
	("Gwalior Tech World", "34 MLN Road City Center", "Gwalior", "Madhya Pradesh", "474001"),
	("Jabalpur Digital Zone", "56 Napier Town", "Jabalpur", "Madhya Pradesh", "482001"),
	("Aurangabad Smart Gadgets", "12 Jalna Road Cidco", "Chhatrapati Sambhajinagar", "Maharashtra", "431001"),
	("Solapur Electronics City", "78 Vijapur Road", "Solapur", "Maharashtra", "413001"),
	("Kolhapur Tech Market", "45 Rajaram Road", "Kolhapur", "Maharashtra", "416001"),
	("Nellore Digital Hub", "23 Trunk Road", "Nellore", "Andhra Pradesh", "524001"),
	("Tirupati Gadget Store", "67 TP Area RTC Complex", "Tirupati", "Andhra Pradesh", "517501"),
	("Salem Electronics Point", "89 Omalur Main Road", "Salem", "Tamil Nadu", "636004"),
	("Tiruchirappalli Tech Store", "34 Bharathidasan Salai", "Tiruchirappalli", "Tamil Nadu", "620001"),
	("Guntur Smart Devices", "56 Brodipet 4th Lane", "Guntur", "Andhra Pradesh", "522002"),
]

SELLER_NAME = "TechVision Distributors Pvt Ltd"
SELLER_ADDR1 = "Plot 14, MIDC Industrial Area, Andheri East"
SELLER_ADDR2 = "Mumbai, Maharashtra - 400093"
SELLER_TAX = "27AABCT1234F1Z5"
SELLER_GSTIN = "GSTIN: 27AABCT1234F1Z5"

VAT_RATE = Decimal("0.10")
START_DATE = date(2023, 4, 7)
END_DATE = date(2024, 4, 7)
DATE_SPAN = (END_DATE - START_DATE).days


def D(v):
	return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt(v):
	return f"{float(v):,.2f}"


def rand_date(seed):
	r = random.Random(seed)
	return START_DATE + timedelta(days=r.randint(0, DATE_SPAN))


def P(text, st=None):
	return Paragraph(str(text), st or s_norm)


def build_invoice(invoice_no: int, out_dir: Path) -> Path:
	idx = invoice_no - 51109301
	r = random.Random(invoice_no)

	inv_date = rand_date(invoice_no)
	client = CLIENTS[idx]

	n_items = r.randint(1, 8)
	chosen = r.sample(PRODUCTS, n_items)

	line_items = []
	for desc, lo, hi in chosen:
		qty = D(r.randint(1, 10))
		net_price = D(r.randint(lo, hi))
		net_worth = D(qty * net_price)
		vat_amt = D(net_worth * VAT_RATE)
		gross = D(net_worth + vat_amt)
		line_items.append((desc, qty, net_price, net_worth, vat_amt, gross))

	total_net = D(sum(x[3] for x in line_items))
	total_vat = D(sum(x[4] for x in line_items))
	total_gross = D(sum(x[5] for x in line_items))

	out_path = out_dir / f"invoice_{invoice_no}.pdf"

	doc = SimpleDocTemplate(
		str(out_path),
		pagesize=A4,
		leftMargin=MARGIN,
		rightMargin=MARGIN,
		topMargin=20 * mm,
		bottomMargin=20 * mm,
		title=f"Invoice {invoice_no}",
		author=SELLER_NAME,
	)
	story = []

	story.append(P(f"Invoice no: {invoice_no}", s_title))
	story.append(Spacer(1, 2 * mm))

	hdr_tbl = Table([[P("Date of issue:", s_norm), P(inv_date.strftime("%d/%m/%Y"), s_norm)]], colWidths=[40 * mm, 120 * mm])
	hdr_tbl.setStyle(TableStyle([
		("VALIGN", (0, 0), (-1, -1), "TOP"),
		("LEFTPADDING", (0, 0), (-1, -1), 0),
		("RIGHTPADDING", (0, 0), (-1, -1), 0),
		("TOPPADDING", (0, 0), (-1, -1), 0),
		("BOTTOMPADDING", (0, 0), (-1, -1), 0),
	]))
	story.append(hdr_tbl)
	story.append(Spacer(1, 8 * mm))

	seller_cell = [
		P("Seller:", s_bold),
		Spacer(1, 2 * mm),
		P(SELLER_NAME, s_norm),
		P(SELLER_ADDR1, s_norm),
		P(SELLER_ADDR2, s_norm),
		Spacer(1, 3 * mm),
		P(f"Tax Id: {SELLER_TAX}", s_norm),
		P(SELLER_GSTIN, s_norm),
	]
	client_cell = [
		P("Client:", s_bold),
		Spacer(1, 2 * mm),
		P(client[0], s_norm),
		P(client[1], s_norm),
		P(f"{client[2]}, {client[3]} - {client[4]}", s_norm),
		Spacer(1, 3 * mm),
		P(f"Tax Id: {r.randint(100,999)}-{r.randint(10,99)}-{r.randint(1000,9999)}", s_norm),
	]
	sc_tbl = Table([[seller_cell, client_cell]], colWidths=[USABLE / 2, USABLE / 2])
	sc_tbl.setStyle(TableStyle([
		("VALIGN", (0, 0), (-1, -1), "TOP"),
		("LEFTPADDING", (0, 0), (-1, -1), 0),
		("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
		("TOPPADDING", (0, 0), (-1, -1), 0),
		("BOTTOMPADDING", (0, 0), (-1, -1), 0),
	]))
	story.append(sc_tbl)
	story.append(Spacer(1, 8 * mm))

	story.append(P("ITEMS", s_sec))

	rows = [[
		P("No.", s_th),
		P("Description", s_th),
		P("Qty", s_th_r),
		P("UM", s_th),
		P("Net Price", s_th_r),
		P("Net Worth", s_th_r),
		P("VAT %", s_th_r),
		P("Gross Worth", s_th_r),
	]]
	for i, (desc, qty, np_, nw, _, gross) in enumerate(line_items, 1):
		rows.append([
			P(f"{i}.", s_td),
			P(desc, s_td),
			P(fmt(qty), s_td_r),
			P("pcs", s_td),
			P(fmt(np_), s_td_r),
			P(fmt(nw), s_td_r),
			P("10%", s_td_r),
			P(fmt(gross), s_td_r),
		])

	ts = [
		("BOX", (0, 0), (-1, -1), 0.5, BORDER),
		("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
		("BACKGROUND", (0, 0), (-1, 0), GREY_BG),
		("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
		("TOPPADDING", (0, 0), (-1, -1), 4),
		("BOTTOMPADDING", (0, 0), (-1, -1), 4),
		("LEFTPADDING", (0, 0), (-1, -1), 4),
		("RIGHTPADDING", (0, 0), (-1, -1), 4),
		("VALIGN", (0, 0), (-1, -1), "TOP"),
	]
	for i in range(2, len(rows), 2):
		ts.append(("BACKGROUND", (0, i), (-1, i), ALT_BG))

	items_tbl = Table(rows, colWidths=COL_W, repeatRows=1)
	items_tbl.setStyle(TableStyle(ts))
	story.append(items_tbl)
	story.append(Spacer(1, 8 * mm))

	story.append(P("SUMMARY", s_sec))
	sum_rows = [
		[P("", s_th), P("VAT %", s_th_r), P("Net Worth", s_th_r), P("VAT", s_th_r), P("Gross Worth", s_th_r)],
		[P("", s_td), P("10%", s_td_r), P(fmt(total_net), s_td_r), P(fmt(total_vat), s_td_r), P(fmt(total_gross), s_td_r)],
		[P("Total", s_td_b), P("", s_td_br), P(f"INR {fmt(total_net)}", s_td_br), P(f"INR {fmt(total_vat)}", s_td_br), P(f"INR {fmt(total_gross)}", s_td_br)],
	]
	sum_tbl = Table(sum_rows, colWidths=SUM_W)
	sum_tbl.setStyle(TableStyle([
		("BOX", (0, 0), (-1, -1), 0.5, BORDER),
		("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
		("BACKGROUND", (0, 0), (-1, 0), GREY_BG),
		("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
		("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
		("TOPPADDING", (0, 0), (-1, -1), 4),
		("BOTTOMPADDING", (0, 0), (-1, -1), 4),
		("LEFTPADDING", (0, 0), (-1, -1), 4),
		("RIGHTPADDING", (0, 0), (-1, -1), 4),
		("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
	]))
	story.append(sum_tbl)

	doc.build(story)
	return out_path


def run(
	out_dir: str | Path | None = None,
	zip_path: str | Path | None = None,
	start_invoice_no: int | None = None,
	end_invoice_no: int | None = None,
	spot_check_invoice_nos: Iterable[int] | None = None,
) -> None:
	settings = get_settings()
	resolved_out_dir = Path(out_dir or settings.invoice_output_dir)
	resolved_zip_path = Path(zip_path or settings.invoice_zip_path)
	resolved_start = start_invoice_no if start_invoice_no is not None else settings.invoice_start_no
	resolved_end = end_invoice_no if end_invoice_no is not None else settings.invoice_end_no
	resolved_spot_checks = tuple(settings.spot_check_invoice_nos if spot_check_invoice_nos is None else spot_check_invoice_nos)

	resolved_out_dir.mkdir(parents=True, exist_ok=True)
	resolved_zip_path.parent.mkdir(parents=True, exist_ok=True)

	invoice_count = max(0, resolved_end - resolved_start)
	print(f"Generating {invoice_count} invoices ...")
	paths = []
	for inv_no in range(resolved_start, resolved_end):
		path = build_invoice(inv_no, resolved_out_dir)
		paths.append(path)
		print(f"  ✅ invoice_{inv_no}.pdf")

	print(f"\nCreating ZIP at {resolved_zip_path} ...")
	with zipfile.ZipFile(resolved_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
		for path in paths:
			zf.write(path, arcname=path.name)
	print(f"✅ ZIP created with {len(paths)} PDFs.\n")

	print("Spot-checking 3 invoices with pdfplumber ...")
	for inv_no in resolved_spot_checks:
		fp = resolved_out_dir / f"invoice_{inv_no}.pdf"
		if not fp.exists():
			print(f"  invoice_{inv_no}: skipped (missing {fp.name})")
			continue
		with pdfplumber.open(fp) as pdf:
			tables = pdf.pages[0].extract_tables()
			text = pdf.pages[0].extract_text()
		print(
			f"  invoice_{inv_no}: {len(tables)} tables | "
			f"items table rows={len(tables[0]) - 1} | "
			f"text chars={len(text)}"
		)
	print("\nAll done!")


def main() -> None:
	run()


if __name__ == "__main__":
	main()
