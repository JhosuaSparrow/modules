# ThingsBoard平台客户端模块 用户指导手册

## 简介

> 该模块为ThingsBoard平台客户端功能模块, 使用MQTT协议进行通信, 实现设备与服务器数据交互
> 
> 主要支持功能
>
> - 消息发布与订阅


## API说明

### TBDeviceMQTTClient

> 该模块主要提供ThingsBoard平台客户端模块的连接, 消息的发送, 消息订阅。

#### 实例化对象

**示例:**

```python
from thingsboard import TBDeviceMQTTClient

cloud_cfg = {
    "host": "xxx",
    "port": 0,
    "username": "xxx",
    "qos": 1,
    "client_id": "xxx",
}
cloud = TBDeviceMQTTClient(**cloud_cfg)
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|host|str|服务端IP|
|port|int|服务端端口|
|username|str|用户名|
|qos|int|消息服务质量(0~1)|
|client_id|str|客户端id, 可使用设备IMEI号|

#### status

> 查询服务器连接状态.

**示例:**

```python
conn_status = cloud.status
print(conn_status)
# True
```

**返回值:**

|数据类型|说明|
|:---|---|
|bool|`True` - 已连接<br>`False` - 未连接|

#### set_callback

> 设置接收服务端下发的数据信息.

**示例:**

```python
def cloud_callback(topic, data):
    print("topic: %s, data: %s" % (topic, data))

cloud.set_callback(cloud_callback)
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|callback|function|用于接收服务端下发的数据信息,<br>函数入参`(topic, data)`|

**返回值:**

|bool|`True` - 成功<br>`False` - 失败|

> 连接登录服务器.

**示例:**

```python
res = cloud.connect()
print(res)
# 0
```

**参数:**

无

#### disconnect

> 断开服务器连接.

**示例:**

```python
res = cloud.disconnect()
print(res)
# True
```

**参数:**

无

**返回值:**

|数据类型|说明|
|:---|---|
|bool|`True` - 成功<br>`False` - 失败|

#### send_telemetry

> 遥测数据上报.

**示例:**

```python
data = {
    "Longitude": 100.26,
    "Latitude": 26.86,
    "Altitude": 0.0,
    "Speed": 10.0
}
res = cloud.send_telemetry(data)
print(res)
# True
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|data|dict|遥测数据|

**返回值:**

|数据类型|说明|
|:---|---|
|bool|`True` - 成功<br>`False` - 失败|

#### send_rpc_reply

> RPC消息应答.

**示例:**

```python
data = {
    "Longitude": 100.26,
    "Latitude": 26.86,
    "Altitude": 0.0,
    "Speed": 10.0
}
request_id = "102"
res = cloud.send_rpc_reply(data, request_id)
print(res)
# True
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|data|dict|服务相关信息|
|request_id|str|消息id|

**返回值:**

|数据类型|说明|
|:---|---|
|bool|`True` - 成功<br>`False` - 失败|

## 使用示例

```python
from usr.thingsboard import TBDeviceMQTTClient

def cloud_callback(topic, data):
    print("topic: %s, data: %s" % (topic, data))
    # RPC消息应答
    if "rpc" in topic:
        request_id = data["id"]
        data = {}
        cloud.send_rpc_reply(data, request_id)


# 功能模块初始化
cloud_cfg = {
    "host": "xxx",
    "port": 0,
    "username": "xxx",
    "qos": 1,
    "client_id": "xxx",
}
cloud = TBDeviceMQTTClient(**cloud_cfg)

# 设置回调函数
cloud.set_callback(cloud_callback)

# 连接登录服务器
res = cloud.connect()
print(res)
# 0

# 遥测数据上报
data = {
    "Longitude": 100.26,
    "Latitude": 26.86,
    "Altitude": 0.0,
    "Speed": 10.0
}
res = cloud.send_telemetry(data)
print(res)
# True

# 断开服务器连接
res = cloud.disconnect()
print(res)
# True
```
