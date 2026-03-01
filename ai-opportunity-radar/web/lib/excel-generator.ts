import ExcelJS from "exceljs";
import type { Profile, ScoredOpportunity } from "@/types";

export async function generateExcel(
  profile: Profile,
  opportunities: ScoredOpportunity[],
  role: string,
  location: string
): Promise<Buffer> {
  const wb = new ExcelJS.Workbook();
  wb.creator = "AI Opportunity Radar";

  // --- Sheet 1: Opportunities ---
  const ws = wb.addWorksheet("Opportunities");

  ws.mergeCells("A1:I1");
  const titleCell = ws.getCell("A1");
  titleCell.value = "AI Opportunity Radar Report";
  titleCell.font = { name: "Calibri", bold: true, size: 16, color: { argb: "FF2F5496" } };
  titleCell.alignment = { horizontal: "left" };

  const info = [
    ["Profile:", profile.name || "N/A"],
    ["Target Role:", role],
    ["Location:", location],
    ["Generated:", new Date().toISOString().replace("T", " ").slice(0, 19)],
    ["Total:", String(opportunities.length)],
  ];
  info.forEach(([label, value], i) => {
    ws.getCell(`A${i + 2}`).value = label;
    ws.getCell(`A${i + 2}`).font = { bold: true, size: 10 };
    ws.getCell(`B${i + 2}`).value = value;
  });

  const headerRow = info.length + 3;
  const headers = [
    "Rank", "Job Title", "Company", "Location", "Match Score",
    "Match Analysis", "Application Tips", "Contact Email", "Link",
  ];
  const widths = [6, 35, 25, 25, 13, 50, 50, 30, 45];

  headers.forEach((h, i) => {
    const cell = ws.getCell(headerRow, i + 1);
    cell.value = h;
    cell.font = { bold: true, color: { argb: "FFFFFFFF" }, size: 11 };
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF2F5496" } };
    cell.alignment = { horizontal: "center", vertical: "middle", wrapText: true };
    cell.border = {
      top: { style: "thin" }, bottom: { style: "thin" },
      left: { style: "thin" }, right: { style: "thin" },
    };
    ws.getColumn(i + 1).width = widths[i];
  });

  const greenFill: ExcelJS.FillPattern = { type: "pattern", pattern: "solid", fgColor: { argb: "FFC6EFCE" } };
  const yellowFill: ExcelJS.FillPattern = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFEB9C" } };
  const redFill: ExcelJS.FillPattern = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFC7CE" } };
  const thinBorder: Partial<ExcelJS.Borders> = {
    top: { style: "thin" }, bottom: { style: "thin" },
    left: { style: "thin" }, right: { style: "thin" },
  };

  opportunities.forEach((opp, i) => {
    const row = headerRow + i + 1;
    const score = opp.matchScore || 0;
    const fill = score >= 80 ? greenFill : score >= 60 ? yellowFill : redFill;

    const emails = opp.emails?.length
      ? opp.emails.join(", ")
      : opp.contactEmail || "";

    const values = [
      i + 1, opp.jobTitle, opp.company, opp.location,
      score, opp.matchExplanation, opp.applicationTips,
      emails, opp.url,
    ];

    values.forEach((v, j) => {
      const cell = ws.getCell(row, j + 1);
      cell.value = v;
      cell.fill = fill;
      cell.border = thinBorder;
      cell.alignment = { vertical: "top", wrapText: true };
    });
  });

  ws.autoFilter = {
    from: { row: headerRow, column: 1 },
    to: { row: headerRow + opportunities.length, column: 9 },
  };
  ws.views = [{ state: "frozen", ySplit: headerRow }];

  // --- Sheet 2: Profile ---
  const ws2 = wb.addWorksheet("Profile");
  ws2.getCell("A1").value = "Profile Summary";
  ws2.getCell("A1").font = { bold: true, size: 14, color: { argb: "FF2F5496" } };
  ws2.mergeCells("A1:B1");

  const fields: [string, string][] = [
    ["Name", profile.name],
    ["Headline", profile.headline],
    ["Current Role", profile.currentRole],
    ["Company", profile.company],
    ["Location", profile.location],
    ["Skills", profile.skills.join(", ")],
    ["Experience", profile.experience.join("\n")],
    ["Education", profile.education.join("\n")],
  ];
  fields.forEach(([label, value], i) => {
    ws2.getCell(`A${i + 3}`).value = label;
    ws2.getCell(`A${i + 3}`).font = { bold: true };
    ws2.getCell(`B${i + 3}`).value = value;
    ws2.getCell(`B${i + 3}`).alignment = { wrapText: true };
  });
  ws2.getColumn(1).width = 15;
  ws2.getColumn(2).width = 80;

  const buffer = await wb.xlsx.writeBuffer();
  return Buffer.from(buffer);
}
