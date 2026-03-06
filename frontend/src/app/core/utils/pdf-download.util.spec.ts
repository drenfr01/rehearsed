import { downloadFeedbackAsPdf, pdfDeps } from './pdf-download.util';
import { SummaryFeedbackResponse } from '../models/chat-graph.model';

describe('downloadFeedbackAsPdf', () => {
  let mockPdf: jasmine.SpyObj<any>;

  const structuredFeedback: SummaryFeedbackResponse = {
    lesson_summary: 'The lesson covered **active listening** techniques.',
    key_moments: '- Student paraphrased correctly\n- Good eye contact',
    overall_feedback: 'Great job overall.',
    your_strengths: 'Empathy and patience.',
    areas_for_growth: 'Try asking more open-ended questions.',
    next_steps: '1. Practice reflective listening\n2. Review materials',
    celebration: 'You completed the session!',
  };

  beforeEach(() => {
    mockPdf = jasmine.createSpyObj(
      'jsPDF',
      ['setFont', 'setFontSize', 'text', 'splitTextToSize', 'addPage', 'save'],
      {
        internal: {
          pageSize: { getWidth: () => 210, getHeight: () => 297 },
        },
      },
    );
    mockPdf.splitTextToSize.and.callFake((text: string) => text.split('\n'));
    spyOn(pdfDeps, 'createPdf').and.returnValue(mockPdf);
  });

  it('should do nothing when feedback is null', () => {
    downloadFeedbackAsPdf(null);
    expect(pdfDeps.createPdf).not.toHaveBeenCalled();
  });

  it('should create a PDF and save with the given filename', () => {
    downloadFeedbackAsPdf(structuredFeedback, 'my-report.pdf');
    expect(pdfDeps.createPdf).toHaveBeenCalled();
    expect(mockPdf.save).toHaveBeenCalledWith('my-report.pdf');
  });

  it('should use default filename', () => {
    downloadFeedbackAsPdf(structuredFeedback);
    expect(mockPdf.save).toHaveBeenCalledWith('session-feedback.pdf');
  });

  it('should render the title "Session Summary"', () => {
    downloadFeedbackAsPdf(structuredFeedback);
    const textCalls = mockPdf.text.calls.allArgs();
    const titleCall = textCalls.find(
      (args: any[]) => args[0] === 'Session Summary',
    );
    expect(titleCall).toBeTruthy();
  });

  it('should render all section headers for structured feedback', () => {
    downloadFeedbackAsPdf(structuredFeedback);
    const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
    expect(textCalls).toContain('Lesson Summary');
    expect(textCalls).toContain('Key Moments');
    expect(textCalls).toContain('Overall Feedback');
    expect(textCalls).toContain('Your Strengths');
    expect(textCalls).toContain('Areas for Growth');
    expect(textCalls).toContain('Next Steps');
    expect(textCalls).toContain('Celebration');
  });

  it('should strip markdown from section body text', () => {
    downloadFeedbackAsPdf(structuredFeedback);
    const splitCalls = mockPdf.splitTextToSize.calls.allArgs().map((a: any[]) => a[0]);
    const lessonText = splitCalls.find((t: string) =>
      t.includes('active listening'),
    );
    expect(lessonText).toBeTruthy();
    expect(lessonText).not.toContain('**');
  });

  it('should handle plain string feedback', () => {
    downloadFeedbackAsPdf('Some **markdown** feedback text.');
    expect(mockPdf.save).toHaveBeenCalledWith('session-feedback.pdf');
    const splitCalls = mockPdf.splitTextToSize.calls.allArgs().map((a: any[]) => a[0]);
    const bodyText = splitCalls.find((t: string) => t.includes('markdown'));
    expect(bodyText).not.toContain('**');
  });

  it('should skip sections with empty body text', () => {
    const partial: SummaryFeedbackResponse = {
      ...structuredFeedback,
      celebration: '',
      next_steps: '   ',
    };
    downloadFeedbackAsPdf(partial);
    const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
    expect(textCalls).not.toContain('Celebration');
    expect(textCalls).not.toContain('Next Steps');
  });
});
