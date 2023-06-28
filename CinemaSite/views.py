import json
import random

from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import send_mail

import datetime

from django.utils import timezone
from background_task import background

from .models import *


def index(request):
    movie_ids = Movie.objects.values("id")
    current_user = request.user
    banners = Banner.objects.all()

    five_movie_ids = set()

    if len(movie_ids) > 0:
        if len(movie_ids) >= 5:
            while len(five_movie_ids) < 6:
                five_movie_ids.add(str(random.choice(movie_ids)["id"]))

    movie_list = Movie.objects.filter(pk__in=five_movie_ids)
    return render(request,
                  "main-site/main_page.html",
                  context={
                      "movie_list": movie_list,
                      "current_user": current_user,
                      "banners": banners,
                  })


def about_us(request):
    context = {
        "cinemas_count": cinemas_count(),
        "cinema_hall_count": cinema_hall_count(),
        "seats_count": cinema_hall_count()*13*17,
        "contact_email": settings.EMAIL_HOST_USER,
        "current_user": request.user
    }
    return render(request, "main-site/aboutus.html", context=context)


def contact(request):
    return render(request, "main-site/contact.html", context={"current_user": request.user})


def repertoires(request):
    movie_list = Movie.objects.all()
    categories_by_movie = []

    for movie in movie_list:
        categories_by_movie.append(movie.get_movie_categories())

    actor_list = Actor.objects.all()
    director_list = Director.objects.all()
    categories_list = MovieCategory.objects.all()
    return render(request,
                  "main-site/repertoires.html",
                  context={
                      "current_user": request.user,
                      "movie_list": movie_list,
                      "categories_by_movie": json.dumps(categories_by_movie),
                      "actor_list": actor_list,
                      "director_list": director_list,
                      "categories_list": categories_list
                  })


def contact_form(request):
    return render(request, "main-site/contact-form.html", context={"current_user": request.user})


def contact_form_send_email(request):
    if request.method == 'POST':
        sender_email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        send_mail(
            "[KONTAKT] " + subject,
            "[Wiadomość od: " + sender_email + "]\n" + message,
            sender_email,
            ['cinemaworld.eservice@gmail.com'],
            fail_silently=False,
        )

        return render(request,
                      "main-site/contact-form-send.html",
                      context={
                          "current_user": request.user,
                      })


def promotion_details(request, promotion_id):
    promotion = Promotion.objects.filter(pk=promotion_id)
    promotion_banner_img = Banner.objects.filter(promotion=promotion_id)

    return render(request,
                  "main-site/promotion.html",
                  context={
                      "current_user": request.user,
                      "promotion": promotion[0],
                      "banner": promotion_banner_img[0],
                  })


def film_details(request, movie_id):
    movie = Movie.objects.get(pk=movie_id)
    movie_categories = movie.film_category_id.all()
    movie_shows = MovieShow.objects.filter(
        movie_id=movie_id,
        date_of_show__gt=timezone.now(),
    ).order_by("date_of_show")

    actors = movie.actors.all()
    directors = movie.director.all()
    cinemas = Cinema.objects.all()

    context = {
        "cinemas": cinemas,
        "movie": movie,
        "movie_shows": movie_shows,
        "movie_category": movie_categories,
        "current_user": request.user,
        "actors": actors,
        "directors": directors
    }

    return render(request, "main-site/film-details.html", context=context)


def ticket_create(request, movie_id, movie_show_id):
    if request.user.is_authenticated:
        current_user = request.user
        try:
            movie = Movie.objects.get(pk=movie_id)
            movie_show = MovieShow.objects.get(pk=movie_show_id)
            list_of_seats = SeatFromShow.objects.filter(movie_show_id=movie_show_id).order_by('row_num', 'seat_num')
            max_row = SeatFromShow.objects.aggregate(Max('row_num'))['row_num__max']
            max_seat_num = SeatFromShow.objects.aggregate(Max('seat_num'))['seat_num__max']

            client = Client.objects.get(user=current_user.id)

            if is_ajax(request):
                data = json.load(request)
                load_data = data.get("load")
                check_seat = data.get("check")
                if load_data:
                    # clearing seat selection after refreshing page (F5)
                    for seat in list_of_seats:
                        if seat.client_considering == client:
                            seat.client_considering = None
                            seat.save()

                    return JsonResponse({"status": "ok", "seats_array": list(list_of_seats.values()),
                                         "max_row": max_row, "max_seat_num": max_seat_num}, status=200)
                elif check_seat:
                    seat_number = data.get("number")
                    seat_row = data.get("row")

                    seat = SeatFromShow.objects.get(row_num=seat_row + 1, seat_num=seat_number + 1,
                                                    movie_show_id=movie_show_id)
                    if seat.client_considering is None and seat.ticket_id is None:
                        seat.client_considering = client
                        seat.save()
                        # TUTAJ
                        remove_seat_occupation_without_ticket(movie_show.id, client.id, seat.id)
                        return JsonResponse({"seat_available": True}, status=200)
                    else:
                        if seat.client_considering == client and seat.ticket_id is None:
                            seat.client_considering = None
                            seat.save()
                            return JsonResponse({"seat_available": True}, status=200)
                        else:
                            return JsonResponse({"seat_available": False}, status=200)
                else:
                    return JsonResponse({"status": "not ok"}, status=200)
            else:
                context = {
                    "movie": movie,
                    "movie_show": movie_show,
                    "current_user": request.user
                }
                return render(request, "main-site/ticket-create.html", context=context)
        except Client.DoesNotExist:
            return HttpResponse("Jesteś zalogowany kontem admina, zaloguj się kontem klienta")
    else:
        return redirect('Accounts:login')


def finalize_ticket(request, movie_id, movie_show_id):
    current_user = request.user
    client = Client.objects.get(user=current_user.id)

    movie = Movie.objects.get(pk=movie_id)

    seats_taken = SeatFromShow.objects.filter(movie_show_id=movie_show_id, client_considering=client)
    ticket_cost = len(seats_taken)*movie.ticket_price

    movie_show = MovieShow.objects.filter(pk=movie_show_id)
    movie_show_date_time = movie_show[0].date_of_show
    # print(movie_show_date_time)

    promotions = Promotion.objects.filter(start_date__lt=movie_show_date_time, end_date__gt=movie_show_date_time)

    context = {
        "seats_taken": seats_taken,
        "base_ticket_cost": ticket_cost,
        "movie_show_id": movie_show_id,
        "current_user": request.user
    }
    # print("base:", ticket_cost)
    promotions_applied = []

    ticket_cost_after_promotion = ticket_cost

    for promotion in promotions:
        # print("P: ", promotion, " ", promotion.category)
        # print("start:", promotion.start_date, "end: ", promotion.end_date)
        discount = True
        if promotion.seat_count is not None:
            if len(seats_taken) >= promotion.seat_count:
                discount = True
            else:
                discount = False
                continue
        elif promotion.movies.all().count() > 0:
            # print(promotion.movies.all())
            if movie in promotion.movies.all():
                discount = True
            else:
                discount = False
                continue
        elif promotion.category is not None:
            # print(promotion.category)
            if promotion.category in movie.film_category_id.all():
                discount = True
            else:
                discount = False
                continue
        if discount:
            ticket_cost_after_promotion *= promotion.discount_multiplier
            promotions_applied.append(promotion.name)

    context.update({
        "promotions_applied": promotions_applied
    })

    if ticket_cost_after_promotion != ticket_cost:
        context.update({
            "ticket_cost": ticket_cost_after_promotion
        })

    return render(request, "main-site/ticket-create-finalize.html", context=context)


def ticket_creation(request, movie_show_id):
    current_user = request.user
    client = Client.objects.get(user=current_user.id)
    ticket = Ticket(user_id=client)
    ticket.save()
    movie_show = MovieShow.objects.get(pk=movie_show_id)

    seats_taken = SeatFromShow.objects.filter(movie_show_id=movie_show_id, client_considering=client)

    for seat in seats_taken:
        seat.ticket_id = ticket
        seat.save()

    subject = "Twój bilet czeka na Ciebie"
    message = "Witaj " + client.name + " dziękujemy za zakup biletu na seans: " + movie_show.movie_id.title + \
              "\nSeans odbędzie się w kinie " + movie_show.cinema_hall_id.cinema.short__str__() + \
              " w sali " + \
              movie_show.cinema_hall_id.hall_number + "\nTwoje miejsca: \n"

    for seat in seats_taken:
        message += "-miejsce " + str(seat.seat_num+1) + ", rząd " + str(seat.row_num+1) + "\n"

    message += "W razie gdybyś zapomniał, seans odbędzie się " + \
               movie_show.date_of_show.strftime("%d-%m-%Y %H:%M:%S") + "\nDo zobaczenia w kinie\nZespół CinemaWorld"

    email_from = settings.EMAIL_HOST_USER
    recipient_list = [str(current_user.email), ]
    send_mail(subject, message, email_from, recipient_list)

    return render(request, "main-site/ticket-confirmation-send.html", context={"current_user": request.user})


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


@background(schedule=60*5)
def remove_seat_occupation_without_ticket(movie_show_id, client_id, seat_id):
    list_of_seats = SeatFromShow.objects.filter(movie_show_id=movie_show_id, client_considering=client_id, pk=seat_id)

    for seat in list_of_seats:
        if seat.ticket_id is None:
            seat.client_considering = None
            seat.save()
