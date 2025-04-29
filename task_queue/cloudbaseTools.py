import requests
import json

class WeixinCloudFunctionHelper:
    def __init__(self, appid, appsecret, env, cloud_function_name):
        self.appid = appid
        self.appsecret = appsecret
        self.env = env
        self.cloud_function_name = cloud_function_name

    def get_access_token(self):
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.appid}&secret={self.appsecret}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"请求发生错误: {e}")
            return None

    def invoke_cloud_function(self, token, postbody):
        url = f"https://api.weixin.qq.com/tcb/invokecloudfunction?access_token={token}&env={self.env}&name={self.cloud_function_name}"
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(url, headers=headers, data=postbody, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"请求发生错误: {e}")
            return None

    def execute_cloud_function(self, img_url, task_id):
        access_token_result = self.get_access_token()
        if access_token_result is None:
            return None
        token = access_token_result.get('access_token')
        if token is None:
            return None

        data = {
            'type': 'uploadImageFile',
            "task_id": task_id,
            "imgUrl": img_url
        }
        postbody = json.dumps(data)
        return self.invoke_cloud_function(token, postbody)