from datetime import date
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Address(models.Model):

    class Meta:
        verbose_name_plural = "Addresses"

    street = models.CharField(max_length=128)
    city = models.CharField(max_length=64)
    postal_code = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.street}, {self.city} {self.postal_code}"


def cinemas_count():
    return Cinema.objects.all().count()


class Cinema(models.Model):
    name = models.CharField(max_length=32)
    description = models.TextField(max_length=512)
    address = models.OneToOneField(Address, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}, location: {self.address}"

    def short__str__(self):
        return f"{self.name}, {self.address.street}"


def cinema_hall_count():
    return CinemaHall.objects.all().count()


class CinemaHall(models.Model):
    hall_number = models.CharField(max_length=4)
    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return str("Hall: " + str(self.hall_number) + ", Cinema: " + str(self.cinema))


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class Client(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=16)
    surname = models.CharField(max_length=32)
    date_of_birth = models.DateField()

    def __str__(self):
        return str(str(self.name) + " " + str(self.surname) + ", ur. " + str(self.date_of_birth))

    def clean(self):
        if calculate_age(self.date_of_birth) < 13:
            raise ValidationError("Musisz mieć minimum 13 lat")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class MovieCategory(models.Model):
    class Meta:
        verbose_name_plural = "Movie categories"

    name = models.CharField(max_length=32)
    description = models.CharField(max_length=512)

    def __str__(self):
        return self.name


def format_filename(instance_data):
    invalid_file_chars = [',', '.', '#', '<', '$', '+', '%', '>', '!', '`', '&', '*', '\'', '|', '{', '?', '\"', '=',
                          '}', '/', ':', '\\', '@', ' ']

    instance_data_formatted = instance_data

    for char in invalid_file_chars:
        instance_data_formatted = instance_data_formatted.replace(char, "-")

    return instance_data_formatted


def get_director_directory(instance, filename):

    filename_formatted = format_filename(instance.name+"_"+instance.surname)

    return settings.MEDIA_ROOT + '/directors-data/director_{0}/{1}'.format(filename_formatted, filename)


class Director(models.Model):
    name = models.CharField(max_length=32)
    surname = models.CharField(max_length=32)
    photo = models.ImageField(upload_to=get_director_directory, null=True, blank=True, max_length=512)

    def __str__(self):
        return str(self.name) + " " + str(self.surname)


def get_actors_directory(instance, filename):

    filename_formatted = format_filename(instance.name+"_"+instance.surname)

    return settings.MEDIA_ROOT + '/actors-data/actor_{0}/{1}'.format(filename_formatted, filename)


class Actor(models.Model):
    name = models.CharField(max_length=32)
    surname = models.CharField(max_length=32)
    as_name = models.CharField(max_length=32)
    as_surname = models.CharField(max_length=32,null=True,blank=True)
    photo = models.ImageField(upload_to=get_actors_directory, null=True, blank=True, max_length=512)

    def __str__(self):
        return str(self.name)+" "+str(self.surname)


def get_film_directory(instance, filename):

    filename_formatted = format_filename(instance.title)

    return settings.MEDIA_ROOT + '/films-data/film_{0}/{1}'.format(filename_formatted, filename)


class Movie(models.Model):
    GENERAL_AUDIENCE = 'G'
    PARENTAL_GUIDANCE_SUGGESTED = 'PG'
    PARENTS_STRONGLY_CAUTIONED = 'PG-13'
    RESTRICTED = 'R'
    ADULTS_ONLY = 'NC-17'

    Age_rating = (
        (GENERAL_AUDIENCE, "General Audiences"),
        (PARENTAL_GUIDANCE_SUGGESTED, "Parental Guidance Suggested"),
        (PARENTS_STRONGLY_CAUTIONED, "Parents Strongly Cautioned"),
        (RESTRICTED, "Restricted"),
        (ADULTS_ONLY, "Adults Only")
    )

    age_rating = models.CharField(max_length=32, choices=Age_rating, blank=False)
    film_category_id = models.ManyToManyField(MovieCategory)
    director = models.ManyToManyField(Director)
    actors = models.ManyToManyField(Actor)
    title = models.CharField(max_length=128)
    description = models.TextField(max_length=512, default="")
    duration = models.CharField(max_length=32)
    release_date = models.DateField()
    ticket_price = models.DecimalField(max_digits=5, decimal_places=2)
    poster = models.ImageField(upload_to=get_film_directory, null=True, max_length=512)
    film_trailer = models.URLField(null=True)

    def __str__(self):
        return str(self.title) + " (" + str(self.release_date.year) + ")"

    def get_movie_categories(self):
        movie_category = list(MovieCategory.objects.filter(movie=self.id).values("name"))
        return movie_category


class MovieShow(models.Model):
    date_of_show = models.DateTimeField()
    movie_id = models.ForeignKey(Movie, on_delete=models.CASCADE, null=True)
    cinema_hall_id = models.ForeignKey(CinemaHall, on_delete=models.CASCADE, null=True)
    language_version = models.CharField(max_length=128)
    movie_format = models.CharField(max_length=32, default="2D")
    additional_information = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return str(
            str(self.movie_id) + ", sala: " + str(self.cinema_hall_id) + ", data: " +
            str(self.date_of_show.strftime("%d-%m-%Y %H:%M:%S"))
        )

    def get_cinema_hall_name(self):
        return self.cinema_hall_id.name

    def clean(self):
        movie_show_list = MovieShow.objects.all()
        for element in movie_show_list:
            if element.date_of_show == self.date_of_show and element.cinema_hall_id == self.cinema_hall_id and element != self:
                raise ValidationError("Nie może być 2 seansów w tym samym miejscu i czasie")

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = True if not self.id else False
        super(MovieShow, self).save(*args, **kwargs)
        if is_new:
            for number in range(1, 18):
                for row in range(1, 14):
                    seat = SeatFromShow(row_num=row, seat_num=number, ticket_id=None, movie_show_id=self,
                                        client_considering=None)
                    seat.save()


class Ticket(models.Model):
    user_id = models.ForeignKey(Client, on_delete=models.CASCADE)
    buy_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Bilet dla " + str(self.user_id) + ", kupiony: " + str(self.buy_date.strftime("%Y-%m-%d %H:%M:%S"))


class SeatFromShow(models.Model):
    row_num = models.IntegerField()
    seat_num = models.IntegerField()
    ticket_id = models.ForeignKey(Ticket, null=True, blank=True, on_delete=models.SET_NULL)
    movie_show_id = models.ForeignKey(MovieShow, on_delete=models.CASCADE)
    client_considering = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str("Rząd: " + str(self.row_num) + " Numer: " +
                   str(self.seat_num) + ", film: " + str(self.movie_show_id)) + " " + str(self.ticket_id)

    def clean(self):
        if self.ticket_id is not None:
            self.is_seat_available = False

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Promotion(models.Model):
    name = models.CharField(max_length=64)
    movies = models.ManyToManyField(Movie, blank=True, null=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    discount_multiplier = models.DecimalField(max_digits=2, decimal_places=2, null=True,
                                                                    blank=True, validators=[MinValueValidator(0),
                                                                                            MaxValueValidator(1.00)])

    category = models.ForeignKey(MovieCategory, on_delete=models.CASCADE, null=True, blank=True)
    seat_count = models.IntegerField(null=True, blank=True)
    description = models.TextField(max_length=2048, blank=True)

    def __str__(self):
        return str(self.name) + " (" + str(self.start_date) + ":" + str(self.end_date) + ")"


def get_banner_directory(instance, filename):
    filename_formatted = format_filename(instance.__str__())

    return settings.MEDIA_ROOT + '/banners-data/{0}/{1}'.format(filename_formatted, filename)


class Banner(models.Model):
    image = models.ImageField(upload_to=get_banner_directory, null=True, blank=True, max_length=512)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, null=True, blank=True)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        if self.movie:
            return f"Baner filmu: {self.movie.title}"
        elif self.promotion:
            return f"Baner promocji: {self.promotion}"
        else:
            return "Baner"

    
