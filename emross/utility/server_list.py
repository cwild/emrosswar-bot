import sys

sys.path.extend(['lib/', 'lib/urllib3/'])

import simplejson
import urllib3

def main():
    master = 'm.emrosswar.com'
    naming = 'naming.php'

    pool = urllib3.PoolManager()

    servers = []

    i = 1
    while True:
        try:
            s = 'http://%s/%s?s=s%d.emrosswar.com' % (master, naming, i)
            r = pool.request('GET', s, headers={'User-Agent': ''})

            jsonp = r.data
            jsonp = jsonp[ jsonp.find('(')+1 : jsonp.rfind(')')]

            json = simplejson.loads(jsonp)

            if json['ret'] is None:
                i -= 1
                break

            server = json['ret']
            servers.append(server)

            print 'PvE %d: %s' % (i, server)
            i += 1

        except (urllib3.exceptions.HTTPError, ValueError), e :
            break


    uservers = set(s for s in servers)
    summary = [(s, servers.count(s)) for s in uservers]
    summary.sort()

    print 'There are %d original servers in total, making up %d actual worlds.' % (i, len(summary))
    print 'Below are the names of the Worlds and how many servers each of these is comprised of.'

    for s in summary:
        print '%s: %d' % s

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print '\nExecution finished'
