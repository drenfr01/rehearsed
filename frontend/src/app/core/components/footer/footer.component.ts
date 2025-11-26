import { Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-footer',
  imports: [
    RouterModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './footer.html',
  styleUrl: './footer.css',
})
export class Footer {
  private authService = inject(AuthService);
  isLoggedIn = this.authService.isLoggedIn;
  
  currentYear = new Date().getFullYear();
  
  footerLinks = [
    { path: '/about', label: 'About', icon: 'info' },
    { path: '/contact', label: 'Contact', icon: 'email' }
  ];
}
