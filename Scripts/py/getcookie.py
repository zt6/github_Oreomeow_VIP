import re
import time
from asyncio import exceptions

import qrcode
import requests
from telethon import Button, events

from .. import chat_id, chname, img_file, jdbot, mybot
from ..bot.utils import press_event

cookiemsg = ""
# 扫码获取cookie 直接采用LOF大佬代码
# getSToken请求获取，s_token用于发送post请求是的必须参数
s_token = ""
# getSToken请求获取，guid,lsid,lstoken用于组装cookies
guid, lsid, lstoken = "", "", ""
# 由上面参数组装生成，getOKLToken函数发送请求需要使用
cookies = ""
# getOKLToken请求获取，token用户生成二维码使用、okl_token用户检查扫码登录结果使用
token, okl_token = "", ""
# 最终获取到的可用的cookie
jd_cookie = ""


def getSToken():
    time_stamp = int(time.time() * 1000)
    get_url = f"https://plogin.m.jd.com/cgi-bin/mm/new_login_entrance?lang=chs&appid=300&returnurl=https://wq.jd.com/passport/LoginRedirect?state={time_stamp}&returnurl=https://home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action&source=wq_passport"

    get_header = {
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-cn",
        "Referer": f"https://plogin.m.jd.com/login/login?appid=300&returnurl=https://wq.jd.com/passport/LoginRedirect?state={time_stamp}&returnurl=https://home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action&source=wq_passport",
        "User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8H7 Safari/6533.18.5 UCBrowser/13.4.2.1122",
        "Host": "plogin.m.jd.com",
    }

    resp = requests.get(url=get_url, headers=get_header)
    parseGetRespCookie(resp.headers, resp.json())


def parseGetRespCookie(headers, get_resp):
    global s_token
    global cookies
    s_token = get_resp.get("s_token")
    set_cookies = headers.get("set-cookie")
    guid = re.findall(r"guid=(.+?);", set_cookies)[0]
    lsid = re.findall(r"lsid=(.+?);", set_cookies)[0]
    lstoken = re.findall(r"lstoken=(.+?);", set_cookies)[0]
    cookies = f"guid={guid}; lang=chs; lsid={lsid}; lstoken={lstoken}; "


def getOKLToken():
    post_time_stamp = int(time.time() * 1000)
    post_url = f"https://plogin.m.jd.com/cgi-bin/m/tmauthreflogurl?s_token={s_token}&v={post_time_stamp}&remember=true"

    post_data = {
        "lang": "chs",
        "appid": 300,
        "returnurl": f"https://wqlogin2.jd.com/passport/LoginRedirect?state={post_time_stamp}&returnurl=//home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action",
        "source": "wq_passport",
    }

    post_header = {
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded; Charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookies,
        "Referer": f"https://plogin.m.jd.com/login/login?appid=300&returnurl=https://wqlogin2.jd.com/passport/LoginRedirect?state={post_time_stamp}&returnurl=//home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action&source=wq_passport",
        "User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8H7 Safari/6533.18.5 UCBrowser/13.4.2.1122",
        "Host": "plogin.m.jd.com",
    }

    try:
        global okl_token
        resp = requests.post(
            url=post_url, headers=post_header, data=post_data, timeout=20
        )
        parsePostRespCookie(resp.headers, resp.json())
    except Exception as error:
        print("Post网络请求错误", error)


def parsePostRespCookie(headers, data):
    global token
    global okl_token
    token = data.get("token")
    okl_token = re.findall(r"okl_token=(.+?);", headers.get("set-cookie"))[0]


def parseJDCookies(headers):
    global jd_cookie
    set_cookie = headers.get("Set-Cookie")
    pt_key = re.findall(r"pt_key=(.+?);", set_cookie)[0]
    pt_pin = re.findall(r"pt_pin=(.+?);", set_cookie)[0]
    jd_cookie = f"pt_key={pt_key};pt_pin={pt_pin};"


def creatqr(text):
    """实例化QRCode生成qr对象"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.clear()
    # 传入数据
    qr.add_data(text)
    qr.make(fit=True)
    # 生成二维码
    img = qr.make_image()
    # 保存二维码
    img.save(img_file)


@jdbot.on(events.NewMessage(from_users=chat_id, pattern=r"^/getcookie"))
async def my_cookie(event):
    """接收/getcookie后执行程序"""
    login = True
    msg = await jdbot.send_message(chat_id, "正在获取二维码，请稍后")
    global cookiemsg
    try:
        SENDER = event.sender_id
        async with jdbot.conversation(SENDER, timeout=30) as conv:
            getSToken()
            getOKLToken()
            url = f"https://plogin.m.jd.com/cgi-bin/m/tmauth?appid=300&client_type=m&token={token}"
            creatqr(url)
            markup = [
                Button.inline("已扫码", data="confirm"),
                Button.inline("取消", data="cancel"),
            ]
            await jdbot.delete_messages(chat_id, msg)
            cookiemsg = await jdbot.send_message(
                chat_id,
                "30s内点击取消将取消本次操作\n如不取消，扫码结果将于30s后显示\n扫码后不想等待点击已扫码",
                file=img_file,
                buttons=markup,
            )
            convdata = await conv.wait_event(press_event(SENDER))
            res = bytes.decode(convdata.data)
            if res != "cancel":
                raise exceptions.TimeoutError()
            login = False
            await jdbot.delete_messages(chat_id, cookiemsg)
            msg = await conv.send_message("对话已取消")
            conv.cancel()
    except exceptions.TimeoutError:
        expired_time = time.time() + 60 * 2
        while login:
            check_time_stamp = int(time.time() * 1000)
            check_url = f"https://plogin.m.jd.com/cgi-bin/m/tmauthchecktoken?&token={token}&ou_state=0&okl_token={okl_token}"

            check_data = {
                "lang": "chs",
                "appid": 300,
                "returnurl": f"https://wqlogin2.jd.com/passport/LoginRedirect?state={check_time_stamp}&returnurl=//home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action",
                "source": "wq_passport",
            }

            check_header = {
                "Referer": f"https://plogin.m.jd.com/login/login?appid=300&returnurl=https://wqlogin2.jd.com/passport/LoginRedirect?state={check_time_stamp}&returnurl=//home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action&source=wq_passport",
                "Cookie": cookies,
                "Connection": "Keep-Alive",
                "Content-Type": "application/x-www-form-urlencoded; Charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8H7 Safari/6533.18.5 UCBrowser/13.4.2.1122",
            }

            resp = requests.post(
                url=check_url, headers=check_header, data=check_data, timeout=30
            )
            data = resp.json()
            if data.get("errcode") == 0:
                parseJDCookies(resp.headers)
                await jdbot.delete_messages(chat_id, cookiemsg)
                await jdbot.send_message(chat_id, "以下为获取到的cookie")
                await jdbot.send_message(chat_id, jd_cookie)
                return
            if data.get("errcode") == 21:
                await jdbot.delete_messages(chat_id, cookiemsg)
                await jdbot.send_message(chat_id, f'发生了某些错误\n{data.get("errcode")}')
                return
            if time.time() > expired_time:
                await jdbot.delete_messages(chat_id, cookiemsg)
                await jdbot.send_message(chat_id, "超过3分钟未扫码，二维码已过期")
                return
    except Exception as e:
        await jdbot.send_message(chat_id, f"something wrong,I'm sorry\n{str(e)}")


if chname:
    jdbot.add_event_handler(
        my_cookie,
        events.NewMessage(from_users=chat_id, pattern=mybot["命令别名"]["getcookie"]),
    )
