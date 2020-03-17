# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.template import Template, Context
from django.db.models import F
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from tiny_link import models
from django.http import HttpResponse
from ratelimit.decorators import ratelimit
import datetime
from django.utils.timezone import utc
import functools
from django.http import HttpResponseForbidden
import hashlib
from pylab import *
from django.core.cache import cache
import base64

def shrink(url):
    """
    For generating shortLinks for actual URLs
    """
    hashObject = hashlib.sha256(str(url).encode('utf-8'))
    fullUrl = hashObject.hexdigest()
    shrinked_url = fullUrl[:7]
    print(fullUrl)
    return shrinked_url


@ratelimit(key='ip', rate='100/m', block=True)
def home(request):
    """
    Home page view containing menu and options for shortening URLs
    """
    url_error = False
    url_input = ""
    shortened_url = ""
    shortLink = ""
    if request.method == "POST":
        validator = URLValidator()
        try:
            url_input = request.POST.get("url", None)
            if not url_input:
                url_error = True
            else:
                validator(url_input)
        except ValidationError:
            url_error = True

        if not url_error:
            try:
                link_db_obj = models.Link.objects.get(pk=url_input)
                print('link_db_obj',link_db_obj)
                if link_db_obj:
                    print('Long URL already exist')
                    expiry_db = link_db_obj.expiry
                    expiry = datetime.datetime.utcnow().replace(tzinfo=utc)
                    timediff = expiry - expiry_db
                    print(timediff.days)
                    if timediff.days < 30:
                        msg = 'Long URL is already tagged to a shortURL and it has not expired yet'
                        return render(request, "403_forbidden.html", {'msg': msg})
                    else:
                        expiry = datetime.datetime.utcnow().replace(tzinfo=utc)
                        shortLink = shrink(url_input)
                        shortened_url = request.build_absolute_uri(shortLink)
                        link_db_obj.expiry = expiry
                        link_db_obj.shortLink = shortLink
                        link_db_obj.save()
            except Exception as e:
                print ('URL does not exist')
                shortLink = shrink(url_input)
                shortened_url = request.build_absolute_uri(shortLink)
                expiry = datetime.datetime.utcnow().replace(tzinfo=utc)
                link_db_obj = models.Link.objects.filter(shortLink=shortLink)
                while( link_db_obj ):
                    shortLinkCharList = list(shortLink)
                    shortLinkCharList[-1] = chr((ord(shortLinkCharList[-1])+1)%256)
                    shortLink = ''.join(shortLinkCharList)
                    shortened_url = request.build_absolute_uri(shortLink)
                    print('New shortened url',shortened_url)
                    link_db_obj = models.Link.objects.get(shortLink=shortLink)
                    print(link_db_obj)
                    if link_db_obj:
                        expiry_db = link_db_obj.expiry
                        timediff = expiry - expiry_db
                        print('timediff',timediff)

                link_db = models.Link()
                link_db.link = url_input
                link_db.shortLink = shortLink
                link_db.expiry = expiry
                link_db.save()
                url_input = ""
                # shortened_url = "%s/%s"%(request.META["HTTP_HOST"], link_db.get_short_id())
                hits_db = models.HitsDatePoint()
                hits_db.day = datetime.date.today()
                hits_db.link = link_db
                hits_db.hits = 0
                hits_db.save()


    return render(request, "index.html",
                  {"error": url_error, "url": url_input, "shorturl": shortLink})


@ratelimit(key='ip', rate='100/m', block=True)
def link(request, id):
    """
    Responsible for redirecting shortURLs to longURLs and make changes to Hit count for the URL in database
    """
    print(id)
    link_db_row = get_object_or_404(models.Link, shortLink=id)
    print('link_db_row', link_db_row.link)

    #models.Link.objects.filter(id=db_id).update(hits=F('hits') + 1)  # Update the link hits
    #
    #if not models.HitsDatePoint.objects.filter(link=link_db, day=datetime.date.today()).exists():
    #     x = models.HitsDatePoint()
    #     x.day = datetime.date.today()
    #     x.link = link_db
    #     try:
    #         x.save()
    #     except Exception as e:
    #         print("Possible corruption: %s" % e)
    #models.HitsDatePoint.objects.filter( link=link_db_row.link).update(hits=F('hits') + 1)
    expiry_db = link_db_row.expiry
    expiry = datetime.datetime.utcnow().replace(tzinfo=utc)
    timediff = expiry - expiry_db
    if timediff.days > 30:
        msg = 'Long URL has expired since it was created more than 30 days ago'
        return render(request, "403_forbidden.html", {'msg': msg})
    today_hits = models.HitsDatePoint.objects.filter(day=datetime.date.today(), link=link_db_row)
    if not today_hits:
        HitsDatePoint_obj = models.HitsDatePoint()
        HitsDatePoint_obj.day = datetime.date.today()
        HitsDatePoint_obj.link = link_db_row
        HitsDatePoint_obj.hits = 1
        HitsDatePoint_obj.save()
    else:
        models.HitsDatePoint.objects.filter(day=datetime.date.today(), link=link_db_row).update(hits=F('hits') + 1)
    print('Hits updated')
    return redirect(link_db_row.link)


@ratelimit(key='ip', rate='100/m', block=True)
def stats(request, shortLink):
    """
    Statistic gathering logic for a shortURL
    """
    if not shortLink:
        return redirect(request.META["HTTP_HOST"]+ '/')
    print ('shortLink',shortLink)
    shorturl = 'http://' + request.META["HTTP_HOST"] + '/' + shortLink
    print ('shortLink:', shortLink)
    link_db = get_object_or_404(models.Link, shortLink=shortLink)

    stats = models.HitsDatePoint.objects.filter(day__gt=datetime.date.today() - datetime.timedelta(days=30),
                                                link=link_db).all()
    print(stats.values())
    stat_hits = list(obj['hits'] for obj in stats.values())
    stat_dates = list(str(obj['day']) for obj in stats.values())
    print(stat_hits, stat_dates)

    from matplotlib import pylab, pyplot as plt

    import PIL, PIL.Image
    from io import BytesIO

    degrees = 25
    plt.xticks(rotation=degrees)
    bar(stat_dates, stat_hits)

    xlabel('Date')
    ylabel('Hits')
    title('Days vs Hits')
    grid(False)

    # Store image in a string buffer
    buffer = BytesIO()
    canvas = pylab.get_current_fig_manager().canvas
    canvas.draw()
    pilImage = PIL.Image.frombytes("RGB", canvas.get_width_height(), canvas.tostring_rgb())
    pilImage.save(buffer, "PNG")

    content_type = "Image/png"
    bufferoutput = buffer.getvalue()

    #graphic = (bufferoutput, content_type)
    graphic = base64.b64encode(bufferoutput)
    graphic = graphic.decode('utf-8')
    pylab.close()

    #return HttpResponse(buffer.getvalue(), content_type="image/png")
    link_url = link_db.link
    return render(request,"stats.html", {"stats": stats, "link": link_db, "link_url": link_url, "graphic":graphic})


def allStats(request):
    """
    To view a list of longURLs and their corresponding shortURLs, and click to view statistic for a shortURL
    """
    #db_id = models.Link.decode_id(id)
    links = models.Link.objects.all()
    for link in links:
        link.shortLink = link.shortLink.split('/')[-1]
    return render(request, "allStats.html", {"links": links})
