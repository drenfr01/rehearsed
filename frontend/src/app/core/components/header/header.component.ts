import { Component, DestroyRef, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';

interface Scenario {
  id: string;
  name: string;
  path?: string;
}

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule
  ],
  templateUrl: './header.html',
  styleUrl: './header.css',
})
export class Header {
  private authService = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  private router = inject(Router);

  isLoggedIn = this.authService.isLoggedIn;
  token = this.authService.token;
  isAdmin = this.authService.isAdmin;
  isDropdownOpen = false;

  // Scenarios for dropdown
  scenarios: Scenario[] = [
    { id: '1', name: 'System of Linear Equations' },
    { id: '2', name: 'Negative Numbers' },
    { id: '3', name: 'Fractals' }
  ];

  // Navigation routes
  routes = [
    { path: '/app/scenario-selection', label: 'Scenario Selection' },
    { path: '/app/scenario-overview', label: 'Scenario Overview' },
    { path: '/app/classroom', label: 'Classroom' }
  ];

  toggleDropdown() {
    this.isDropdownOpen = !this.isDropdownOpen;
  }

  closeDropdown() {
    this.isDropdownOpen = false;
  }

  selectScenario(scenario: Scenario) {
    console.log('Selected scenario:', scenario);
    // Navigate to scenario or handle selection
    // this.router.navigate(['/app/scenario-selection', scenario.id]);
  }

  // Close dropdown when clicking outside
  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    const dropdown = target.closest('.scenario-dropdown');

    if (!dropdown && this.isDropdownOpen) {
      this.closeDropdown();
    }
  }

  logout() {
    this.authService.logout();
  }

  createSession() {
    const subscription = this.authService.createSession().subscribe({
      next: () => {
        this.router.navigate(['/app/scenario-selection'], { replaceUrl: true });
      },
      error: (error: Error) => {
        console.log(error.message);
      },
    });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }
}
