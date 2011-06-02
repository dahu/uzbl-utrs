#!/usr/bin/env python2
import os
from sys import argv
import json
import socket
from datetime import datetime
import subprocess
import re

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            values = {}
            dt = {'__datetime__' : values}
            values['year'] = o.year
            values['month'] = o.month
            values['day'] = o.day
            values['hour'] = o.hour
            values['minute'] = o.minute
            values['second'] = o.second
            values['microsecond'] = o.microsecond
            values['tzinfo'] = o.tzinfo
            values['__string_repr__'] = o.isoformat()
            return dt
        else:
            return json.JSONEncoder.default(self, o)

def object_decoder(d):
    if '__datetime__' in d:
        o =  d['__datetime__']
        dt = datetime(o['year'], o['month'], o['day'], o['hour'], o['minute'], o['second'], o['microsecond'], o['tzinfo'])
        return dt
    return d

def fetch_queue():
    filename = os.environ['XDG_CONFIG_HOME'] + '/uzbl/article_queue'
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        qfile = open(filename)
        return json.load(qfile, object_hook=object_decoder)
    else:
        return []

def persist_queue(queue):
    filename = os.environ['XDG_CONFIG_HOME'] + '/uzbl/article_queue'
    qfile = open(filename, 'w')
    json.dump(queue, qfile, cls=JSONEncoder)

def create_url():
    return {'url' : os.environ['UZBL_URI'], 'title' : os.environ['UZBL_TITLE'], 'timestamp' : datetime.now()}

def push(queue):
    queue.insert(0, create_url())

def pop(queue, i):
    try: return queue.pop(i-1)
    except IndexError:
        fifo = open(os.environ['UZBL_FIFO'], "a")
        fifo.write('js alert("'+str(i)+': Queue doesn\'t have that many entries");\n')
        fifo.close()

def shift(queue):
    if len(queue) > 0:
        return queue.pop(-1)
    fifo = open(os.environ['UZBL_FIFO'], "a")
    fifo.write("js alert('Queue empty');\n")
    fifo.close()

def append(queue):
    queue.append(create_url())

def forward(queue):
    append(queue)
    return pop(queue, -1)

def back(queue):
    push(queue)
    return shift(queue)

def list_queue(queue):
    pos = 0
    qs = ""
    first = True
    for item in queue:
        pos += 1
        if not first:
            qs += "\n"
        first = False
        qs += str(pos) + ': ' + item['title']
    choice = subprocess.Popen(['echo "%s" | dmenu -i -l 10' % qs], shell=True, stdout=subprocess.PIPE).communicate()[0]
    if choice:
        index = int(re.search('^(\d+)', choice).group(1))
        url = pop(queue, index)
        persist_queue(queue)
        fifo = open(os.environ['UZBL_FIFO'], "a")
        fifo.write("uri " + url['url'] + "\n")
        fifo.close()

def write_fifo(url):
    fifo = open(os.environ['UZBL_FIFO'], "a")
    if url:
        fifo.write("uri " + url['url'] + "\n")
    else:
        fifo.write("exit\n")
    fifo.close()

def main():
    usage = "usage: "+argv[0]+" push|pop [x]|append|shift|forward|back|list"
    act=argv[1]
    queue = fetch_queue()
    url = None
    if act == "push":
        url = push(queue)
    elif act == "pop":
        try: url = pop(queue, int(argv[2]))
        except IndexError: url = pop(queue, 0)
    elif act == "shift":
        url = shift(queue)
    elif act == "append":
        url = append(queue)
    elif act == "list":
        list_queue(queue)
        return
    elif act == "forward":
        url = forward(queue)
    elif act == "back":
        url = back(queue)
    else:
        print usage
        exit(1)
    persist_queue(queue)
    write_fifo(url)

if __name__ == "__main__":
    main()
