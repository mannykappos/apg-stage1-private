// Turn a Claude-doc markdown export into a formatted A4 Word document.
// usage: node md2docx.js input.md output.docx [diagram.png "placeholder substring"] [subtitle]
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, LevelFormat, BorderStyle, ImageRun, Footer, PageNumber, TableLayoutType,
} = require('docx');

const [, , inPath, outPath, imgPath, imgMarker, subtitle] = process.argv;
const lines = fs.readFileSync(inPath, 'utf8').replace(/\r/g, '').split('\n');

const FONT = 'Arial';
const INK = '1F2933', MUTED = '5B6670', ACCENT = '1F4E79', RULE = 'C9D2DB', HEAD_FILL = 'E8EEF4', ZEBRA = 'F6F8FA';
const PAGE_W = 11906, MARGIN = 1134, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, 2 cm margins

function unescape(s) {
  return s.replace(/\\([\\`*_{}\[\]()#+\-.!|>])/g, '$1').replace(/&#91;/g, '[').replace(/&amp;/g, '&');
}

// inline: **bold**, `code`, [text](url)
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0, m;
  const push = (t, extra = {}) => { if (t) out.push(new TextRun({ text: unescape(t), font: FONT, color: INK, ...base, ...extra })); };
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) push(tok.slice(2, -2), { bold: true });
    else if (tok.startsWith('`')) push(tok.slice(1, -1), { font: 'Consolas', color: '334E68' });
    else { const mm = tok.match(/\[([^\]]+)\]\(([^)]+)\)/); push(mm[1], { color: ACCENT, underline: {} }); }
    last = m.index + tok.length;
  }
  push(text.slice(last));
  return out;
}

const children = [];
const para = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), spacing: { after: 120, line: 276 }, ...opts.p });

function table(rows) {
  const cells = rows.map(r => r.replace(/^\||\|$/g, '').split(/(?<!\\)\|/).map(c => c.trim()));
  const header = cells[0], body = cells.slice(2);
  const n = header.length;
  // column widths from content length, with a floor
  const clean = s => unescape(s.replace(/\*\*|`/g, ''));
  const len = header.map((h, i) => Math.max(h.length, ...body.map(r => clean(r[i] || '').length)));
  // a column is never narrower than its longest word (header included), at ~95 dxa per character of 8.5 pt text
  const minW = header.map((h, i) => Math.max(...[h, ...body.map(r => r[i] || '')].map(c => Math.max(...clean(c).split(/\s+/).map(w => w.length)))) * 95 + 220);
  const weights = len.map(l => Math.max(4, Math.min(l, 90)));
  const spare = CONTENT_W - minW.reduce((a, b) => a + b, 0);
  const total = weights.reduce((a, b) => a + b, 0);
  let widths = spare > 0 ? minW.map((m, i) => m + Math.floor(spare * weights[i] / total)) : weights.map(w => Math.floor(CONTENT_W * w / total));
  widths[n - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: RULE };
  const borders = { top: border, bottom: border, left: border, right: border };
  const mk = (r, isHead, zebra) => new TableRow({
    tableHeader: isHead, cantSplit: true,
    children: r.map((c, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA }, borders,
      shading: isHead ? { type: ShadingType.CLEAR, fill: HEAD_FILL, color: 'auto' } : zebra ? { type: ShadingType.CLEAR, fill: ZEBRA, color: 'auto' } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({ children: runs(c, { size: 17, bold: isHead || undefined }), spacing: { after: 0, line: 252 } })],
    })),
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    rows: [mk(header, true, false), ...body.map((r, k) => mk(r, false, k % 2 === 1))],
  });
}

let i = 0;
let listRef = 0;
while (i < lines.length) {
  const l = lines[i];
  if (!l.trim()) { i++; continue; }
  if (l.startsWith('# ')) {
    children.push(new Paragraph({ heading: HeadingLevel.TITLE, children: runs(l.slice(2)) }));
    if (subtitle) children.push(new Paragraph({ children: runs(subtitle, { color: MUTED, size: 20 }), spacing: { after: 240 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: ACCENT, space: 6 } } }));
    i++; continue;
  }
  if (/^Nov \d+, \d{4} · /.test(l)) { i++; continue; } // the doc's byline chip line; the subtitle replaces it
  if (l.startsWith('## ')) { children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(l.slice(3)) })); i++; continue; }
  if (l.startsWith('### ')) { children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(l.slice(4)) })); i++; continue; }
  if (l.startsWith('|')) {
    const rows = []; while (i < lines.length && lines[i].startsWith('|')) rows.push(lines[i++]);
    children.push(table(rows)); children.push(new Paragraph({ children: [], spacing: { after: 120 } })); continue;
  }
  if (imgPath && imgMarker && l.includes(imgMarker)) {
    const data = fs.readFileSync(imgPath);
    const w = data.readUInt32BE(16), h = data.readUInt32BE(20);
    const maxW = 640; // px at 96 dpi ~ 16.9 cm
    children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 },
      children: [new ImageRun({ type: 'png', data, transformation: { width: maxW, height: Math.round(maxW * h / w) } })] }));
    i++; continue;
  }
  if (/^\s*[-*] /.test(l) || /^\s*\d+\. /.test(l)) {
    const ordered = /^\s*\d+\. /.test(l);
    const ref = ordered ? `num${listRef++}` : 'bullets';
    while (i < lines.length && (/^\s*[-*] /.test(lines[i]) || /^\s*\d+\. /.test(lines[i]))) {
      const cur = lines[i];
      const level = Math.min(2, Math.floor((cur.match(/^\s*/)[0].length) / 4));
      const isOrd = /^\s*\d+\. /.test(cur);
      const text = cur.replace(/^\s*([-*]|\d+\.) /, '');
      children.push(new Paragraph({ numbering: { reference: isOrd ? ref : 'bullets', level }, children: runs(text), spacing: { after: 80, line: 276 } }));
      i++;
    }
    continue;
  }
  // paragraph: join until blank
  const buf = [l]; i++;
  while (i < lines.length && lines[i].trim() && !/^(#|\||\s*[-*] |\s*\d+\. )/.test(lines[i])) buf.push(lines[i++]);
  children.push(para(buf.join(' ')));
}

const numConfigs = [{ reference: 'bullets', levels: [0, 1, 2].map(lv => ({ level: lv, format: LevelFormat.BULLET, text: ['•', '–', '•'][lv], alignment: AlignmentType.LEFT,
  style: { paragraph: { indent: { left: 360 + lv * 360, hanging: 260 } } } })) }];
for (let k = 0; k < listRef; k++) numConfigs.push({ reference: `num${k}`, levels: [0, 1, 2].map(lv => ({ level: lv, format: lv === 1 ? LevelFormat.LOWER_LETTER : LevelFormat.DECIMAL,
  text: `%${lv + 1}.`, alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360 + lv * 360, hanging: 300 } } } })) });

const doc = new Document({
  creator: 'Claude (builder)', title: lines[0].replace(/^# /, ''),
  styles: {
    default: { document: { run: { font: FONT, size: 20, color: INK } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', run: { font: FONT, size: 36, bold: true, color: ACCENT }, paragraph: { spacing: { before: 0, after: 80 }, keepNext: true } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 28, bold: true, color: ACCENT },
        paragraph: { spacing: { before: 320, after: 120 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 23, bold: true, color: INK },
        paragraph: { spacing: { before: 220, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: numConfigs },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: 'Page ', font: FONT, size: 16, color: MUTED }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: MUTED }),
                 new TextRun({ text: ' of ', font: FONT, size: 16, color: MUTED }), new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: MUTED })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(outPath, b); console.log('wrote', outPath, b.length); });
