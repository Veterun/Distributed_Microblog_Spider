__author__ = 'multiangle'
"""
    NAME:       server.py
    PY_VERSION: python3.4
    FUNCTION:
    This server part of distrubuted microblog spider.
    The function of server can be divided into 3 parts.
    1.  proxy manager.  Scratch web page in high speed need a lot of http proxy ip.
    Server should maintain a proxy pool which should provide proxy to client.
    2.  task manager.   Client will require task from server. task list should fetched
    from sqlserver and stored in memory
    3.  store return info.  When client finished searching user information from sina,
    client will return this info to server. if the length of data is too lang, client
    will seperate it into several parts and send then individually. Server should combine
    these data package together.
        Besides, server should check whether the received user is already exist in database.
    Server has to assure that no repeating data exists in database. It a heavy task for
    server to connect with databases.

    VERSION:    _0.1_

    UPDATE_HISTORY:
        _0.1_:  The 1st edition
"""
#======================================================================
#----------------import package--------------------------
# import python package
import threading

# import from outer package
import tornado.web
import tornado.ioloop
import tornado.options
from tornado.options import define,options

# import from this folder
from server_proxy import proxy_pool,proxy_manager
import server_config as config
import File_Interface as FI
from DB_Interface import MySQL_Interface
#=======================================================================
define('port',default=8000,help='run on the given port',type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers=[
            (r'/auth',AuthHandler),
            (r'/proxy/',ProxyHandler),
            (r'/task',TaskHandler),
            (r'/proxy_size',ProxySize),
            (r'/proxy_empty',ProxyEmpty),
            (r'/proxy_return',ProxyReturn),
            (r'/info_return',InfoReturn)
        ]
        settings=dict(
            debug=True
        )
        tornado.web.Application.__init__(self,handlers,**settings)

class AuthHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('connection valid')
        self.finish()

class ProxyHandler(tornado.web.RequestHandler):
    def get(self):
        global proxy
        num=int(self.get_argument('num'))
        if num>proxy.size():
            self.write('no valid proxy')
            self.finish()
        else:
            proxy_list=proxy.get(num)
            proxy_list=['{url},{timedelay};'.format(url=x[0],timedelay=x[1]) for x in proxy_list]
            res=''
            for i in proxy_list: res+=i
            res=res[0:-1]       # 'url,timedelay;url,timedelay;...,'
            self.write(res)
            self.finish()

class TaskHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('1221171697,connect')
        self.finish()

class ProxySize(tornado.web.RequestHandler):
    global proxy
    def get(self):
        self.write(str(proxy.size()))
        self.finish()

class ProxyEmpty(tornado.web.RequestHandler):
    global proxy
    def get(self):
        proxy.empty()
        if proxy.size()<2:
            self.write('empty proxy success')
            self.finish()

class ProxyReturn(tornado.web.RequestHandler):
    def post(self):
        global  proxy
        data=self.get_argument('data')
        proxy_list=data.split(';')
        in_data=[x.split(',') for x in proxy_list]
        proxy.add(in_data)
        self.write('return success')
        self.finish()

class InfoReturn(tornado.web.RequestHandler):
    def post(self):
        user_basic_info=self.get_argument('user_basic_info')
        attends=self.get_argument('user_attends')
        try:
            user_basic_info=eval(user_basic_info)
            attends=eval(attends)

            dbi=MySQL_Interface()

            if attends.__len__()>0:           #store attends info
                col_info=dbi.get_col_name('cache_attends')
                keys=attends[0].keys()
                attends= [[line[i] if i in keys else '' for i in col_info] for line in attends]
                dbi.insert_asList('cache_attends',attends)
            else:
                pass

            col_info=dbi.get_col_name('cache_user_info')    # store user basic info
            keys=user_basic_info.keys()
            data=[user_basic_info[i] if i in keys else '' for i in col_info]
            dbi.insert_asList('cache_user_info',[data])

            if attends.__len__()>0:            # store atten connection web
                user_uid=user_basic_info['uid']
                data=[[user_uid,x['uid']] for x in attends]
                dbi.insert_asList('cache_atten_web',data)
            else:
                pass

            self.write('success to return user info')
            self.finish()
        except:
            self.write('fail to return user info')
            self.finish()

if __name__=='__main__':
    proxy_lock=threading.Lock()
    global proxy
    proxy=proxy_pool()
    pm=proxy_manager(proxy,proxy_lock)
    pm.start()

    tornado.options.parse_command_line()
    Application().listen(options.port)
    tornado.ioloop.IOLoop.instance().start()