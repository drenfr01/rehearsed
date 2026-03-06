import jsPDF from 'jspdf';
import { SummaryFeedbackResponse } from '../models/chat-graph.model';

const PAGE_MARGIN = 15;
const TITLE_FONT_SIZE = 20;
const HEADER_FONT_SIZE = 14;
const BODY_FONT_SIZE = 11;
const LINE_HEIGHT_FACTOR = 1.5;

interface FeedbackSection {
  title: string;
  body: string;
}

export const pdfDeps = {
  createPdf: () => new jsPDF('p', 'mm', 'a4'),
};

function stripMarkdown(md: string): string {
  return md
    .replace(/^#{1,6}\s+/gm, '')        // headings
    .replace(/\*\*(.+?)\*\*/g, '$1')    // bold
    .replace(/\*(.+?)\*/g, '$1')        // italic
    .replace(/__(.+?)__/g, '$1')        // bold alt
    .replace(/_(.+?)_/g, '$1')          // italic alt
    .replace(/~~(.+?)~~/g, '$1')        // strikethrough
    .replace(/`(.+?)`/g, '$1')          // inline code
    .replace(/^\s*[-*+]\s+/gm, '  - ')  // unordered lists
    .replace(/^\s*\d+\.\s+/gm, '  - ')  // ordered lists -> normalized
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1') // images
    .replace(/^>\s?/gm, '')             // blockquotes
    .replace(/^---+$/gm, '')            // horizontal rules
    .replace(/\n{3,}/g, '\n\n')         // collapse excessive newlines
    .trim();
}

function buildSections(data: SummaryFeedbackResponse): FeedbackSection[] {
  return [
    { title: 'Lesson Summary', body: data.lesson_summary },
    { title: 'Key Moments', body: data.key_moments },
    { title: 'Overall Feedback', body: data.overall_feedback },
    { title: 'Your Strengths', body: data.your_strengths },
    { title: 'Areas for Growth', body: data.areas_for_growth },
    { title: 'Next Steps', body: data.next_steps },
    { title: 'Celebration', body: data.celebration },
  ].filter(s => s.body?.trim());
}

function lineHeightMm(fontSize: number): number {
  return (fontSize * LINE_HEIGHT_FACTOR * 25.4) / 72;
}

export function downloadFeedbackAsPdf(
  feedback: SummaryFeedbackResponse | string | null,
  filename = 'session-feedback.pdf',
): void {
  if (!feedback) return;

  const pdf = pdfDeps.createPdf();
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const contentWidth = pageWidth - PAGE_MARGIN * 2;
  const bottomLimit = pageHeight - PAGE_MARGIN;
  let y = PAGE_MARGIN;

  function ensureSpace(needed: number): void {
    if (y + needed > bottomLimit) {
      pdf.addPage();
      y = PAGE_MARGIN;
    }
  }

  function renderLines(lines: string[], fontSize: number): void {
    const lh = lineHeightMm(fontSize);
    for (const line of lines) {
      ensureSpace(lh);
      pdf.text(line, PAGE_MARGIN, y);
      y += lh;
    }
  }

  // Title
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(TITLE_FONT_SIZE);
  pdf.text('Session Summary', pageWidth / 2, y, { align: 'center' });
  y += lineHeightMm(TITLE_FONT_SIZE) + 4;

  if (typeof feedback === 'string') {
    const plain = stripMarkdown(feedback);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(BODY_FONT_SIZE);
    const lines: string[] = pdf.splitTextToSize(plain, contentWidth);
    renderLines(lines, BODY_FONT_SIZE);
  } else {
    const sections = buildSections(feedback);
    for (const section of sections) {
      // Section header
      ensureSpace(lineHeightMm(HEADER_FONT_SIZE) + lineHeightMm(BODY_FONT_SIZE));
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(HEADER_FONT_SIZE);
      pdf.text(section.title, PAGE_MARGIN, y);
      y += lineHeightMm(HEADER_FONT_SIZE) + 1;

      // Section body
      const plain = stripMarkdown(section.body);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(BODY_FONT_SIZE);
      const lines: string[] = pdf.splitTextToSize(plain, contentWidth);
      renderLines(lines, BODY_FONT_SIZE);
      y += 4;
    }
  }

  pdf.save(filename);
}
