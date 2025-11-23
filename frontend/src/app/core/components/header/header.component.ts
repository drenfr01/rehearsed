import { Component, DestroyRef, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-header',
  imports: [
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

  // Navigation routes
  routes = [
    { path: '/app/scenario-selection', label: 'Scenario Selection' },
    { path: '/app/scenario-overview', label: 'Scenario Overview' },
    { path: '/app/classroom', label: 'Classroom' }
  ];

  // Admin routes
  adminRoutes = [
    { path: '/app/admin', label: 'Admin Dashboard' }
  ];

  getTruncatedSessionId(): string {
    const sessionToken = this.token();
    if (!sessionToken) return '';
    // Show first 8 and last 4 characters
    if (sessionToken.length <= 12) return sessionToken;
    return `${sessionToken.slice(0, 8)}...${sessionToken.slice(-4)}`;
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
