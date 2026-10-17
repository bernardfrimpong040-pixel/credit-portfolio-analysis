"""
STEP 8a - Build the Excel limits workbook
=========================================

What this script does, in plain words:
  Reads outputs/limit_monitor.csv (made in Step 4) and builds an Excel file,
  outputs/concentration_limits.xlsx, with four sheets:

    Read Me        what the workbook is and how to use it
    Settings       the limit settings, in YELLOW cells you can change
    Limit Monitor  one row per industry and state. The limit, headroom,
                   % of limit used and status are all FORMULAS that read
                   the Settings sheet
    Summary        counts of Breach / Watch / Within, also formulas

  Because everything is a formula, changing one number on the Settings sheet
  (say the industry limit from 15% to 18%) updates every status straight away.
  That is what banks do each year when they "recalibrate" their limits.

How to run it:
    python scripts/04_concentration_limits.py    (only if you haven't yet)
    python scripts/08_build_limits_workbook.py

Then open outputs/concentration_limits.xlsx in Excel.
"""

from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

PROJECT_FOLDER = Path(__file__).parent.parent
OUTPUT_FOLDER = PROJECT_FOLDER / "outputs"
MONITOR_CSV = OUTPUT_FOLDER / "limit_monitor.csv"
WORKBOOK_FILE = OUTPUT_FOLDER / "concentration_limits.xlsx"

if not MONITOR_CSV.exists():
    print("I can't find outputs/limit_monitor.csv. Run Step 4 first:")
    print("    python scripts/04_concentration_limits.py")
    raise SystemExit

data = pd.read_csv(MONITOR_CSV)
# Industries first, then states; biggest share first inside each
data["dimension_order"] = data["dimension"].map({"Industry": 0, "State": 1})
data = data.sort_values(["dimension_order", "pct_of_dollars"], ascending=[True, False])

# ---------------------------------------------------------------------------
# Styles (kept in one place). The colour rules are the usual finance ones:
#   blue text   = a number typed in (an input)
#   black text  = a formula
#   green text  = a formula that reads another sheet
#   yellow fill = a cell you are meant to change
# ---------------------------------------------------------------------------
FONT_NAME = "Arial"
normal = Font(name=FONT_NAME, size=10)
bold = Font(name=FONT_NAME, size=10, bold=True)
title_font = Font(name=FONT_NAME, size=14, bold=True)
input_font = Font(name=FONT_NAME, size=10, color="0000FF")      # blue
link_font = Font(name=FONT_NAME, size=10, color="008000")       # green
header_font = Font(name=FONT_NAME, size=10, bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="1F4E79")
yellow_fill = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top")

workbook = Workbook()

# ===========================================================================
# Sheet 1: Read Me
# ===========================================================================
readme = workbook.active
readme.title = "Read Me"
readme.column_dimensions["A"].width = 110
lines = [
    ("Concentration Limits Workbook", title_font),
    ("", normal),
    ("What it is", bold),
    ("A limit monitor for an SBA 7(a) small-business loan portfolio (loans approved 2001-2010). "
     "Each industry and state has a limit: the most of the portfolio it may hold. "
     "Riskier groups get a tighter limit.", normal),
    ("", normal),
    ("How to use it", bold),
    ("1. Go to the Settings sheet and change any YELLOW cell (for example the industry limit).", normal),
    ("2. The Limit Monitor and Summary sheets update by themselves: every limit, headroom and status is a formula.", normal),
    ("3. Use the filter arrows on the Limit Monitor header row to show only Breach or Watch rows.", normal),
    ("", normal),
    ("Colour key", bold),
    ("Yellow cell = a setting you can change.   Blue text = a number typed in.   "
     "Black text = a formula.   Green text = a formula reading another sheet.", normal),
    ("", normal),
    ("Status rules", bold),
    ("Breach = share of dollars is above the limit.   Watch = share has used the watch level (e.g. 80%) "
     "of the limit or more.   Within = comfortably inside the limit.", normal),
    ("Risk index = share of dollars lost / share of dollars lent. Above 1 means the group "
     "loses more than its size suggests.", normal),
    ("", normal),
    ("Important", bold),
    ("The limit settings are EXAMPLE values chosen for this portfolio project. They are not SBA "
     "or bank policy.", normal),
    ("", normal),
    ("Source", bold),
    ("U.S. Small Business Administration 7(a) loan data (Kaggle: 'Should This Loan be Approved or "
     "Denied?'), cleaned and analysed in this project. Shares and risk indexes come from "
     "outputs/limit_monitor.csv, built by scripts/04_concentration_limits.py.", normal),
]
for row_number, (text, font) in enumerate(lines, start=1):
    cell = readme.cell(row=row_number, column=1, value=text)
    cell.font = font
    cell.alignment = Alignment(wrap_text=True, vertical="top")

# ===========================================================================
# Sheet 2: Settings (the inputs)
# ===========================================================================
settings = workbook.create_sheet("Settings")
settings.column_dimensions["A"].width = 46
settings.column_dimensions["B"].width = 14
settings.column_dimensions["C"].width = 70
settings["A1"] = "Limit settings (change the yellow cells)"
settings["A1"].font = title_font

for col, text in enumerate(["Setting", "Value", "What it means"], start=1):
    cell = settings.cell(row=3, column=col, value=text)
    cell.font, cell.fill, cell.border = header_font, header_fill, box

# (row, label, value, number format, explanation)
setting_rows = [
    (4, "Industry limit", 0.15, "0.0%", "Most of the portfolio's dollars one industry may hold"),
    (5, "Industry limit, high-risk", 0.10, "0.0%", "Tighter limit for industries with a high risk index"),
    (6, "State limit", 0.10, "0.0%", "Most of the portfolio's dollars one state may hold"),
    (7, "State limit, high-risk", 0.075, "0.0%", "Tighter limit for states with a high risk index"),
    (8, "High-risk if risk index is above", 1.25, "0.00", "Risk index = share of losses / share of dollars"),
    (9, "Watch level (share of limit used)", 0.80, "0%", "Status becomes Watch once this much of the limit is used"),
]
for row, label, value, number_format, explanation in setting_rows:
    settings.cell(row=row, column=1, value=label).font = normal
    value_cell = settings.cell(row=row, column=2, value=value)
    value_cell.font, value_cell.fill, value_cell.number_format = input_font, yellow_fill, number_format
    settings.cell(row=row, column=3, value=explanation).font = normal
    for col in range(1, 4):
        settings.cell(row=row, column=col).border = box
settings["B4"].comment = Comment(
    "Example setting chosen for this project, not SBA or bank policy. "
    "Change it and watch the Limit Monitor update.", "Portfolio project")
settings["A11"] = "These are example settings for a portfolio project, not real policy."
settings["A11"].font = Font(name=FONT_NAME, size=9, italic=True)

# ===========================================================================
# Sheet 3: Limit Monitor (data + formulas)
# ===========================================================================
monitor = workbook.create_sheet("Limit Monitor")
headers = ["Dimension", "Group", "Loans", "Share of dollars", "Share of losses",
           "Risk index", "High risk?", "Limit", "Headroom", "Limit used", "Status"]
widths = [11, 44, 10, 15, 15, 11, 11, 10, 11, 11, 11]
for col, (text, width) in enumerate(zip(headers, widths), start=1):
    cell = monitor.cell(row=1, column=col, value=text)
    cell.font, cell.fill, cell.border = header_font, header_fill, box
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    monitor.column_dimensions[get_column_letter(col)].width = width
monitor.freeze_panes = "C2"      # headers and group names stay visible while scrolling

first_row = 2
for offset, record in enumerate(data.itertuples(index=False)):
    r = first_row + offset
    # Inputs from the analysis (blue). Shares are stored as fractions: 0.172 shows as 17.2%
    monitor.cell(row=r, column=1, value=record.dimension).font = normal
    monitor.cell(row=r, column=2, value=record.group_name).font = normal
    monitor.cell(row=r, column=3, value=int(record.number_of_loans)).font = input_font
    monitor.cell(row=r, column=4, value=record.pct_of_dollars / 100).font = input_font
    monitor.cell(row=r, column=5, value=record.pct_of_losses / 100).font = input_font

    # Formulas (black = same sheet, green = reads the Settings sheet)
    monitor.cell(row=r, column=6, value=f"=IF(D{r}>0,E{r}/D{r},0)").font = normal
    monitor.cell(row=r, column=7, value=f'=IF(F{r}>Settings!$B$8,"Yes","No")').font = link_font
    monitor.cell(row=r, column=8, value=(
        f'=IF(A{r}="Industry",IF(G{r}="Yes",Settings!$B$5,Settings!$B$4),'
        f'IF(G{r}="Yes",Settings!$B$7,Settings!$B$6))')).font = link_font
    monitor.cell(row=r, column=9, value=f"=H{r}-D{r}").font = normal
    monitor.cell(row=r, column=10, value=f"=IF(H{r}>0,D{r}/H{r},0)").font = normal
    monitor.cell(row=r, column=11, value=(
        f'=IF(J{r}>1,"Breach",IF(J{r}>=Settings!$B$9,"Watch","Within"))')).font = link_font

    for col, number_format in [(3, "#,##0"), (4, "0.00%"), (5, "0.00%"), (6, "0.00"),
                               (8, "0.0%"), (9, "0.00%;(0.00%);-"), (10, "0%")]:
        monitor.cell(row=r, column=col).number_format = number_format
    for col in range(1, 12):
        monitor.cell(row=r, column=col).border = box

last_row = first_row + len(data) - 1
monitor.auto_filter.ref = f"A1:K{last_row}"

# Colour the Status cell (the word itself is always shown, so colour is never alone)
status_range = f"K{first_row}:K{last_row}"
for word, fill_colour in [("Breach", "F4B6B6"), ("Watch", "FCE4A6"), ("Within", "C6EFCE")]:
    monitor.conditional_formatting.add(
        status_range,
        FormulaRule(formula=[f'$K{first_row}="{word}"'],
                    fill=PatternFill("solid", fgColor=fill_colour)))
# Negative headroom (over the limit) in red text
monitor.conditional_formatting.add(
    f"I{first_row}:I{last_row}",
    FormulaRule(formula=[f"$I{first_row}<0"], font=Font(name=FONT_NAME, size=10, color="C00000")))

note_row = last_row + 2
monitor.cell(row=note_row, column=1,
             value="Source: outputs/limit_monitor.csv (Step 4), loans approved 2001-2010. "
                   "Blue = inputs from the analysis. Limit, headroom, limit used and status are formulas."
             ).font = Font(name=FONT_NAME, size=9, italic=True)

# ===========================================================================
# Sheet 4: Summary (formulas only)
# ===========================================================================
summary = workbook.create_sheet("Summary")
summary.column_dimensions["A"].width = 34
for col in "BCDE":
    summary.column_dimensions[col].width = 13
summary["A1"] = "Limit monitor summary"
summary["A1"].font = title_font

for col, text in enumerate(["Dimension", "Breach", "Watch", "Within", "Total"], start=1):
    cell = summary.cell(row=3, column=col, value=text)
    cell.font, cell.fill, cell.border = header_font, header_fill, box

monitor_ref = "'Limit Monitor'"
dim_range = f"{monitor_ref}!$A${first_row}:$A${last_row}"
status_ref = f"{monitor_ref}!$K${first_row}:$K${last_row}"
share_ref = f"{monitor_ref}!$D${first_row}:$D${last_row}"
group_ref = f"{monitor_ref}!$B${first_row}:$B${last_row}"

for r, dimension in [(4, "Industry"), (5, "State")]:
    summary.cell(row=r, column=1, value=dimension).font = normal
    for col, word in [(2, "Breach"), (3, "Watch"), (4, "Within")]:
        summary.cell(row=r, column=col,
                     value=f'=COUNTIFS({dim_range},$A{r},{status_ref},"{word}")').font = link_font
    summary.cell(row=r, column=5, value=f"=SUM(B{r}:D{r})").font = normal
summary["A6"] = "Total"
summary["A6"].font = bold
for col in "BCDE":
    summary[f"{col}6"] = f"=SUM({col}4:{col}5)"
    summary[f"{col}6"].font = bold
for r in range(4, 7):
    for col in range(1, 6):
        summary.cell(row=r, column=col).border = box

# Largest single exposure in each dimension, found with INDEX/MATCH
summary["A8"] = "Largest exposures"
summary["A8"].font = bold
for col, text in enumerate(["Dimension", "Group", "Share of dollars"], start=1):
    cell = summary.cell(row=9, column=col, value=text)
    cell.font, cell.fill, cell.border = header_font, header_fill, box
summary.column_dimensions["B"].width = 40
for r, dimension in [(10, "Industry"), (11, "State")]:
    summary.cell(row=r, column=1, value=dimension).font = normal
    # Largest share for this dimension: MAX over an IF that keeps only matching rows.
    # SUMPRODUCT(MAX(...)) makes it work as a normal formula (no Ctrl+Shift+Enter).
    summary.cell(row=r, column=3,
                 value=f"=SUMPRODUCT(MAX(({dim_range}=$A{r})*{share_ref}))").font = link_font
    summary.cell(row=r, column=3).number_format = "0.0%"
    summary.cell(row=r, column=2,
                 value=(f"=INDEX({group_ref},MATCH(1,INDEX(({dim_range}=$A{r})*"
                        f"({share_ref}=C{r}),0),0))")).font = link_font
    for col in range(1, 4):
        summary.cell(row=r, column=col).border = box

# A tie-out check: each dimension's shares should add up to 100%
summary["A13"] = "Check: shares add up to 100%"
summary["A13"].font = bold
for r, dimension in [(14, "Industry"), (15, "State")]:
    summary.cell(row=r, column=1, value=dimension).font = normal
    summary.cell(row=r, column=2, value=f"=SUMIFS({share_ref},{dim_range},$A{r})").font = link_font
    summary.cell(row=r, column=2).number_format = "0.0%"
    summary.cell(row=r, column=3,
                 value=f'=IF(ABS(B{r}-1)<0.005,"OK","Check")').font = normal
    for col in range(1, 4):
        summary.cell(row=r, column=col).border = box

# Make Summary the sheet that opens first after Read Me
workbook.move_sheet("Summary", offset=-1)

WORKBOOK_FILE.parent.mkdir(exist_ok=True)
workbook.save(WORKBOOK_FILE)
print(f"Saved {WORKBOOK_FILE}")
print(f"   {len(data)} groups on the Limit Monitor sheet")
print("Open it in Excel, then try changing a yellow cell on the Settings sheet.")
