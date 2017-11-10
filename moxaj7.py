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
from datetime import tzinfo, timedelta, datetime
import pymongo
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
import pytz

global db
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

def rsp_note():
    string = "\np.s. 若您為車長請負責叫車"
    string += "\n費用參考(以車資70元為例):\n2人:車長35 乘客35\n3人:車長20 乘客各25\n4人:車長10 乘客各20"
    return string
def func_FAQ():
    string = "\
1.請務必依照平台指示填寫姓名及電話。\n\
2.顯示時間為計程車發車時間，請謹慎評估且於五分鐘前抵達集合地點。\n\
–大坪林集合地點:三號出口附近的福園號 https://goo.gl/86doY7\n\
–公司集合地點:寶橋路135號一樓大廳集合\n\
3.由車長負責叫車，務必在發車時間前完成動作。\n\
4.叫車期間請即時追蹤乘車資訊(點選主選單)以避免名單異動造成的不必要困擾。"
    return string
def application(environ, start_response):
    global db
    time_div = 750
    #data_json = json.dumps(data_str)
    data_str = {}
    #print data_json
    tz = pytz.timezone('Asia/Taipei')
    local_dt = datetime.now().replace(tzinfo=pytz.utc).astimezone(tz)
    now = tz.normalize(local_dt).strftime('%m-%d %H:%M')
    h = tz.normalize(local_dt).strftime('%H')
    m = tz.normalize(local_dt).strftime('%M')
    timestamp = int(h)*60 + int(m)
    print "[Debug] timestamp = " + str(timestamp)
    timeslot = []
    timeslot_str = []
    if(10-int(m)%10 < 5):
	timeslot.append(local_dt + timedelta(minutes=(10-int(m)%10 + 10)))
    else:
	timeslot.append(local_dt + timedelta(minutes=(10-int(m)%10)))
    timeslot_str.append(tz.normalize(timeslot[0]).strftime('%m-%d %H:%M'))
    timeslot.append(timeslot[0] + timedelta(minutes=10))
    timeslot_str.append(tz.normalize(timeslot[1]).strftime('%m-%d %H:%M'))
    timeslot.append(timeslot[1] + timedelta(minutes=10))
    timeslot_str.append(tz.normalize(timeslot[2]).strftime('%m-%d %H:%M'))

    date_year = str(datetime.today().year)+"-"+str(datetime.today().month)+"-"+str(datetime.today().day) #2017-mm-dd
    print date_year
    db_collection = db[date_year]
    db_user = db['user']

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
	enable_cancel = 0
	enroll = 0
	reset = 0
	rookie = 0
	user = {}
	user['Register Name'] = ""
	user['Phone'] = ""
	user['Register'] = 0
	msg = event.message.text.split(' ')
	if(msg[0] == "重新註冊"):
                print "重新註冊"
		reset = 1
		result = db_user.delete_one({"User ID":event.source.user_id})
	if(msg[0] == "是"):
		print "是"
		db_user.find_one_and_update({"User ID":event.source.user_id}, {'$set':{"Register":1}}, return_document=ReturnDocument.AFTER)
		show_mainmenu = 1
	elif(msg[0] == "否"):
		print "否"
		reset = 1
		db_user.delete_one({"User ID":event.source.user_id})
	#判斷是否已註冊完畢
	find = 0
	for p in db_user.find():
		if(event.source.user_id == p["User ID"]):
			find = 1
			user["User ID"] = event.source.user_id
			if(p["Register Name"] != ""):
				enroll += 1
				user["Register Name"] = p["Register Name"]
			if(p["Phone"] != ""):
				enroll += 1
				user["Phone"] = p["Phone"]
			if(p["Register"] == 1):
				enroll += 1
				user["User ID"] = p["User ID"]
	if(find == 0):
		user["Line Name"] = profile.display_name
		user["User ID"] = event.source.user_id
		db_user.insert_one(user).inserted_id
		rookie = 1
        if(msg[0] == "主選單"):
		if(enroll == 3):
			show_mainmenu = 1
	elif(msg[0] == "搭車"):
		print "搭車"
	        date_time = msg[1] + " " + msg[2] #mm-dd HH:MM
		time_wish_str = msg[2].split(':')
                time_wish = int(time_wish_str[0])*60 + int(time_wish_str[1])
		#搜尋是否最近已搭乘過
		last_time = 0
                for document in db_collection.find().sort("Timestamp", pymongo.ASCENDING):
                	passenger = document["Passenger"]
			for p in passenger:
	                        if(p["User ID"] == user["User ID"]):
                       			last_time = document["Timestamp"]
		if(-30 < time_wish - last_time < 30):
			line_bot_api.push_message(event.source.user_id,
                            TextSendMessage(text = "您最近已有1筆預約，請您先取消再預約"))
			start_response('200 OK', [])
			return create_body('OK')
		else:
			show_mainmenu = 1
			show_result = 1
		find = 0
		for document in db_collection.find():
			if(document["Date"] == date_time):
				print "Find the date data!"
				find = 1
				find_user = 0
				passenger = document["Passenger"]
				for p in passenger:
		                        if(p["User ID"] == user["User ID"]):
						find_user = 1
				if(find_user == 0):
					passenger.append(user)
					db_collection.find_one_and_update({"Date":date_time}, {'$set':{"Passenger":passenger}}, return_document=ReturnDocument.AFTER)
		if(find==0):
                        data_str["Date"] = date_time
			time_tmp = msg[2].split(':')
                        data_str["Timestamp"] = int(time_tmp[0])*60 + int(time_tmp[1])
                        data_str["Passenger"] = []
                        data_str["Passenger"].append(user)
			print data_str
			db_collection.insert_one(data_str).inserted_id
	elif(msg[0] == "取消"):
		print "取消"
		time_cancel_str = msg[2].split(':')
		time_cancel = int(time_cancel_str[0])*60 + int(time_cancel_str[1])
		if(timestamp > time_cancel - 5):#超出可取消的時間
			line_bot_api.push_message(event.source.user_id,
	                    TextSendMessage(text = "取消失敗，您已超過可取消的時間，下次請於搭車前五分鐘取消"))
		else:
			show_mainmenu = 1
			show_cancel = 1
			date_time = msg[1] + " " + msg[2]
			for document in db_collection.find():
        	                if(document["Date"] == date_time):
					passenger = document["Passenger"]
					for item in range(len(passenger)):
						if(passenger[item]["User ID"] == user["User ID"]):
							del passenger[item]
							break
					db_collection.find_one_and_update({"Date":date_time}, {'$set':{"Passenger":passenger}}, return_document=ReturnDocument.AFTER)
	elif(msg[0] == "搭乘狀況"):
		print "搭乘狀況"
		reply = ""
		for document in db_collection.find({"Timestamp":{"$gt":timestamp-60}}).sort("Timestamp", pymongo.ASCENDING):
			num = len(document["Passenger"])
			passenger = document["Passenger"]
			if(num%4==0):
				num_car = int(num/4)
				num_left = 4
			else:
				num_car = int(num/4)+1
				num_left = num%4
			print "num = " + str(num)
                        print "num_car = " + str(num_car)
                        print "num_left = " + str(num_left)
			num_p = 0
			car_now = 1
			for p in passenger:
				num_p = num_p%4 + 1
				print "num_p = " + str(num_p)
				if(car_now < num_car):
					if(num_p == 1):
						reply += document["Date"] + " 乘客" + str(4) + "人如下:"
			                       	reply += "\n車長: " + p["Register Name"] + " " + p["Phone"]
                        		else:
                                               	reply += "\n乘客"+str(num_p-1)+": "+  p["Register Name"] + " " + p["Phone"]
				else:
                                        if(num_p == 1):
						reply += document["Date"] + " 乘客" + str(num_left) + "人如下:"
                                                reply += "\n車長: " + p["Register Name"] + " " + p["Phone"]
                                        else:
                                                reply += "\n乘客"+str(num_p-1)+": "+  p["Register Name"] + " " + p["Phone"]
				if(num_p==4):
					car_now += 1
					print "car_now = " + str(car_now)
					reply += "\n\n"
			if(num!=0)and(num_p!=4):
				reply += "\n\n"
		if(reply.strip() == ""):
			line_bot_api.reply_message(event.reply_token, TextSendMessage(text = "目前尚無任何資料"))
		else:
			reply = reply[:-1]
	                reply += "===================="
			reply += rsp_note()
			#reply += "\np.s. 若您為車長請負責叫車"
	                #reply += "\n費用參考(以車資70元為例):\n2人:車長35 乘客35\n3人:車長20 乘客各25\n4人:車長10 乘客各20"
			line_bot_api.reply_message(event.reply_token, TextSendMessage(text = reply))	
	elif(msg[0] == "乘車須知"):
		print "乘車須知"
		reply = ""
		reply = func_FAQ()
		line_bot_api.reply_message(event.reply_token, TextSendMessage(text = reply))
	else:
		if(enroll == 0)and(reset!=1)and(rookie!=1):
			user["Register Name"] = msg[0]
			db_user.find_one_and_update({"User ID":event.source.user_id}, {'$set':{"Register Name":msg[0]}}, return_document=ReturnDocument.AFTER)
			enroll += 1
		elif(enroll == 1):
			user["Phone"] = msg[0]
			db_user.find_one_and_update({"User ID":event.source.user_id}, {'$set':{"Phone":msg[0]}}, return_document=ReturnDocument.AFTER)
			enroll +=1
        #新使用者
        print "enroll = " + str(enroll)
        if(enroll != 3):
                if(enroll == 0):
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text = "新使用者您好，目前尚未有您的資料，請問在公司大家平常都怎麼稱呼你/妳呢?"))
                        #user['Display Name'] = profile.display_name
                        #db_user.insert_one(user).inserted_id
                elif(enroll == 1):
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text = "請輸入您的手機號碼 ex. 0910555666"))
                elif(enroll == 2):
                        confirm_str = "請確認您的資料是否正確:\n名字: " + user["Register Name"] + "\n電話: "+ user["Phone"]
                        confirm_template = ConfirmTemplate(text = confirm_str, actions=[
                            MessageTemplateAction(label='是', text='是'),
                            MessageTemplateAction(label='否', text='否'),
                        ])
                        template_message = TemplateSendMessage(
                            alt_text='Confirm alt text', template=confirm_template)
                        line_bot_api.reply_message(event.reply_token, template_message)
                start_response('200 OK', [])
                return create_body('OK')
	if(show_mainmenu == 1):
                time_str = []
                text_str = []
		num_passenger = []
		print "[Debug] data_str =>"
		print data_str
		for i in range(0,3):
			find = 0
			for document in db_collection.find():
				find_user = 0
				if(timeslot_str[i] == document["Date"]):
					find = 1
					passenger = document["Passenger"]
					num_passenger.append(len(passenger))
					for p in passenger:
			                        if(p["User ID"] == user["User ID"]):
	                                        	time_str.append("取消 " + timeslot_str[i])
        	                                	text_str.append("取消 " + timeslot_str[i])
							find_user = 1
							break
					if(find_user == 0):
						time_tmp_str = timeslot_str[i].split(' ')
						time_tmp_str = time_tmp_str[1].split(':')
				                time_local = int(time_tmp_str[0])*60 + int(time_tmp_str[1])	
						if(time_local < time_div): #上班時間
							time_str.append(timeslot_str[i] + " 上班搭車")
		                        	        text_str.append("搭車 " + timeslot_str[i])
						else: #下班時間
							time_str.append(timeslot_str[i] + " 下班搭車")
                                                        text_str.append("搭車 " + timeslot_str[i])
			if(find==0):
				print "timestamp = " + str(timestamp)
                                time_tmp_str = timeslot_str[i].split(' ')
                                time_tmp_str = time_tmp_str[1].split(':')
                                time_local = int(time_tmp_str[0])*60 + int(time_tmp_str[1])
				if(time_local < time_div): #上班時間
					time_str.append(timeslot_str[i] + " 上班搭車")
					text_str.append("搭車 " + timeslot_str[i])
					num_passenger.append(0)
				else: #下班時間
					time_str.append(timeslot_str[i] + " 下班搭車")
                                        text_str.append("搭車 " + timeslot_str[i])
                                        num_passenger.append(0)
                for i in range(0,3):
                	time_str[i] = time_str[i] + " " + str(num_passenger[i]) + "人"
		if(user["Register Name"] != ""):
			profile.display_name = user["Register Name"]
		carousel_template = CarouselTemplate(columns=[
                CarouselColumn(text='歡迎使用Moxa計程車共乘服務', title= profile.display_name +' 您好', actions=[
                        MessageTemplateAction(label=time_str[0], text=text_str[0]),
                        MessageTemplateAction(label=time_str[1], text=text_str[1]),
                        MessageTemplateAction(label=time_str[2], text=text_str[2]),
                ]),
                CarouselColumn(text='請點選以下服務', title= '其他服務', actions=[
                        MessageTemplateAction(label="搭乘狀況", text='搭乘狀況'),
                        MessageTemplateAction(label="乘車須知", text='乘車須知'),
                        MessageTemplateAction(label="重新註冊", text='重新註冊'),
                ]),
                ])
                template_message = TemplateSendMessage(
                        alt_text='Buttons alt text', template=carousel_template)
                line_bot_api.reply_message(event.reply_token, template_message)

	result = ""
	if(show_result == 1) or (show_cancel == 1):
		for document in db_collection.find():
                        if(date_time == document["Date"]):
                                passenger = document["Passenger"]
                                num = len(passenger)
                                if(num%4==0):
                                        num_car = int(num/4)
                                        num_left = 4
                                else:
                                        num_car = int(num/4)+1
                                        num_left = num%4
                                num_p = 0
                                car_now = 1
                                #result = date_time + " 搭車共 " + str(num) + " 人："
                                for p in passenger:
                                        #result += "\n" + p["Register Name"] + " " + p["Phone"]
                                        num_p = num_p%4 + 1
                                        print "num_p = " + str(num_p)
                                        if(car_now < num_car):
                                                if(num_p == 1):
                                                        result += document["Date"] + " 乘客" + str(4) + "人如下:"
                                                        result += "\n車長: " + p["Register Name"] + " " + p["Phone"]
                                                else:
                                                        result += "\n乘客"+str(num_p-1)+": "+  p["Register Name"] + " " + p["Phone"]
                                        else:
                                                if(num_p == 1):
                                                        result += document["Date"] + " 乘客" + str(num_left) + "人如下:"
                                                        result += "\n車長: " + p["Register Name"] + " " + p["Phone"]
                                                else:
                                                        result += "\n乘客"+str(num_p-1)+": "+  p["Register Name"] + " " + p["Phone"]
                                        if(num_p==4):
                                                car_now += 1
                                                print "car_now = " + str(car_now)
	if(show_result == 1):
		date_time = msg[1] + " " + msg[2] #mm-dd HH:MM
		result_copy = result
		if(timestamp < time_div):
			print "[Debug] 上班"
			result += "\n====================\n"+"上車地點為大坪林捷運站附近的\"福園號\" https://goo.gl/86doY7"
		else:
			print "[Debug] 下班"
			result += "\n====================\n"+"上車地點為公司135號一樓大廳"
		result += rsp_note()
		#result += "\np.s. 若您為車長請負責叫車"
		#result += "\n費用參考(以車資70元為例):\n2人:車長35 乘客35\n3人:車長20 乘客各25\n4人:車長10 乘客各20"
		line_bot_api.push_message(event.source.user_id,
        	    TextSendMessage(text = result))
		#通知其他人
		for p in passenger:
			if(p["User ID"] != user["User ID"]):
				line_bot_api.push_message(p["User ID"],
		                    TextSendMessage(text = "有新乘客加入了!\n" + result_copy))
	if(show_cancel == 1):
		date_time = msg[1] + " " + msg[2] #mm-dd HH:MM
		line_bot_api.push_message(event.source.user_id,
                    TextSendMessage(text = "取消成功"))
		#通知其他人
		for p in passenger:
                        if(p["User ID"] != user["User ID"]):
                                line_bot_api.push_message(p["User ID"],
                                    TextSendMessage(text = "有人臨時取消了QQ\n" + result))
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
    print "Star MoxaJ7 Service"
    global db
    db_client = MongoClient()
    db = db_client['MoxaJ7']
    httpd = wsgiref.simple_server.make_server('', options.port, application)
    httpd.serve_forever()
