import { TestBed } from '@angular/core/testing';

import { ChatGraph } from './chat-graph';

describe('ChatGraph', () => {
  let service: ChatGraph;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChatGraph);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
