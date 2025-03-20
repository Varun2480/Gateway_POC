import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { RestaurantService } from './restaurant.service';
import { AppRoutingModule } from './app-routing.module';

@NgModule({
  imports: [BrowserModule, HttpClientModule, AppRoutingModule, AppComponent], //import app component
  providers: [RestaurantService],
  bootstrap: [AppComponent],
})
export class AppModule {}