import { Component, OnInit } from '@angular/core';
import { RestaurantService } from '../restaurant.service';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';

interface Restaurant {
  id: number;
  name: string;
  cuisine: string;
  rating: number;
}

@Component({
  selector: 'app-restaurant-list',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  templateUrl: './restaurant-list.component.html',
  styleUrls: ['./restaurant-list.component.css'],
})
export class RestaurantListComponent implements OnInit {
  restaurants: Restaurant[] = [];

  constructor(private restaurantService: RestaurantService) {}

  ngOnInit(): void {
    // No initial fetch here
  }

  fetchRestaurants(): void {
    this.restaurantService.getRestaurants().subscribe((restaurants) => {
      console.log('API Response:', restaurants); // Add console log
      this.restaurants = restaurants;
    });
  }
}