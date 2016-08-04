from django.core.management.base import BaseCommand
#from monitoringsite.gangamon.models import *
from monitoringsite.gangamon.eventproc import *

import stomp
import time
import sys
import ssl
import traceback
import os.path
import logging.handlers
import datetime

stomp_logger = logging.getLogger('stomp.py')
stomp_logger.setLevel(logging.DEBUG) 
stomp_handler = logging.handlers.RotatingFileHandler('/data/gangamon/dashboard/service/logs/runcollector_stomp.log', maxBytes=1000000, backupCount=3)
stomp_logger.addHandler(stomp_handler)

logger = logging.getLogger('runcollector')

should_stop = False

PRODUCTION_MODE = False
LOGPATH = '.'
DATAPATH = '.'

class Command(BaseCommand):
    help = "Runs the collector for Ganga and Diane. By default uses test queues. To run in production mode specify production argument."

    requires_model_validation = True 

    def __init__(self):
        super(Command, self).__init__()
        self.connections = []

    def handle(self, *args, **options):
        global PRODUCTION_MODE,LOGPATH,DATAPATH
        global should_stop

        PRODUCTION_MODE = False
        LOGPATH='/data/gangamon/dashboard/service/logs'
        DATAPATH='/data/gangamon/dashboard/data'
        try:
            if args[0] == 'production':
                PRODUCTION_MODE = True
                LOGPATH='/data/gangamon/dashboard/service/logs'
                DATAPATH='/data/gangamon/dashboard/data'
        except IndexError:
            PRODUCTION_MODE = False
        #    LOGPATH='.'
        #    DATAPATH='.'


        loghandler = logging.handlers.RotatingFileHandler(os.path.join(LOGPATH,'runcollector_master.log'), maxBytes=1000000, backupCount=3)
        logger.addHandler(loghandler)
        loghandler.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(message)s"))
        logger.setLevel(logging.DEBUG)

        HEARTBEAT_FILE = os.path.join(LOGPATH,'runcollector.heartbeat.txt')

        def update_heartbeat_file(t=None):
            if not t:
                t = time.time()
            f = file(HEARTBEAT_FILE,'w')
            f.write(str(t)+'\n')
            f.close()

        if PRODUCTION_MODE:    
            print "RUNNING IN PRODUCTION MODE"
            import socket
            msghosts = socket.gethostbyname_ex('dashb-mb.cern.ch')[2]
            #msghosts, port = ["gridmsg107.cern.ch", "gridmsg108.cern.ch"], 6162
            #msghosts = ["gridmsg107.cern.ch", "gridmsg108.cern.ch"]
            port = 61123 #6162
        else:    
            print "RUNNING IN TEST MODE"
            #msghosts, port = ["gridmsg007.cern.ch"], 6162
            import socket
            msghosts = socket.gethostbyname_ex('dashb-test-mb.cern.ch')[2]
            port = 61123 #6162

        print 'log created in:',loghandler.baseFilename
        for server in msghosts:
            loghandler = logging.handlers.RotatingFileHandler(os.path.join(LOGPATH,'runcollector_'+str(server)+'.log'), maxBytes=1000000, backupCount=3)
            print 'log created in:',loghandler.baseFilename
            logger.addHandler(loghandler)
            loghandler.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(message)s"))
            logger.setLevel(logging.DEBUG)
            logger.info('starting collector %s %d',server, port) 
            logger.info('Production mode is %s',PRODUCTION_MODE)


            def prodstr(s): # testing: rather than changing the queue names, we now use a development server with the same queue names
                return s
        
            # From Ganga 5.4.1 messages are sent to /queue/ganga.status (used to be /topic/ganga.status)

            self.add_listener(GangaListener(), server, port, [prodstr('/queue/ganga.status')])
            self.add_listener(DianeListener(), server, port, [prodstr('/queue/diane.journal'), prodstr('/queue/diane.status')])

            #this should be refactores and put into gangausage app
            self.add_listener(GangaUsageListener(), server, port, [prodstr('/queue/ganga.usage')])

            self.add_listener(GangaJobSubmittedListener(), server, port, [prodstr('/queue/ganga.jobsubmission')])
        
            # 20091104: we continue to listen to /queue/ganga.status.uat so we know
            # which users to inform to turn off UAT09 AthenaMSGMS monitoring service
            #self.add_listener(GangaUat09Listener(), server, port, [prodstr('/queue/ganga.status.uat')])

        last_heartbeat_log = 0
        while not should_stop:
            if os.path.exists(os.path.join(LOGPATH,'kill')):
                logger.critical('exiting, kill file found in %s',LOGPATH)
                print 'exiting, kill file found in ',LOGPATH
                should_stop = True
                for (c, ts) in self.connections:
                    c.stop()
                break
                
            if time.time()-last_heartbeat_log > 5*60: # every five minutes
                logger.info('still listening...')
                last_heartbeat_log = time.time()
                update_heartbeat_file(last_heartbeat_log)
                
            for (c, ts) in self.connections: # make sure connections are active
                try:
                    if not c.is_connected():
                        logger.info("%s connection not active; restarting...",c.__class__.__name__)
                        c.start()
                        c.connect()
                        for t in ts: # re-subscribe to topics
                            c.subscribe(destination=ts, ack='auto')
                        logger.info('%s connected!', c.__class__.__name__)
                except (stomp.NotConnectedException, stomp.ConnectionClosedException):
                    logger.exception('%s connection error; attempting to reconnect...', c.__class__.__name__)
                # sleep
                time.sleep(1)
        time.sleep(3)
        sys.exit(-1)
        
    def add_listener(self, listener, server, port, topics):
        connection = stomp.Connection( host_and_ports=[(server, port)],
                                       use_ssl = True, user='ganagmon',
                                       ssl_key_file = '/etc/grid-security/hostkey.pem',
                                       ssl_cert_file = '/etc/grid-security/hostcert.pem',
                                       ssl_version = ssl.PROTOCOL_TLSv1_2 )
        connection.set_listener(listener.__class__.__name__,listener)
        connection.start()
        connection.connect()
        for t in topics:
            connection.subscribe(destination=t, ack='auto')
        self.connections.append((connection, topics))
        logger.info('added listener %s, %s, %d, %s',listener.__class__.__name__,server,port,topics)


class GangaListener(stomp.ConnectionListener):
    
    def __init__(self):
        self.p = GangaEventProcessor()
        logger.info('gangaeventprocessor() created')
        
    def on_error(self, headers, body):
        logger.error('ERROR: %s, %s', repr(headers), body)

    def on_message(self, headers, body):
        try:
            logger.info('Ganga message %s %s', repr(headers), body)

            msg = eval(body)
            msg['_msg_t'] = headers['timestamp']
            try:
                _msg_t, event = str(int(msg['_msg_t'])/1000), msg['event']
            except KeyError:
                logger.exception('no timestamp in message')
                raise
            try:
                del msg['event']
            except KeyError:
                logger.exception('no event key in the message')
                raise

            data = [_msg_t, event, msg]
            #print repr(data)
            
            self.p.process_event(data)
            
        except MemoryError,e:
            logger.exception('I WILL STOP THE COLLECTOR NOW! At message: %s %s', headers, body)
            global should_stop
            should_stop = True
        except Exception, e:
            logger.exception('INVALID MESSAGE %s %s', headers, body)


class GangaUat09Listener(GangaListener):
    """Ganga UAT09 listener which extends GangaListener by logging all message
    bodies to a log file, which is saved with a date-time suffix, once an hour.
    """
    def __init__(self):
        GangaListener.__init__(self)
        import logging.handlers
        self.logger = logging.getLogger('uat09')
        handler = logging.handlers.TimedRotatingFileHandler('/data/uat09/message.log', when='H', interval=6)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        
    def on_message(self, headers, body):
        """Log message body to /data/uat09/message.log and call
        GangaListener.on_message().
        """
        self.logger.info(body)
        GangaListener.on_message(self, headers, body)
    

class DianeListener(stomp.ConnectionListener):
    """Diane listener which writes message contents to a database."""

    def __init__(self):
        self.p = DianeEventProcessor()
        
    def on_error(self, headers, body):
        logger.error('ERROR: %s, %s',repr(headers), body)

    def on_message(self, headers, body):
        try:
            logger.info('DIANE message %s %s', repr(headers), body)
            #print repr(data)
            msg = eval(body)
            msg['_msg_t'] = headers['timestamp']
            try:
                _msg_t, event = str(int(msg['_msg_t'])/1000), msg['event']
            except KeyError:
                logger.exception()
            try:
                del msg['event']
            except KeyError:
                logger.exception()
            data = [_msg_t, event, msg]
            self.p.process_event(data)
        except MemoryError,e:
            logger.exception('I WILL STOP THE COLLECTOR NOW! At message: %s %s', headers, body)
            global should_stop
            should_stop = True
        except Exception, e:
            logger.exception('INVALID MESSAGE %s %s', headers, body)


# this should be refactored into gangausage app!
from monitoringsite.gangausage.models import GangaSession, GangaJobSubmitted

class GangaUsageListener(stomp.ConnectionListener):
    def __init__(self):
        import logging.handlers
        self.logger = logging.getLogger('gangausage.emergency')
        backup_log_path = os.path.join(DATAPATH,'ganga.usage.emergency.log')
        handler = logging.handlers.RotatingFileHandler(backup_log_path, maxBytes=50000000) #50MB
        logger.info('storing usage events in a backup log: %s',backup_log_path)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        
    def on_message(self, headers, body):
        try:
            # save to a file first, for safety
            self.logger.info(body)
            # insert into DB
            params = eval(body)
            s = GangaSession()
            s.time_start = int(params['start'])/1000.0
            s.session_type = params['session']
            s.version = params['version']
            s.host  = params['host']
            s.user = params['user']
            s.runtime_packages = params['runtime_packages']

            try:
                s.interactive = params['interactive']
                s.GUI = params['GUI']
                s.webgui = params['webgui']
                s.text_shell = params['text_shell']
                s.script_file = params['script_file']
                s.test_framework = params['test_framework']
            except KeyError:
                pass #that's fine - an older Ganga version without new, extended attributes            

            s.save()
        except MemoryError,e:
            logger.exception('I WILL STOP THE COLLECTOR NOW! At message: %s %s', headers, body)
            global should_stop
            should_stop = True            
        except Exception,e:
            logger.exception('INVALID MESSAGE %s %s', headers, body)

    def on_error(self, headers, body):
        logger.error('ERROR: %s, %s',repr(headers), body)
                
class GangaJobSubmittedListener(stomp.ConnectionListener):
    def __init__(self):
        import logging.handlers
        self.logger = logging.getLogger('gangajobsubmitted.emergency')
        backup_log_path = os.path.join(DATAPATH,'ganga.jobsubmitted.emergency.log')
        handler = logging.handlers.RotatingFileHandler(backup_log_path, maxBytes=50000000) #50MB
        logger.info('storing job submitted events in a backup log: %s',backup_log_path)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        
    def on_message(self, headers, body):
        try:
            # save to a file first, for safety
            self.logger.info(body)
            # insert into DB
            params = eval(body)
            msg_date = datetime.datetime.fromtimestamp(int(params['start'])/1000.0).date()

            job_submitted = GangaJobSubmitted.objects.filter(date=msg_date, user=params['user'], host=params['host'], application=params['application'], backend=params['backend'])

            if len(job_submitted) == 0:
                job_submitted_new = GangaJobSubmitted()
                job_submitted_new.application = params['application']
                job_submitted_new.backend = params['backend']
                job_submitted_new.host = params['host']
                job_submitted_new.user = params['user']
                job_submitted_new.date = msg_date
                job_submitted_new.plain_jobs = int(params['plain_job'])
                job_submitted_new.master_jobs = int(params['master_job'])
                job_submitted_new.sub_jobs = int(params['sub_jobs'])

                try:
                    job_submitted_new.runtime_packages = params['runtime_packages']
                except KeyError:
                    pass #that's fine, older ganga version is used

                job_submitted_new.save()
            else:
                job_submitted[0].plain_jobs += int(params['plain_job'])
                job_submitted[0].master_jobs += int(params['master_job'])
                job_submitted[0].sub_jobs += int(params['sub_jobs'])
                job_submitted[0].save()
        
        except Exception,e:
            logger.exception('INVALID MESSAGE %s %s', headers, body)

    def on_error(self, headers, body):
        logger.error('ERROR: %s, %s',repr(headers), body)

