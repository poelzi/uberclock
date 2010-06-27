# Create your views here.
# Create your views here.
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
import datetime
from uberclock.db.models import Entry

def index(request):

    data = {}

    return render_to_response('index.html',
                              data,
                              context_instance=RequestContext(request))


# file charts.py
def sleep_stats(request):
    import random
    
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter

    fig=Figure()
    ax=fig.add_subplot(111)
    x=[]
    y=[]
#     now=datetime.datetime.now()
#     delta=datetime.timedelta(days=1)
#     for i in range(10):
#         x.append(now)
#         now+=delta
#         y.append(random.randint(0, 1000))
    for entry in Entry.objects.all():
        x.append(entry.date)
        y.append(entry.value)
    ax.plot_date(x, y, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    canvas=FigureCanvas(fig)
    response=HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response
