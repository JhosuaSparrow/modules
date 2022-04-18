# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ujson
import utime
import osTimer
import quecIot

from queue import Queue

from usr.modules.ota import SOTA
from usr.modules.logging import getLogger
from usr.modules.common import CloudObservable, CloudObjectModel

log = getLogger(__name__)


EVENT_CODE = {
    1: {
        10200: "Device authentication succeeded.",
        10420: "Bad request data (connection failed).",
        10422: "Device authenticated (connection failed).",
        10423: "No product information found (connection failed).",
        10424: "PAYLOAD parsing failed (connection failed).",
        10425: "Signature verification failed (connection failed).",
        10426: "Bad authentication version (connection failed).",
        10427: "Invalid hash information (connection failed).",
        10430: "PK changed (connection failed).",
        10431: "Invalid DK (connection failed).",
        10432: "PK does not match authentication version (connection failed).",
        10450: "Device internal error (connection failed).",
        10466: "Boot server address not found (connection failed).",
        10500: "Device authentication failed (an unknown exception occurred in the system).",
        10300: "Other errors.",
    },
    2: {
        10200: "Access is successful.",
        10430: "Incorrect device key (connection failed).",
        10431: "Device is disabled (connection failed).",
        10450: "Device internal error (connection failed).",
        10471: "Implementation version not supported (connection failed).",
        10473: "Abnormal access heartbeat (connection timed out).",
        10474: "Network exception (connection timed out).",
        10475: "Server changes.",
        10476: "Abnormal connection to AP.",
        10500: "Access failed (an unknown exception occurred in the system).",
    },
    3: {
        10200: "Subscription succeeded.",
        10300: "Subscription failed.",
    },
    4: {
        10200: "Transparent data sent successfully.",
        10210: "Object model data sent successfully.",
        10220: "Positioning data sent successfully.",
        10300: "Failed to send transparent data.",
        10310: "Failed to send object model data.",
        10320: "Failed to send positioning data.",
    },
    5: {
        10200: "Receive transparent data.",
        10210: "Receive data from the object model.",
        10211: "Received object model query command.",
        10473: "Received data but the length exceeds the module buffer limit, receive failed.",
        10428: "The device receives too much buffer and causes current limit.",
    },
    6: {
        10200: "Logout succeeded (disconnection succeeded).",
    },
    7: {
        10700: "New OTA plain.",
        10701: "The module starts to download.",
        10702: "Package download.",
        10703: "Package download complete.",
        10704: "Package update.",
        10705: "Firmware update complete.",
        10706: "Failed to update firmware.",
        10707: "Received confirmation broadcast.",
    },
    8: {
        10428: "High-frequency messages on the device cause current throttling.",
        10429: "Exceeds the number of activations per device or daily requests current limit.",
    }
}


class QuecObjectModel(CloudObjectModel):
    """This class is queccloud object model

    This class extend CloudObjectModel

    Attribute:
        items:
            - object model dictionary
            - data format:
            {
                "event": {
                    "name": "event",
                    "id": "",
                    "perm": "",
                    "struct_info": {
                        "name": "struct",
                        "id": "",
                        "struct_info": {
                            "key": {
                                "name": "key"
                            }
                        },
                    },
                },
                "property": {
                    "name": "event",
                    "id": "",
                    "perm": "",
                    "struct_info": {}
                }
            }
        items_id:
            - queccloud object model id and name map
            - data format
            {
                4: "energy",
                9: "power_switch",
                23: "phone_num",
            }
    """

    def __init__(self, om_file="/usr/quec_object_model.json"):
        super().__init__(om_file)
        self.items_id = {}
        self.init()

    def init(self):
        with open(self.om_file, "rb") as f:
            cloud_object_model = ujson.load(f)
            for om_type in cloud_object_model.keys():
                if om_type not in ("events", "properties"):
                    continue
                for om_item in cloud_object_model[om_type]:
                    om_key = om_item["code"]
                    om_key_id = om_item["id"]
                    om_key_perm = om_item["subType"].lower()
                    self.set_item(om_type, om_key, om_key_id, om_key_perm)

                    struct_info_list = []
                    event_out_put = []
                    if om_type == "properties":
                        if om_item["dataType"] == "STRUCT":
                            struct_info_list = om_item["specs"]
                    elif om_type == "events":
                        if om_item.get("outputData"):
                            event_out_put = [int(struct_item.get("$ref", "").split("/")[-1]) for struct_item in om_item["outputData"]]

                    for struct_info in struct_info_list:
                        struct_key = struct_info["code"]
                        struct_key_id = struct_info["id"]
                        struct_key_struct = {}
                        if struct_info["dataType"] == "STRUCT":
                            for struct_key_struct_key in struct_info["dataType"]["specs"]:
                                struct_key_struct[struct_key_struct_key["identifier"]] = {
                                    "name": struct_key_struct_key["identifier"]
                                }
                        self.set_item_struct(
                            om_type, om_key, struct_key,
                            struct_key_id=struct_key_id,
                            struct_key_struct=struct_key_struct
                        )

                    for property_id in event_out_put:
                        struct_key = self.items_id.get(property_id, "")
                        struct_key_id = property_id
                        struct_key_struct = self.items.get(struct_key, {}).get("struct_info", {})
                        self.set_item_struct(
                            om_type, om_key, struct_key,
                            struct_key_id=struct_key_id,
                            struct_key_struct=struct_key_struct
                        )

    def __set_items_id(self, om_key, om_key_id):
        """Set object model id, name to items_id

        Parameter:
            om_key: object model name
            om_key_id: object model id

        Return:
            True: Success
            False: Falied
        """
        self.items_id[om_key_id] = om_key
        return True

    def __del_items_id(self, om_type, om_key):
        """Delete object model id, name from items_id

        Parameter:
            om_type: object model type, `event` or `property`
            om_key: object model name

        Return:
            True: Success
            False: Falied
        """
        if self.items.get(om_type) is not None:
            if self.items[om_type].get(om_key):
                om_key_id = self.items[om_type][om_key]["id"]
                self.items_id.pop(om_key_id)
        return True

    def set_item(self, om_type, om_key, om_key_id, om_key_perm):
        """Set object model item to items
        This function extend CloudObjectModel.set_item and add __set_items_id function

        Return:
            True: Success
            False: Falied
        """
        if super().set_item(om_type, om_key, om_key_id=om_key_id, om_key_perm=om_key_perm):
            self.__set_items_id(om_key, om_key_id)
            return True
        return False

    def del_item(self, om_type, om_key):
        """Delete object model item from items
        This function extend CloudObjectModel.del_item and add __del_items_id function

        Return:
            True: Success
            False: Falied
        """
        if super().del_item(om_type, om_key):
            self.__del_items_id(om_type, om_key)
            return True
        return False


class QuecThing(CloudObservable):
    """This is a class for queccloud iot.

    This class extend CloudObservable.

    This class has the following functions:
        1. Cloud connect and disconnect
        2. Publish data to cloud
        3. Monitor data from cloud by event callback

    Run step:
        1. cloud = QuecThing(pk, ps, dk, ds, server)
        2. cloud.addObserver(RemoteSubscribe)
        3. cloud.set_object_model(QuecObjectModel)
        4. cloud.init()
        5. cloud.post_data(data)
        6. cloud.close()
    """

    def __init__(self, pk, ps, dk, ds, server, life_time=120, mcu_name="", mcu_version=""):
        """
        1. Init parent class CloudObservable
        2. Init cloud connect params
        """
        super().__init__()
        self.__pk = pk
        self.__ps = ps
        self.__dk = dk
        self.__ds = ds
        self.__server = server
        self.__life_time = life_time
        self.__mcu_name = mcu_name
        self.__mcu_version = mcu_version
        self.__object_model = None

        self.__file_size = 0
        self.__md5_value = ""
        self.__post_result_wait_queue = Queue(maxsize=16)
        self.__quec_timer = osTimer()

    def __rm_empty_data(self, data):
        """Remove post success data item from data"""
        for k, v in data.items():
            if not v:
                del data[k]

    def __quec_timer_cb(self, args):
        """osTimer callback to break waiting of get publish result"""
        self.__put_post_res(False)

    def __get_post_res(self):
        """Get publish result"""
        self.__quec_timer.start(1000 * 10, 0, self.__quec_timer_cb)
        res = self.__post_result_wait_queue.get()
        self.__quec_timer.stop()
        return res

    def __put_post_res(self, res):
        """Save publish result to queue"""
        if self.__post_result_wait_queue.size() >= 16:
            self.__post_result_wait_queue.get()
        self.__post_result_wait_queue.put(res)

    def __sota_download_info(self, size, md5_value):
        self.__file_size = size
        self.__md5_value = md5_value

    def __sota_upgrade_start(self, start_addr, need_download_size):
        download_size = 0
        sota_mode = SOTA()
        while need_download_size != 0:
            readsize = 4096
            if (readsize > need_download_size):
                readsize = need_download_size
            updateFile = quecIot.mcuFWDataRead(start_addr, readsize)
            sota_mode.write_update_data(updateFile)
            log.debug("Download File Size: %s" % readsize)
            need_download_size -= readsize
            start_addr += readsize
            download_size += readsize
            if (download_size == self.__file_size):
                log.debug("File Download Success, Update Start.")
                self.ota_action(3)
                if sota_mode.check_md5(self.__md5_value):
                    if sota_mode.file_update():
                        sota_mode.sota_set_flag()
                        log.debug("File Update Success, Power Restart.")
                    else:
                        log.debug("File Update Failed, Power Restart.")
                break
            else:
                self.ota_action(2)

        res_data = ("object_model", [("power_restart", 1)])
        self.notifyObservers(self, *res_data)

    def __data_format(self, k, v):
        """Publish data format by AliObjectModel

        Parameter:
            k: object model name
            v: object model value

        return:
            {
                "object_model_id": object_model_value
            }

        e.g.:
        k:
            "sos_alert"

        v:
            {"local_time": 1649995898000}

        return data:
            {
                6: {
                    19: 1649995898000
                }
            }
        """
        # log.debug("k: %s, v: %s" % (k, v))
        k_id = None
        struct_info = {}
        if self.__object_model.items["events"].get(k):
            k_id = self.__object_model.items["events"][k]["id"]
            if isinstance(self.__object_model.items["events"][k]["struct_info"], dict):
                struct_info = self.__object_model.items["events"][k]["struct_info"]
        elif self.__object_model.items["properties"].get(k):
            k_id = self.__object_model.items["properties"][k]["id"]
            if isinstance(self.__object_model.items["properties"][k]["struct_info"], dict):
                struct_info = self.__object_model.items["properties"][k]["struct_info"]
        else:
            return False

        if isinstance(v, dict):
            nv = {}
            for ik, iv in v.items():
                if struct_info.get(ik):
                    nv[struct_info[ik]["id"]] = iv
                else:
                    nv[ik] = iv
            v = nv

        return {k_id: v}

    def __event_cb(self, data):
        """Queccloud downlink message callback

        Parameter:
            data: response dictionary info, all event info see `EVENT_CODE`
            data format: (`event_code`, `errcode`, `event_data`)
                - `event_code`: event code
                - `errcode`: detail code
                - `event_data`: event data info, data type: bytes or dict
        """
        res_data = ()
        event = data[0]
        errcode = data[1]
        eventdata = b""
        if len(data) > 2:
            eventdata = data[2]
        log.info("Event[%s] ErrCode[%s] Msg[%s] EventData[%s]" % (event, errcode, EVENT_CODE.get(event, {}).get(errcode, ""), eventdata))

        if event == 3:
            if errcode == 10200:
                if eventdata:
                    file_info = eval(eventdata)
                    log.info("OTA File Info: componentNo: %s, sourceVersion: %s, targetVersion: %s, "
                             "batteryLimit: %s, minSignalIntensity: %s, minSignalIntensity: %s" % file_info)
        elif event == 4:
            if errcode == 10200:
                self.__put_post_res(True)
            elif errcode == 10210:
                self.__put_post_res(True)
            elif errcode == 10220:
                self.__put_post_res(True)
            elif errcode == 10300:
                self.__put_post_res(False)
            elif errcode == 10310:
                self.__put_post_res(False)
            elif errcode == 10320:
                self.__put_post_res(False)
        elif event == 5:
            if errcode == 10200:
                # TODO: Data Type Passthrough (Not Support Now).
                res_data = ("raw_data", eventdata)
            elif errcode == 10210:
                dl_data = [(self.__object_model.items_id[k], v.decode() if isinstance(v, bytes) else v) for k, v in eventdata.items()]
                res_data = ("object_model", dl_data)
            elif errcode == 10211:
                # eventdata[0] is pkgId.
                object_model_ids = eventdata[1]
                object_model_val = [self.__object_model.items_id[i] for i in object_model_ids if self.__object_model.items_id.get(i)]
                res_data = ("query", object_model_val)
                pass
        elif event == 7:
            if errcode == 10700:
                if eventdata:
                    file_info = eval(eventdata)
                    log.info("OTA File Info: componentNo: %s, sourceVersion: %s, targetVersion: %s, "
                             "batteryLimit: %s, minSignalIntensity: %s, useSpace: %s" % file_info)
                    res_data = ("object_model", [("ota_status", (file_info[0], 1, file_info[2]))])
            elif errcode == 10701:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10702:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10703:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10704:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10705:
                res_data = ("object_model", [("ota_status", (None, 3, None))])
            elif errcode == 10706:
                res_data = ("object_model", [("ota_status", (None, 4, None))])

        if res_data:
            self.notifyObservers(self, *res_data)

        if event == 7 and errcode == 10701 and eventdata:
            file_info = eval(eventdata)
            self.__sota_download_info(int(file_info[1]), file_info[2])
        if event == 7 and errcode == 10703 and eventdata:
            file_info = eval(eventdata)
            log.info("OTA File Info: componentNo: %s, length: %s, md5: %s, crc: %s" % file_info)
            self.__sota_upgrade_start(int(file_info[2]), int(file_info[3]))

    def set_object_model(self, object_model):
        """Register QuecObjectModel to this class"""
        if object_model and isinstance(object_model, QuecObjectModel):
            self.__object_model = object_model
            return True
        return False

    def init(self, enforce=False):
        """queccloud connect

        Parameter:
            enforce:
                True: enfore cloud connect
                False: check connect status, return True if cloud connected

        Return:
            Ture: Success
            False: Failed
        """
        log.debug(
            "[init start] enforce: %s QuecThing Work State: %s, quecIot.getConnmode(): %s"
            % (enforce, quecIot.getWorkState(), quecIot.getConnmode())
        )
        log.debug("[init start] PK: %s, PS: %s, DK: %s, DS: %s, SERVER: %s" % (self.__pk, self.__ps, self.__dk, self.__ds, self.__server))
        if enforce is False:
            if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
                return True

        quecIot.init()
        quecIot.setEventCB(self.__event_cb)
        quecIot.setProductinfo(self.__pk, self.__ps)
        if self.__dk or self.__ds:
            quecIot.setDkDs(self.__dk, self.__ds)
        quecIot.setServer(1, self.__server)
        quecIot.setLifetime(self.__life_time)
        quecIot.setMcuVersion(self.__mcu_name, self.__mcu_version)
        quecIot.setConnmode(1)

        count = 0
        while quecIot.getWorkState() != 8 and count < 10:
            utime.sleep_ms(200)
            count += 1

        if not self.__ds and self.__dk:
            count = 0
            while count < 3:
                dkds = quecIot.getDkDs()
                if dkds:
                    self.__dk, self.__ds = dkds
                    log.debug("dk: %s, ds: %s" % dkds)
                    break
                count += 1
                utime.sleep(count)

        log.debug("[init over] QuecThing Work State: %s, quecIot.getConnmode(): %s" % (quecIot.getWorkState(), quecIot.getConnmode()))
        if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
            return True
        else:
            return False

    def close(self):
        """queccloud disconnect"""
        return quecIot.setConnmode(0)

    def post_data(self, data):
        """Publish object model property, event

        Parameter:
            data format:
            {
                "phone_num": "123456789",
                "energy": 100,
                "gps": [
                    "$GNGGA,XXX"
                    "$GNVTG,XXX"
                    "$GNRMC,XXX"
                ],
            }

        Return:
            Ture: Success
            False: Failed
        """
        res = True
        # log.debug("post_data: %s" % str(data))
        for k, v in data.items():
            om_data = self.__data_format(k, v)
            if om_data is not False:
                if v is not None:
                    phymodelReport_res = quecIot.phymodelReport(1, om_data)
                    if not phymodelReport_res:
                        res = False
                        break
                else:
                    continue
            elif k == "gps":
                locReportOutside_res = quecIot.locReportOutside(v)
                if not locReportOutside_res:
                    res = False
                    break
            elif k == "non_gps":
                locReportInside_res = quecIot.locReportInside(v)
                if not locReportInside_res:
                    res = False
                    break
            else:
                v = {}
                continue

            res = self.__get_post_res()
            if res:
                v = {}
            else:
                res = False
                break

        self.__rm_empty_data(data)
        return res

    def ota_request(self, mp_mode=0):
        """Publish mcu and firmware ota plain request

        Return:
            Ture: Success
            False: Failed
        """
        return quecIot.otaRequest(mp_mode) if mp_mode in (0, 1) else False

    def ota_action(self, action=1, module=None):
        """Publish ota upgrade start or cancel ota upgrade

        Parameter:
            action: confirm or cancel upgrade
                - 0: cancel upgrade
                - 1: confirm upgrade

            module: useless

        Return:
            Ture: Success
            False: Failed
        """
        return quecIot.otaAction(action) if action in (0, 1, 2, 3) else False
