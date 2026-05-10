import { InlineFeedbackEntry, Message, SummaryFeedbackResponse } from '../models/chat-graph.model';

const PAGE_MARGIN = 15;
const TITLE_FONT_SIZE = 20;
const SECTION_TITLE_FONT_SIZE = 16;
const HEADER_FONT_SIZE = 14;
const BODY_FONT_SIZE = 11;
const SMALL_FONT_SIZE = 10;
const LINE_HEIGHT_FACTOR = 1.5;
const INDENT = 10;

export interface PdfDownloadData {
  summaryFeedback: SummaryFeedbackResponse | string | null;
  transcript?: Message[];
  inlineFeedback?: InlineFeedbackEntry[];
}

interface FeedbackSection {
  title: string;
  body: string;
}

export const pdfDeps = {
  createPdf: async () => {
    const { default: jsPDF } = await import('jspdf');
    return new jsPDF('p', 'mm', 'a4');
  },
};

function stripMarkdown(md: string): string {
  return md
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/~~(.+?)~~/g, '$1')
    .replace(/`(.+?)`/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '  - ')
    .replace(/^\s*\d+\.\s+/gm, '  - ')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/^>\s?/gm, '')
    .replace(/^---+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
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
  data: PdfDownloadData,
  filename?: string,
): Promise<void>;
export function downloadFeedbackAsPdf(
  data: SummaryFeedbackResponse | string | null,
  filename?: string,
): Promise<void>;
export async function downloadFeedbackAsPdf(
  dataOrLegacy: PdfDownloadData | SummaryFeedbackResponse | string | null,
  filename = 'session-feedback.pdf',
): Promise<void> {
  let pdfData: PdfDownloadData;

  if (dataOrLegacy === null) return;

  if (typeof dataOrLegacy === 'string') {
    pdfData = { summaryFeedback: dataOrLegacy };
  } else if ('summaryFeedback' in dataOrLegacy) {
    pdfData = dataOrLegacy;
  } else {
    pdfData = { summaryFeedback: dataOrLegacy as SummaryFeedbackResponse };
  }

  const { summaryFeedback, transcript, inlineFeedback } = pdfData;
  if (!summaryFeedback && (!transcript || transcript.length === 0)) return;

  const pdf = await pdfDeps.createPdf();
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

  function renderLines(lines: string[], fontSize: number, x = PAGE_MARGIN): void {
    const lh = lineHeightMm(fontSize);
    for (const line of lines) {
      ensureSpace(lh);
      pdf.text(line, x, y);
      y += lh;
    }
  }

  // Title
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(TITLE_FONT_SIZE);
  pdf.text('Session Report', pageWidth / 2, y, { align: 'center' });
  y += lineHeightMm(TITLE_FONT_SIZE) + 4;

  // Conversation section
  if (transcript && transcript.length > 0) {
    const feedbackByTurnId = new Map<string, InlineFeedbackEntry>();
    if (inlineFeedback) {
      for (const entry of inlineFeedback) {
        feedbackByTurnId.set(entry.turnId, entry);
      }
    }

    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(SECTION_TITLE_FONT_SIZE);
    ensureSpace(lineHeightMm(SECTION_TITLE_FONT_SIZE) + 2);
    pdf.text('Conversation', PAGE_MARGIN, y);
    y += lineHeightMm(SECTION_TITLE_FONT_SIZE) + 2;

    // Separator line
    pdf.setDrawColor(180, 180, 180);
    pdf.line(PAGE_MARGIN, y, pageWidth - PAGE_MARGIN, y);
    y += 3;

    for (const message of transcript) {
      const roleLabel =
        message.role === 'user'
          ? 'Teacher:'
          : `Student (${message.student_name ?? 'Unknown'}):`;

      // Role label
      ensureSpace(lineHeightMm(BODY_FONT_SIZE) * 2);
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(BODY_FONT_SIZE);
      pdf.text(roleLabel, PAGE_MARGIN, y);
      y += lineHeightMm(BODY_FONT_SIZE);

      // Message content
      const plain = stripMarkdown(message.content);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(BODY_FONT_SIZE);
      const msgLines: string[] = pdf.splitTextToSize(plain, contentWidth - INDENT);
      renderLines(msgLines, BODY_FONT_SIZE, PAGE_MARGIN + INDENT);

      // Coach feedback for user messages
      if (message.role === 'user' && message.turnId) {
        const entry = feedbackByTurnId.get(message.turnId);
        if (entry && entry.status === 'ready' && entry.feedback.length > 0) {
          y += 1;
          ensureSpace(lineHeightMm(SMALL_FONT_SIZE) * 2);
          pdf.setFont('helvetica', 'bolditalic');
          pdf.setFontSize(SMALL_FONT_SIZE);
          pdf.text('Coach Feedback:', PAGE_MARGIN + INDENT, y);
          y += lineHeightMm(SMALL_FONT_SIZE);

          pdf.setFont('helvetica', 'italic');
          for (const fb of entry.feedback) {
            const fbPlain = stripMarkdown(fb);
            const fbLines: string[] = pdf.splitTextToSize(fbPlain, contentWidth - INDENT * 2);
            renderLines(fbLines, SMALL_FONT_SIZE, PAGE_MARGIN + INDENT * 2);
          }
        }
      }

      y += 2;
    }

    y += 4;
  }

  // Summary section
  if (summaryFeedback) {
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(SECTION_TITLE_FONT_SIZE);
    ensureSpace(lineHeightMm(SECTION_TITLE_FONT_SIZE) + 2);
    pdf.text('Session Summary', PAGE_MARGIN, y);
    y += lineHeightMm(SECTION_TITLE_FONT_SIZE) + 2;

    pdf.setDrawColor(180, 180, 180);
    pdf.line(PAGE_MARGIN, y, pageWidth - PAGE_MARGIN, y);
    y += 3;

    if (typeof summaryFeedback === 'string') {
      const plain = stripMarkdown(summaryFeedback);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(BODY_FONT_SIZE);
      const lines: string[] = pdf.splitTextToSize(plain, contentWidth);
      renderLines(lines, BODY_FONT_SIZE);
    } else {
      const sections = buildSections(summaryFeedback);
      for (const section of sections) {
        ensureSpace(lineHeightMm(HEADER_FONT_SIZE) + lineHeightMm(BODY_FONT_SIZE));
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(HEADER_FONT_SIZE);
        pdf.text(section.title, PAGE_MARGIN, y);
        y += lineHeightMm(HEADER_FONT_SIZE) + 1;

        const plain = stripMarkdown(section.body);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(BODY_FONT_SIZE);
        const lines: string[] = pdf.splitTextToSize(plain, contentWidth);
        renderLines(lines, BODY_FONT_SIZE);
        y += 4;
      }
    }
  }

  pdf.save(filename);
}
