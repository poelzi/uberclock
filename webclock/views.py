# Create your views here.
# Create your views here.
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse
import datetime, os, re
from uberclock.db.models import Entry, Session

INDEX_PATH = os.path.join(os.path.dirname(__file__), 
                           "templates", "webclock", "index")

def get_clock_types():
    res = {}
    for item in os.listdir(INDEX_PATH):
        # read the content
        try:
            content = open(os.path.join(INDEX_PATH, item)).read()
        except IOError:
            continue
        match = re.search("webclock_name (.*)", content)
        if match:
            res[os.path.basename(item)] = match.group(1)
    return res


def index(request):
    types = get_clock_types()

    typ = request.COOKIES.get("webclock_clock", "simple.html")

    typ = request.GET.get("typ", typ)
    if not typ in types:
        typ = "simple.html"

    data = {"types": types,
            "current": typ,
           }

    ret = render_to_response('webclock/index/%s' %typ,
                              data,
                              context_instance=RequestContext(request))

    if request.COOKIES.get("webclock_clock", "simple.html") != typ:
        ret.set_cookie("webclock_clock", value=typ)

    return ret


def stats(request):
    now = datetime.datetime.now()
    data = {
        'now': now,
        'now_week': now.isocalendar()[1],
        'sessions': Session.objects.all().order_by("-id")
        }

    return render_to_response('stats.html',
                              data,
                              context_instance=RequestContext(request))

def stats_detail(request, session):
    now = datetime.datetime.now()
    sess = get_object_or_404(Session, id__exact=session)

    next = Session.objects.filter(id__exact=sess.id+1)
    if next: 
        next = next[0]
    else:
        next = None

    prev = Session.objects.filter(id__exact=sess.id-1)
    if prev: 
        prev = prev[0]
    else:
        prev = None


    data = {
        'prev': prev,
        'next': next,
        'now': now,
        'now_week': now.isocalendar()[1],
        'session': sess
        }

    return render_to_response('stats_detail.html',
                              data,
                              context_instance=RequestContext(request))


# file charts.py
def png_graph(request, session=None):
    import random
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter


    fig=Figure()
    ax=fig.add_subplot(111)
    x=[]
    y=[]

    if Session.objects.all().count():
        if session:
            sess = get_object_or_404(Session, id__exact=session)
        else:
            sess = Session.objects.all().order_by("-id")[0]

#     now=datetime.datetime.now()
#     delta=datetime.timedelta(days=1)
#     for i in range(10):
#         x.append(now)
#         now+=delta
#         y.append(random.randint(0, 1000))
        for entry in sess.entry_set.all():
            x.append(entry.date)
            y.append(entry.value)
    ax.plot_date(x, y, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    canvas=FigureCanvas(fig)
    response=HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response
