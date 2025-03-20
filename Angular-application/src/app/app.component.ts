import { Component } from '@angular/core';
import { RestaurantListComponent } from './restaurant-list/restaurant-list.component'; // Import the other component
import { CommonModule } from '@angular/common'; // Import CommonModule

@Component({
  selector: 'app-root',
  standalone: true, // Make sure it's standalone
  imports: [RestaurantListComponent, CommonModule], // Import the component and common module
  templateUrl: './app.component.html',
  styleUrls: [],
})
export class AppComponent {
  title = 'restaurant-app';
}