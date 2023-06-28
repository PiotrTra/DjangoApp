from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('aboutus/', views.about_us, name='about_us'),
    path('contact/', views.contact, name='contact'),
    path('contact-form/', views.contact_form, name='contact-form'),
    path('contact-form/mail-send/', views.contact_form_send_email, name='send_email'),
    path('repertoires/', views.repertoires, name='repertoires'),
    path('film/<int:movie_id>/', views.film_details, name='film_detail'),
    path('film/<int:movie_id>/show=<str:movie_show_id>/', views.ticket_create, name='ticket_create'),
    path('film/<int:movie_id>/show=<str:movie_show_id>/finalize/', views.finalize_ticket, name='ticket_create_fin'),
    path('show=<str:movie_show_id>/ticket-finalize', views.ticket_creation, name='ticket_send'),
    path('promotion=<int:promotion_id>', views.promotion_details, name="promotion"),
]
