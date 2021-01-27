import time
import json
import requests
import datetime
from campus import CampusCard


def main():
    # sectets字段录入
    username_list = os.environ['USERNAME'].split(',')
    password_list = os.environ['PASSWORD'].split(',')
    sckey = os.environ['SCKEY']
    success, failure, result = [], [], []

    # 提交打卡
    count, msg, run = 0, "null", False
    for username, password in zip([i.strip() for i in username_list if i != ''],
                                  [i.strip() for i in password_list if i != '']):
        print("-----------------------")
        print("开始获取用户%s信息" % (username[-4:]))
        while count < 3:
            try:
                campus = CampusCard(username, password)
                token = campus.user_info["sessionId"]
                time.sleep(1)
                res = check_in(token).res.json()
                strTime = GetNowTime()
                if res['code'] == '10000':
                    success.append(username[-4:])
                    msg = username[-4:] + "-打卡成功-" + strTime
                    result = res
                    run = False
                    break
                else:
                    failure.append(value[-4:])
                    msg = username[-4:] + "-失败-" + strTime
                    count = count + 1
                    print('%s打卡失败，开始第%d次重试...' % (username[-6:], count))
                    time.sleep(301)

            except Exception as err:
                print(err)
                msg = '出现错误'
                failure.append(username[-4:])
                break
        print(msg)
        print("-----------------------")
    fail = sorted(set(failure), key=failure.index)
    title = "成功: %s 人,失败: %s 人" % (len(success), len(fail))
    for _ in range(1):
        try:
            if not (sckey is None) & run:
                print('开始Wechat推送...')
                WechatPush(title, sckey[0], success, fail, result)
                break
        except:
            print("WeChat推送出错！")


# 时间函数
def GetNowTime():
    cstTime = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))
    strTime = cstTime.strftime("%H:%M:%S")
    return strTime


def get_post_json(post_json):
    """
    获取打卡数据
    :param jsons: 用来获取打卡数据的json字段
    :return:
    """
    for _ in range(3):
        try:
            res = requests.post(
                url="https://reportedh5.17wanxiao.com/sass/api/epmpics",
                json=post_json,
                verify=False,
            ).json()
        except:
            logging.warning("获取完美校园打卡post参数失败，正在重试...")
            time.sleep(1)
            continue
        if res["code"] != "10000":
            logging.warning(res)
        data = json.loads(res["data"])
        # print(data)
        post_dict = {
            "areaStr": data['areaStr'],
            "deptStr": data['deptStr'],
            "deptid": data['deptStr']['deptid'] if data['deptStr'] else None,
            "customerid": data['customerid'],
            "userid": data['userid'],
            "username": data['username'],
            "stuNo": data['stuNo'],
            "phonenum": data["phonenum"],
            "templateid": data["templateid"],
            "updatainfo": [
                {"propertyname": i["propertyname"], "value": i["value"]}
                for i in data["cusTemplateRelations"]
            ],
            "updatainfo_detail": [
                {
                    "propertyname": i["propertyname"],
                    "checkValues": i["checkValues"],
                    "description": i["decription"],
                    "value": i["value"],
                }
                for i in data["cusTemplateRelations"]
            ],
            "checkbox": [
                {"description": i["decription"], "value": i["value"]}
                for i in data["cusTemplateRelations"]
            ],
        }
        # print(json.dumps(post_dict, sort_keys=True, indent=4, ensure_ascii=False))
        logging.info("获取完美校园打卡post参数成功")
        return post_dict
    return None


def healthy_check_in(token, username, post_dict):
    """
    第一类健康打卡
    :param username: 手机号
    :param token: 用户令牌
    :param post_dict: 打卡数据
    :return:
    """
    check_json = {
        "businessType": "epmpics",
        "method": "submitUpInfo",
        "jsonData": {
            "deptStr": post_dict["deptStr"],
            "areaStr": post_dict["areaStr"],
            "reportdate": round(time.time() * 1000),
            "customerid": post_dict["customerid"],
            "deptid": post_dict["deptid"],
            "source": "app",
            "templateid": post_dict["templateid"],
            "stuNo": post_dict["stuNo"],
            "username": post_dict["username"],
            "phonenum": post_dict["phonenum"],
            "userid": post_dict["userid"],
            "updatainfo": post_dict["updatainfo"],
            "gpsType": 1,
            "token": token,
        },
    }
    for _ in range(3):
        try:
            res = requests.post(
                "https://reportedh5.17wanxiao.com/sass/api/epmpics", json=check_json, timeout=10
            ).json()
            if res['code'] == '10000':
                logging.info(res)
                return {
                    "status": 1,
                    "res": res,
                    "post_dict": post_dict,
                    "check_json": check_json,
                    "type": "healthy",
                }
            elif "频繁" in res['data']:
                logging.info(res)
                return {
                    "status": 1,
                    "res": res,
                    "post_dict": post_dict,
                    "check_json": check_json,
                    "type": "healthy",
                }
            else:
                logging.warning(res)
                return {"status": 0, "errmsg": f"{post_dict['username']}: {res}"}
        except:
            errmsg = f"```打卡请求出错```"
            logging.warning("健康打卡请求出错")
            return {"status": 0, "errmsg": errmsg}
    return {"status": 0, "errmsg": "健康打卡请求出错"}


# 打卡提交函数
def check_in(token):
    sign_url = "https://reportedh5.17wanxiao.com/sass/api/epmpics"
    # 获取第一类健康打卡的参数
    user_json = {
        "businessType": "epmpics",
        "jsonData": {"templateid": "pneumonia", "token": token},
        "method": "userComeApp",
    }
    post_dict = get_post_json(user_json)

    # 提交打卡
    time.sleep(2)
    if post_dict:
        # 第一类健康打卡
        # print(post_dict)

        # 修改温度等参数
        # for j in post_dict['updatainfo']:  # 这里获取打卡json字段的打卡信息，微信推送的json字段
        #     if j['propertyname'] == 'temperature':  # 找到propertyname为temperature的字段
        #         j['value'] = '36.2'  # 由于原先为null，这里直接设置36.2（根据自己学校打卡选项来）
        #     if j['propertyname'] == 'xinqing':
        #         j['value'] = '健康'

        # 修改地址，依照自己完美校园，查一下地址即可
        # post_dict['areaStr'] = '{"streetNumber":"89号","street":"建设东路","district":"","city":"新乡市","province":"河南省",' \
        #                        '"town":"","pois":"河南师范大学(东区)","lng":113.91572178314209,' \
        #                        '"lat":35.327695868943984,"address":"牧野区建设东路89号河南师范大学(东区)","text":"河南省-新乡市",' \
        #                        '"code":""} '
        healthy_check_dict = healthy_check_in(token, post_dict)
        return healthy_check_dict


# 微信通知
def WechatPush(title, sckey, success, fail, result):
    send_url = f"https://sc.ftqq.com/{sckey}.send"
    strTime = GetNowTime()
    page = json.dumps(result, sort_keys=True, indent=4, separators=(',', ':'), ensure_ascii=False)
    content = [f"""`{strTime}`
#### 打卡成功用户:
`{success}`
#### 打卡失败用户:
`{fail}`
#### 主用户打卡信息:
```
{page}
```"""]
    data = {
        "text": title,
        "desp": content
    }
    try:
        req = requests.post(send_url, data=data)
        if req.json()["errmsg"] == 'success':
            print("Server酱推送服务成功")
        else:
            print("Server酱推送服务失败")
    except:
        print("Server酱推送异常")


if __name__ == '__main__':
    main()
