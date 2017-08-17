# coding=utf-8
__author__ = "hbw"

import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.options
from uuid import uuid4
import qrcode
import os
from tornado import iostream
from tornado.web import RequestHandler


def _has_stream_request_body(cls):
    if not issubclass(cls, RequestHandler):
        raise TypeError("expected subclass of RequestHandler, got %r", cls)
    return getattr(cls, '_stream_request_body', False)


class LongPoolRequestHandler(tornado.web.RequestHandler):
    def on_connection_close(self):

        if _has_stream_request_body(self.__class__):
            if not self.request.body.done():
                self.request.body.set_exception(iostream.StreamClosedError())
                self.request.body.exception()
            else:
                print "else 1"
        else:
            qrcode_pic_path = os.path.join("./static/qrcode", self.sid + ".png")
            # qrcode_file_path = self.application.qrcodeObj.
            os.remove(qrcode_pic_path)


class ClickStatusCallBackHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        sid = args[0]
        if sid:
            self.sid = sid
        if sid not in self.application.qrcodeObj.ids:
            self.write("error sid!")  # self.async_callback(
        self.application.qrcodeObj.click_register_callback(sid, self.on_message, self)

    def on_message(self):
        # self.redirect("static")
        self.application.qrcodeObj.click_callbacks[self.sid]["status"] = True
        # self.redirect("/static/index.html", True, 301)
        self.write("客户端成功点击成功，您的授权已经通过")
        self.finish()


class ClickHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        sid = args[0]
        if sid not in self.application.qrcodeObj.ids:
            self.write("error sid!")
        if sid not in self.application.qrcodeObj.click_callbacks:
            self.write("not in callbacks")
        func = self.application.qrcodeObj.click_callbacks[sid]["function"]
        self_obj = self.application.qrcodeObj.click_callbacks[sid]["self_obj"]
        status = self.application.qrcodeObj.click_callbacks[sid]["status"]
        if not status:
            func()
        # self.redirect("/static/helloworld.html", True, 301)
        # self.redirect("/static/index.html", True, 301)
        self.write("客户端成功点击成功，您的授权已经通过")


class ScanStatusCallBackHandler(LongPoolRequestHandler):
    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        sid = args[0]
        if sid:
            self.sid = sid
        if sid not in self.application.qrcodeObj.ids:
            self.write("error sid!")  # self.async_callback(
        self.application.qrcodeObj.scan_register_callback(sid, self.on_message, self)

    def on_message(self):
        self.write("客户端成功扫描，等待click操作！")
        self.application.qrcodeObj.scan_callbacks[self.sid]["status"] = True
        self.finish()


class ScanQrcodeHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        sid = args[0]
        if sid not in self.application.qrcodeObj.ids:
            self.write("error sid!")
        if sid not in self.application.qrcodeObj.scan_callbacks:
            self.write("not in callbacks")
        func = self.application.qrcodeObj.scan_callbacks[sid]["function"]
        self_obj = self.application.qrcodeObj.scan_callbacks[sid]["self_obj"]
        status = self.application.qrcodeObj.scan_callbacks[sid]["status"]
        if not status:
            func()
        self.redirect("/static/click.html?sid=" + sid, True, 301)


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        sid = self.application.get_qrcode()
        ret_obj = self.application.qrcodeObj.ids[sid]
        self.write(ret_obj)
        # self.render("qrcode_index.html", qrcode_url=qrcode_url, qrcode_status=qrcode_status)


class QrCode(object):
    def __init__(self):
        self.base_url = "http://10.1.1.120:8000/"
        self.ids = {}
        self.scan_callbacks = {}
        self.click_callbacks = {}
        self.qrcode_pic_dir = "/Users/Grubby/Documents/pythonep/tornado_project/tornado_long_poll_oauth/static/qrcode"
        self.web_base_url = self.base_url + "static/qrcode/"
        self.qrcode_callback_base_url = self.base_url + "callback_scan_status/"
        self.qrcode_scan_base_url = self.base_url + "scan_qrcode/"
        self.click_callback_base_url = self.base_url + "callback_click_status/"
        self.click_base_url = self.base_url + "click/"

    def scan_register_callback(self, sid, callback, self_obj):
        ret = {
            "function": callback,
            "self_obj": self_obj,
            "status": False
        }
        self.scan_callbacks[sid] = ret

    def click_register_callback(self, sid, callback, self_obj):
        ret = {
            "function": callback,
            "self_obj": self_obj,
            "status": False
        }
        self.click_callbacks[sid] = ret

    def callback(self):
        pass

    def register_sid(self, sid, url_dict):
        url_dict["sid"] = sid
        self.ids[sid] = url_dict

    def create_qrcode(self):
        sid = str(uuid4())
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=1,
        )
        pic_name = sid + ".png"

        qrcode_url_path = self.web_base_url + pic_name
        qrcode_callback_url = self.qrcode_callback_base_url + sid
        qrcode_scan_url = self.qrcode_scan_base_url + sid
        click_callback_url = self.click_callback_base_url + sid
        click_url = self.click_base_url + sid
        qrcode_pic_path = os.path.join(self.qrcode_pic_dir, pic_name)
        url_dict = {
            "qrcode_url_path": qrcode_url_path,
            "qrcode_callback_url": qrcode_callback_url,
            "qrcode_scan_url": qrcode_scan_url,
            "click_callback_url": click_callback_url,
            "click_url": click_url,
        }
        self.register_sid(sid, url_dict)
        qr.add_data(qrcode_scan_url)
        qr.make(fit=True)

        img = qr.make_image()

        img.save(qrcode_pic_path)
        return sid


class Application(tornado.web.Application):
    def __init__(self):
        self.qrcodeObj = QrCode()
        handlers = [
            (r'/', IndexHandler),
            (r'/scan_qrcode/(.*)', ScanQrcodeHandler),
            (r'/callback_scan_status/(.*)', ScanStatusCallBackHandler),
            # (r'/get_scan_status/(.*)', ScanStatusHandler),
            (r'/click/(.*)', ClickHandler),
            (r'/callback_click_status/(.*)', ClickStatusCallBackHandler)
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        tornado.web.Application.__init__(self, handlers, **settings)

    def get_qrcode(self):
        return self.qrcodeObj.create_qrcode()


if __name__ == '__main__':
    tornado.options.parse_command_line()

    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
