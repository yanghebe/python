# -*- coding: utf-8 -*-
## 載入需要的模組 ##
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import re

from sqlalchemy.sql.expression import text
from database import db_session, init_db
from user import Users
from product import Products
from cart import Cart
from config import Config
from order import Orders
from item import Items

from linepay import LinePay
from urllib.parse import parse_qsl
import uuid
app = Flask(__name__)
## LINE 聊天機器人的基本資料 ##
line_bot_api = LineBotApi('k/mPd9EjsdkYBoZszsBncRnPi0azFEkFPukixE9TbfZ1oavqogKusZ8ozTedw23JFMYv2dHsmLkw6F605se8HpCUPEML9UYEdmRBirCZFIwpxUdTZuji54xOO9mrJ7FvNJ39XzIJJPlFl/0SpJV/EAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('7f19d3f182789e74eb99832c7c2d2517')

#line_bot_api.push_message('Ud79ee4eb29a3613bfb2783494aa62f4d', TextSendMessage(text='💝💝歡迎光臨您到來!!!💝💝'))

####################### function #####################################################
def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def Usage(event):
    push_msg(event,"  🌸 歡迎到來愛麗絲花店 🌸   \
                    \n\
                    \n 🌈🌈 介紹 🌈🌈\
                    \n\
                    \n💕 在某年某月的各種花 💕\
                    \n🌟 讓我們一起期待春暖花開的那天 🌟\
                    \n🌟 油價通知 ➦➦➦ 輸入查詢油價 🌟")

def push_msg(evevt,msg):
    try:
        user_id = evevt.source.user_id
        line_bot_api.push_message(user_id,TextSendMessage(text=msg))
    except:
        room_id = evevt.source.user_id
        line_bot_api.push_message(room_id,TextSendMessage(text=msg))
            

@app.teardown_appcontext  #加上這個function可以幫助我們每一次執行完後都會關閉資料庫連線
def shutdown_session(exception=None):
    db_session.remove()

#建立或取得user id
def get_or_create_user(user_id):
    #從id=user_id先獲得有沒有這個user，如果有就直接跳到return
    user = db_session.query(Users).filter_by(id=user_id).first()
    #沒有的話就會透過line_bot_api來取得用戶資訊
    if not user:
        profile = line_bot_api.get_profile(user_id)
        #然後再建立user並且存入到資料庫當中
        user = Users(id=user_id, nick_name=profile.display_name,image_url=profile.picture_url)
        db_session.add(user)
        db_session.commit()
@app.route("/confirm")
def confirm():
    transaction_id = request.args.get('transactionId')
    order = db_session.query(Orders).filter(Orders.transaction_id == transaction_id).first()

    if order:
        line_pay = LinePay()
        line_pay.confirm(transaction_id=transaction_id, amount=order.amount)

        order.is_pay = True#確認收款無誤時就會改成已付款
        db_session.commit()
        
        #傳收據給用戶
        message = order.display_receipt()
        line_bot_api.push_message(to=order.user_id, messages=message)

        return '<h1>Your payment is successful. thanks for your purchase.</h1>'

## 接收 LINE 的資訊 ##
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    ## handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

## 學你說話
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    get_or_create_user(event.source.user_id)#加入這行
    #message_text = str(event.message.text).lower()#將所有的字變成小寫

    #如果沒有中文，就轉小寫，如果有中文，就不轉換
    if is_ascii(str(event.message.text)):
        message_text = str(event.message.text).lower()
    else:
        message_text = event.message.text

    emsg = event.message.text
    message = None

    '''print(event.source.user_id)
    profile = line_bot_api.get_profile(event.source.user_id)

    print(profile.user_id)
    print(profile.picture_url)
    print(profile.status_message)#None'''

    cart = Cart(user_id = event.source.user_id)
    #######################判斷區#####################################################
    if re.match('/help|news',emsg):
        Usage(event)

    if message_text in ["what is your story?", "story"]:
        message = [
            ImageSendMessage(
                original_content_url='https://i.imgur.com/DKzbk3l.jpg',
                preview_image_url='https://i.imgur.com/DKzbk3l.jpg'
            ), StickerSendMessage(
                #熊大
                package_id='11537',
                sticker_id='52002734'
            )
        ]

    elif message_text in ['i am ready to order.', 'add']:
        #message = TextSendMessage(text='list products')
        message = Products.list_all()

    elif message_text in ['my cart', 'cart']:
        message = TextSendMessage(text='cart')

    elif "like to have" in message_text:
        product_name = message_text.split(',')[0]
        num_item = message_text.rsplit(':')[1]
        product = db_session.query(Products).filter(Products.name.ilike(product_name)).first()
        message = TextSendMessage(text='Yep')
        
        if product:
            cart.add(product=product_name, num=num_item)
            confirm_template = ConfirmTemplate(
                text= 'Sure, {} {}, anything else?'.format(num_item, product_name),
                actions=[
                    MessageAction(label='Add', text='add'),
                    MessageAction(label="That's it", text="that's it")
                ])
            message = TemplateSendMessage(alt_text='anything else?', template=confirm_template)
        
        else:
            message = TextSendMessage(text="Sorry, We din't have {}.".format(product_name))
        print(cart.bucket())
    
    elif message_text in ['my cart', "that's it"]:
        if cart.bucket():
            #message = TextSendMessage(text='Well done.')
            message = cart.display()
        else:
            message = TextSendMessage(text='Your cart is empty now.')

    elif message_text == 'empty cart':

        cart.reset()

        message = TextSendMessage(text='Your cart is empty now.')

    if message:
        line_bot_api.reply_message(
        event.reply_token,
        message) 
@handler.add(PostbackEvent)
def handle_postback(event):
    data = dict(parse_qsl(event.postback.data))#先將postback中的資料轉成字典

    action = data.get('action')#再get action裡面的值

    if action == 'checkout':#如果action裡面的值是checkout的話才會執行結帳的動作

        user_id = event.source.user_id#取得user_id

        cart = Cart(user_id=user_id)#透過user_id取得購物車

        if not cart.bucket():#判斷購物車裡面有沒有資料，沒有就回傳購物車是空的
            message = TextSendMessage(text='Your cart is empty now.')

            line_bot_api.reply_message(event.reply_token, [message])

            return 'OK'

        order_id = uuid.uuid4().hex#如果有訂單的話就會使用uuid的套件來建立，因為它可以建立獨一無二的值

        total = 0 #總金額
        items = [] #暫存訂單項目

        for product_name, num in cart.bucket().items():#透過迴圈把項目轉成訂單項目物件
            #透過產品名稱搜尋產品是不是存在
            product = db_session.query(Products).filter(Products.name.ilike(product_name)).first()
            #接著產生訂單項目的物件
            item = Items(product_id=product.id,
                         product_name=product.name,
                         product_price=product.price,
                         order_id=order_id,
                         quantity=num)

            items.append(item)

            total += product.price * int(num)#訂單價格 * 訂購數量
        #訂單項目物件都建立後就會清空購物車
        cart.reset()
        #建立LinePay的物件
        line_pay = LinePay()
        #再使用line_pay.pay的方法，最後就會回覆像postman的格式
        info = line_pay.pay(product_name='LSTORE',
                            amount=total,
                            order_id=order_id,
                            product_image_url=Config.STORE_IMAGE_URL)
        #取得付款連結和transactionId後
        pay_web_url = info['paymentUrl']['web']
        transaction_id = info['transactionId']
        #接著就會產生訂單
        order = Orders(id=order_id,
                       transaction_id=transaction_id,
                       is_pay=False,
                       amount=total,
                       user_id=user_id)
        #接著把訂單和訂單項目加入資料庫中
        db_session.add(order)

        for item in items:
            db_session.add(item)

        db_session.commit()
        #最後告知用戶並提醒付款
        message = TemplateSendMessage(
            alt_text='Thank you, please go ahead to the payment.',
            template=ButtonsTemplate(
                text='Thank you, please go ahead to the payment.',
                actions=[
                    URIAction(label='Pay NT${}'.format(order.amount),
                              uri=pay_web_url)
                ]))

        line_bot_api.reply_message(event.reply_token, [message])

    return 'OK'
@handler.add(FollowEvent)
def handle_follow(event):
    #同樣取得user_id
    get_or_create_user(event.source.user_id)

    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text='Hi! 歡迎回到火星村')
    )

@handler.add(UnfollowEvent)
def handle_unfollow():
    #先執行封鎖再解封會print出
    print("Got unfollow event")

#初始化產品資訊
@app.before_first_request
def init_products():
    # init db
    result = init_db()#先判斷資料庫有沒有建立，如果還沒建立就會進行下面的動作初始化產品
    if result:
        init_data = [Products(name='無毒白蝦-博士好蝦預購中-(30-35尾600克)',
                              product_image_url='https://i.imgur.com/0KinQXT.jpg',
                              price=380,
                              description='無毒白蝦-博士好蝦預購中-(30-35尾600克)'),
                     Products(name='無毒白蝦-博士好蝦預購中-(40-45尾600克)',
                              product_image_url='https://i.imgur.com/0KinQXT.jpg',
                              price=300,
                              description='無毒白蝦-博士好蝦預購中-(40-45尾600克)'),
                     Products(name='無毒白蝦-博士好蝦預購中-(15-18尾300克)',
                              price=200,
                              product_image_url='https://i.imgur.com/0KinQXT.jpg',
                              description='無毒白蝦-博士好蝦預購中-(15-18尾300克)')]
        db_session.bulk_save_objects(init_data)#透過這個方法一次儲存list中的產品
        db_session.commit()#最後commit()才會存進資料庫

if __name__ == "__main__":
    #init_db()
    init_products()
    app.run()
    