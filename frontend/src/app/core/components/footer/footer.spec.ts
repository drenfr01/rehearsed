import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Footer } from './footer.component';

describe('Footer', () => {
  let component: Footer;
  let fixture: ComponentFixture<Footer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Footer],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(Footer);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have the current year', () => {
    expect(component.currentYear).toBe(new Date().getFullYear());
  });

  it('should have footer links', () => {
    expect(component.footerLinks.length).toBe(2);
    expect(component.footerLinks[0].label).toBe('About');
    expect(component.footerLinks[1].label).toBe('Contact');
  });

  it('should have paths and icons for footer links', () => {
    for (const link of component.footerLinks) {
      expect(link.path).toBeTruthy();
      expect(link.icon).toBeTruthy();
    }
  });
});
