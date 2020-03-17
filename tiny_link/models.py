from django.db import models
import string

_char_map = [x for x in string.ascii_letters+string.digits]

def index_to_char(sequence):
    return "".join([_char_map[int(x)] for x in sequence])


class Link(models.Model):
    link = models.URLField(primary_key=True)
    # Store the total redirects here so we don't need to do a possibly expensive SUM query on HitsDatePoint
    shortLink = models.URLField()
    expiry = models.DateTimeField()

    def __repr__(self):
        return "<Link : %s>"%(self.link)


class HitsDatePoint(models.Model):
    day = models.DateField(auto_now=True, db_index=True)
    hits = models.IntegerField(default=0)
    link = models.ForeignKey(Link, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("day", "link"),)