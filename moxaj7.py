# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import wsgiref.simple_server
from argparse import ArgumentParser

from builtins import bytes
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, ImageCarouselTemplate, ImageCarouselColumn, URITemplateAction,
    PostbackTemplateAction, DatetimePickerTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage, FileMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
)
from linebot.utils import PY3
import json
from datetime import tzinfo, timedelta, datetime, date
import pytz

global num_total
global data_str

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)

def application(environ, start_response):
    global num_total
    global data_str
    data_json = json.dumps(data_str)
    print data_str
    print data_json
    tz = pytz.timezone('Asia/Taipei')
    local_dt = datetime.now().replace(tzinfo=pytz.utc).astimezone(tz)
    now = tz.normalize(local_dt).strftime('%m-%d %H:%M')
    m = tz.normalize(local_dt).strftime('%M')
    timeslot = []
    timeslot_str = []
    timeslot.append(local_dt + timedelta(minutes=(10-int(m)%10)))
    timeslot_str.append(tz.normalize(timeslot[0]).strftime('%m-%d %H:%M'))
    timeslot.append(timeslot[0] + timedelta(minutes=10))
    timeslot_str.append(tz.normalize(timeslot[1]).strftime('%m-%d %H:%M'))
    timeslot.append(timeslot[1] + timedelta(minutes=10))
    timeslot_str.append(tz.normalize(timeslot[2]).strftime('%m-%d %H:%M'))
 
    # check request method
    if environ['REQUEST_METHOD'] != 'POST':
        start_response('405 Method Not Allowed', [])
        return create_body('Method Not Allowed')

    # get X-Line-Signature header value
    signature = environ['HTTP_X_LINE_SIGNATURE']

    # get request body as text
    wsgi_input = environ['wsgi.input']
    content_length = int(environ['CONTENT_LENGTH'])
    body = wsgi_input.read(content_length).decode('utf-8')

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        start_response('400 Bad Request', [])
        return create_body('Bad Request')
    print events
    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

	profile = line_bot_api.get_profile(event.source.user_id)
	#print profile.display_name
	show_mainmenu = 0
	show_result = 0
	show_cancel = 0
	msg = event.message.text.split(' ')
        if(msg[0] == "主選單"):
		show_mainmenu = 1
	if(msg[0] == "搭車"):
		print "搭車"
		show_mainmenu = 1
		show_result = 1
		date = msg[1] + " " + msg[2]
		if(date in data_json):
			print "have more than 1 passenger"
			passenger = data_str[date]
			if(profile.display_name in passenger):
				print "already take a car"
			else:
				data_str[date].append(profile.display_name)
		else:
			data_str[date] = []
			data_str[date].append(profile.display_name)
	if(msg[0] == "取消"):
		print "取消"
		show_mainmenu = 1
		show_cancel = 1
		date = msg[1] + " " + msg[2]
		data_str[date].remove(profile.display_name)
	if(msg[0] == "搭乘狀況"):
		print "搭乘狀況"
		reply = ""
		for key in data_str:
			p = data_str[key]
			num = len(data_str[key])
			if(num !=0):
				reply = reply + key + " 乘客" + str(num) + "人如下:\n"
				for i in p:
					reply = reply + i + ". "
				reply = reply + "\n"
		line_bot_api.reply_message(event.reply_token, TextSendMessage(text = reply))	
	if(show_mainmenu == 1):
                time_str = []
                text_str = []
		num_passenger = []
		data_json = json.dumps(data_str)
		for i in range(0,3):
			if(timeslot_str[i] in data_json):
				passenger = data_str[timeslot_str[i]]
				print len(data_str[timeslot_str[i]])
				num_passenger.append(len(data_str[timeslot_str[i]]))
                                if(profile.display_name in passenger):
                                        time_str.append("取消 " + timeslot_str[i])
                                        text_str.append("取消 " + timeslot_str[i])
				else:
					time_str.append(timeslot_str[i] + " 搭車")
	                                text_str.append("搭車 " + timeslot_str[i])
			else:
				time_str.append(timeslot_str[i] + " 搭車")
				text_str.append("搭車 " + timeslot_str[i])
				num_passenger.append(0)
                for i in range(0,3):
                	time_str[i] = time_str[i] + " 共 " + str(num_passenger[i]) + " 人"
		carousel_template = CarouselTemplate(columns=[
                CarouselColumn(text='歡迎使用MoxaJ7共乘服務', title= profile.display_name +' 您好', actions=[
                        PostbackTemplateAction(label=time_str[0], data='ping1', text=text_str[0]),
                        PostbackTemplateAction(label=time_str[1], data='ping1', text=text_str[1]),
                        PostbackTemplateAction(label=time_str[2], data='ping1', text=text_str[2]),
                        #MessageTemplateAction(label='Translate Rice', text='米')
                ]),
                CarouselColumn(text='請點選以下服務', title= '其他服務', actions=[
                        PostbackTemplateAction(label="搭乘狀況", data='ping1', text='搭乘狀況'),
                        PostbackTemplateAction(label="FAQ", data='ping1', text='FAQ'),
                        PostbackTemplateAction(label="返回主選單", data='ping1', text='主選單'),
                        #MessageTemplateAction(label='Translate Rice', text='米')
                ]),
                ])
                template_message = TemplateSendMessage(
                        alt_text='Buttons alt text', template=carousel_template)
                line_bot_api.reply_message(event.reply_token, template_message)
	
	if(show_result == 1):
		date = msg[1] + " " + msg[2]
		num = len(data_str[date])
		result = date + " 搭車共 " + str(num) + " 人：\n"
		passenger = data_str[date]
		for p in passenger:
			result = result + p + ". "
		line_bot_api.push_message(
	            event.source.user_id,
        	    TextSendMessage(text = result)
	        )
	if(show_cancel == 1):
		line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text = "取消成功")
                )

    start_response('200 OK', [])
    return create_body('OK')


def create_body(text):
    if PY3:
        return [bytes(text, 'utf-8')]
    else:
        return text


if __name__ == '__main__':
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    options = arg_parser.parse_args()
    print "hi"
    global num_total
    num_total = 0
    global data_str
    data_str = {}
    httpd = wsgiref.simple_server.make_server('', options.port, application)
    httpd.serve_forever()
