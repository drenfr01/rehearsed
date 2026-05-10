import { downloadFeedbackAsPdf, pdfDeps } from './pdf-download.util';
import { SummaryFeedbackResponse, Message, InlineFeedbackEntry } from '../models/chat-graph.model';

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
      ['setFont', 'setFontSize', 'text', 'splitTextToSize', 'addPage', 'save', 'setDrawColor', 'line'],
      {
        internal: {
          pageSize: { getWidth: () => 210, getHeight: () => 297 },
        },
      },
    );
    mockPdf.splitTextToSize.and.callFake((text: string) => text.split('\n'));
    spyOn(pdfDeps, 'createPdf').and.returnValue(Promise.resolve(mockPdf));
  });

  it('should do nothing when feedback is null (legacy call)', async () => {
    await downloadFeedbackAsPdf(null);
    expect(pdfDeps.createPdf).not.toHaveBeenCalled();
  });

  it('should handle legacy string feedback call', async () => {
    await downloadFeedbackAsPdf('Some **markdown** feedback text.');
    expect(mockPdf.save).toHaveBeenCalledWith('session-feedback.pdf');
  });

  it('should handle legacy structured feedback call', async () => {
    await downloadFeedbackAsPdf(structuredFeedback, 'my-report.pdf');
    expect(pdfDeps.createPdf).toHaveBeenCalled();
    expect(mockPdf.save).toHaveBeenCalledWith('my-report.pdf');
  });

  it('should render section headers for structured feedback', async () => {
    await downloadFeedbackAsPdf({ summaryFeedback: structuredFeedback });
    const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
    expect(textCalls).toContain('Lesson Summary');
    expect(textCalls).toContain('Key Moments');
    expect(textCalls).toContain('Overall Feedback');
    expect(textCalls).toContain('Your Strengths');
    expect(textCalls).toContain('Areas for Growth');
    expect(textCalls).toContain('Next Steps');
    expect(textCalls).toContain('Celebration');
  });

  it('should strip markdown from section body text', async () => {
    await downloadFeedbackAsPdf({ summaryFeedback: structuredFeedback });
    const splitCalls = mockPdf.splitTextToSize.calls.allArgs().map((a: any[]) => a[0]);
    const lessonText = splitCalls.find((t: string) => t.includes('active listening'));
    expect(lessonText).toBeTruthy();
    expect(lessonText).not.toContain('**');
  });

  it('should skip sections with empty body text', async () => {
    const partial: SummaryFeedbackResponse = {
      ...structuredFeedback,
      celebration: '',
      next_steps: '   ',
    };
    await downloadFeedbackAsPdf({ summaryFeedback: partial });
    const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
    expect(textCalls).not.toContain('Celebration');
    expect(textCalls).not.toContain('Next Steps');
  });

  describe('with transcript', () => {
    const transcript: Message[] = [
      { role: 'user', content: 'What is slope?', turnId: 'turn-1' },
      { role: 'assistant', content: 'Slope is the steepness of a line.', student_name: 'Maria' },
      { role: 'user', content: 'Good answer, Maria!', turnId: 'turn-2' },
    ];

    const inlineFeedback: InlineFeedbackEntry[] = [
      { turnId: 'turn-1', feedback: ['Nice open-ended question.'], status: 'ready' },
      { turnId: 'turn-2', feedback: ['Good positive reinforcement.'], status: 'ready' },
    ];

    it('should render transcript role labels', async () => {
      await downloadFeedbackAsPdf({
        summaryFeedback: structuredFeedback,
        transcript,
        inlineFeedback,
      });
      const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
      expect(textCalls).toContain('Teacher:');
      expect(textCalls).toContain('Student (Maria):');
    });

    it('should render conversation and session summary section titles', async () => {
      await downloadFeedbackAsPdf({
        summaryFeedback: structuredFeedback,
        transcript,
      });
      const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
      expect(textCalls).toContain('Conversation');
      expect(textCalls).toContain('Session Summary');
    });

    it('should render coach feedback labels for user turns', async () => {
      await downloadFeedbackAsPdf({
        summaryFeedback: structuredFeedback,
        transcript,
        inlineFeedback,
      });
      const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
      const coachLabels = textCalls.filter((t: string) => t === 'Coach Feedback:');
      expect(coachLabels.length).toBe(2);
    });

    it('should render transcript without inline feedback when none provided', async () => {
      await downloadFeedbackAsPdf({
        summaryFeedback: null,
        transcript,
      });
      const textCalls = mockPdf.text.calls.allArgs().map((a: any[]) => a[0]);
      expect(textCalls).toContain('Teacher:');
      expect(textCalls).not.toContain('Coach Feedback:');
    });
  });
});
