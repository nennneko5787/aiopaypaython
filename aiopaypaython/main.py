import datetime
from uuid import uuid4

import httpx
from . import pkce
from bs4 import BeautifulSoup


class PayPayError(Exception):
    pass


class PayPayLoginError(Exception):
    pass


class NetWorkError(Exception):
    pass


class PayPayNetWorkError(Exception):
    pass


class PayPay:
    def __init__(
        self,
        proxy: dict = None,
    ):
        self.proxy = proxy
        self.session = httpx.AsyncClient(proxy=proxy)

    async def initialize(
        self,
        phone: str = None,
        password: str = None,
        device_uuid: str = None,
        client_uuid: str = str(uuid4()).upper(),
        access_token: str = None,
    ):

        if phone and "-" in phone:
            phone = phone.replace("-", "")

        if device_uuid:
            self.device_uuid = device_uuid
        else:
            self.device_uuid = str(uuid4()).upper()

        self.client_uuid = client_uuid
        self.params = {"payPayLang": "ja"}
        try:
            iosstore = await self.session.get(
                "https://apps.apple.com/jp/app/paypay-%E3%83%9A%E3%82%A4%E3%83%9A%E3%82%A4/id1435783608",
            )
        except Exception as e:
            raise NetWorkError(e)

        self.version = (
            BeautifulSoup(iosstore.text, "html.parser")
            .find(class_="l-column small-6 medium-12 whats-new__latest__version")
            .text.split()[1]
        )
        self.headers = {
            "Host": "app4.paypay.ne.jp",
            "Accept-Charset": "UTF-8",
            "Client-Mode": "NORMAL",
            "Client-OS-Release-Version": "16.7.5",
            "Client-OS-Type": "IOS",
            "Client-OS-Version": "16.7.5",
            "Client-Type": "PAYPAYAPP",
            "Client-UUID": client_uuid,
            "Client-Version": self.version,
            "Device-Brand-Name": "apple",
            "Device-Hardware-Name": "iPhone10,1",
            "Device-Manufacturer-Name": "apple",
            "Device-Name": "iPhone10,1",
            "Device-UUID": self.device_uuid,
            "Is-Emulator": "false",
            "Network-Status": "WIFI",
            "System-Locale": "ja",
            "Timezone": "Asia/Tokyo",
            "User-Agent": f"PaypayApp/{self.version} iOS16.7.5 Ktor",
        }
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
            self.access_token = access_token
        elif phone:
            self.access_token = None
            self.refresh_token = None
            self.timestamp = None
            self.code_verifier, self.code_challenge = pkce.generate_pkce_pair(43)
            payload = {
                "clientId": "pay2-mobile-app-client",
                "clientAppVersion": self.version,
                "clientOsVersion": "16.7.5",
                "clientOsType": "IOS",
                "redirectUri": "paypay://oauth2/callback",
                "responseType": "code",
                "state": pkce.generate_code_verifier(43),
                "codeChallenge": self.code_challenge,
                "codeChallengeMethod": "S256",
                "scope": "REGULAR",
                "tokenVersion": "v2",
                "prompt": "",
                "uiLocales": "ja",
            }
            par = await self.session.post(
                "https://app4.paypay.ne.jp/bff/v2/oauth2/par?payPayLang=ja",
                headers=self.headers,
                data=payload,
            )
            try:
                par = par.json()
            except:
                raise PayPayNetWorkError("日本以外からは接続できません")

            if par["header"]["resultCode"] != "S0000":
                raise PayPayLoginError(par)

            headers = {
                "Host": "www.paypay.ne.jp",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari jp.pay2.app.ios/{self.version}",
                "Is-Emulator": "false",
                "Accept-Language": "ja-jp",
            }
            await self.session.get(
                f"https://www.paypay.ne.jp/portal/api/v2/oauth2/authorize?request_uri={par['payload']['requestUri']}&client_id=pay2-mobile-app-client",
                headers=headers,
            )

            headers = {
                "Host": "www.paypay.ne.jp",
                "Accept": "application/json, text/plain, */*",
                "Client-Id": "pay2-mobile-app-client",
                "Client-Type": "PAYPAYAPP",
                "Accept-Encoding": "gzip, deflate, br",
                "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari jp.pay2.app.ios/{self.version}",
                "Accept-Language": "ja-jp",
                "Referer": "https://www.paypay.ne.jp/portal/oauth2/sign-in?client_id=pay2-mobile-app-client&mode=landing",
            }
            par_check = (
                await self.session.get(
                    "https://www.paypay.ne.jp/portal/api/v2/oauth2/par/check",
                    headers=headers,
                )
            ).json()
            if par_check["header"]["resultCode"] != "S0000":
                raise PayPayLoginError(par_check)

            self.timestamp = str(
                round(
                    datetime.datetime.now(
                        datetime.timezone(datetime.timedelta(hours=9))
                    ).timestamp()
                )
            )
            headers = {
                "Host": "www.paypay.ne.jp",
                "Content-Type": "application/json",
                "Client-App-Load-Start": self.timestamp,
                "Client-Os-Version": "16.7.5",
                "Accept": "application/json, text/plain, */*",
                "Client-Type": "PAYPAYAPP",
                "Client-Id": "pay2-mobile-app-client",
                "Client-Version": self.version,
                "Accept-Language": "ja-jp",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://www.paypay.ne.jp",
                "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari jp.pay2.app.ios/{self.version}",
                "Referer": "https://www.paypay.ne.jp/portal/oauth2/sign-in?client_id=pay2-mobile-app-client&mode=landing",
                "Client-Os-Type": "IOS",
            }
            phonepas = {
                "username": phone,
                "password": password,
                "signInAttemptCount": 1,
            }
            signin = (
                await self.session.post(
                    "https://www.paypay.ne.jp/portal/api/v2/oauth2/sign-in/password",
                    headers=headers,
                    json=phonepas,
                )
            ).json()
            if signin["header"]["resultCode"] != "S0000":
                raise PayPayLoginError(signin)

            if device_uuid:
                try:
                    uri = (
                        signin["payload"]["redirectUrl"]
                        .replace("paypay://oauth2/callback?", "")
                        .split("&")
                    )
                except:
                    raise PayPayLoginError("登録されていないDevice-UUID")

                headers = {
                    "Client-Version": self.version,
                    "Device-Uuid": self.device_uuid,
                    "System-Locale": "en",
                    "User-Agent": f"PaypayApp/{self.version} iOS16.7.5 Ktor",
                    "Cache-Control": "no-cache",
                    "Is-Emulator": "false",
                    "Device-Name": "iPhone10,1",
                    "Device-Hardware-Name": "iPhone10,1",
                    "Client-Os-Version": "16.7.5",
                    "Device-Brand-Name": "apple",
                    "Client-Os-Release-Version": "16.7.5",
                    "Client-Os-Type": "IOS",
                    "Client-Mode": "NORMAL",
                    "Client-Type": "PAYPAYAPP",
                    "Timezone": "Asia/Tokyo",
                    "Accept-Language": "ja-jp",
                    "Device-Manufacturer-Name": "apple",
                    "Accept-Charset": "UTF-8",
                    "Device-Latlon-Timestamp": "",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "*/*",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Network-Status": "WIFI",
                    "Client-Uuid": client_uuid,
                }
                confirm_data = {
                    "clientId": "pay2-mobile-app-client",
                    "redirectUri": "paypay://oauth2/callback",
                    "code": uri[0].replace("code=", ""),
                    "codeVerifier": self.code_verifier,
                }
                get_token = (
                    await self.session.post(
                        "https://app4.paypay.ne.jp/bff/v2/oauth2/token",
                        headers=headers,
                        data=confirm_data,
                        params=self.params,
                    )
                ).json()
                if get_token["header"]["resultCode"] != "S0000":
                    raise PayPayLoginError(get_token)

                self.access_token = get_token["payload"]["accessToken"]  # 90日もつよ
                self.refresh_token = get_token["payload"]["refreshToken"]
                self.headers["Authorization"] = f"Bearer {self.access_token}"

            else:

                code_update = (
                    await self.session.post(
                        "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/update",
                        headers=headers,
                        json={},
                    )
                ).json()
                if code_update["header"]["resultCode"] != "S0000":
                    raise PayPayLoginError(code_update)

                headers["Referer"] = (
                    "https://www.paypay.ne.jp/portal/oauth2/verification-method?client_id=pay2-mobile-app-client&mode=navigation-2fa"
                )
                parameter = {
                    "params": {
                        "extension_id": "user-main-2fa-v1",
                        "data": {
                            "type": "SELECT_FLOW",
                            "payload": {
                                "flow": "OTL",
                                "sign_in_method": "MOBILE",
                                "base_url": "https://www.paypay.ne.jp/portal/oauth2/l",
                            },
                        },
                    }
                }
                send_url = (
                    await self.session.post(
                        "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/update",
                        headers=headers,
                        json=parameter,
                    )
                ).json()
                if send_url["header"]["resultCode"] != "S0000":
                    raise PayPayLoginError(send_url)

    async def login(self, url: str) -> dict:
        if "https://" in url:
            url = url.replace("https://www.paypay.ne.jp/portal/oauth2/l?id=", "")
        headers = {
            "Host": "www.paypay.ne.jp",
            "Content-Type": "application/json",
            "Client-App-Load-Start": self.timestamp,
            "Client-Os-Version": "16.7.5",
            "Accept": "application/json, text/plain, */*",
            "Client-Type": "PAYPAYAPP",
            "Client-Id": "pay2-mobile-app-client",
            "Client-Version": self.version,
            "Accept-Language": "ja-jp",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.paypay.ne.jp",
            "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari jp.pay2.app.ios/{self.version}",
            "Referer": "https://www.paypay.ne.jp/portal/oauth2/l?id=7FXQCJ&client_id=pay2-mobile-app-client",
            "Client-Os-Type": "IOS",
        }
        confirm_url = (
            await self.session.post(
                "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/sign-in/2fa/otl/verify",
                headers=headers,
                json={"code": url},
            )
        ).json()
        if confirm_url["header"]["resultCode"] != "S0000":
            raise PayPayLoginError(confirm_url)

        parameter = {
            "params": {
                "extension_id": "user-main-2fa-v1",
                "data": {"type": "COMPLETE_OTL", "payload": None},
            }
        }
        get_uri = (
            await self.session.post(
                "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/update",
                headers=headers,
                json=parameter,
            )
        ).json()
        if get_uri["header"]["resultCode"] != "S0000":
            raise PayPayLoginError(get_uri)

        try:
            uri = (
                get_uri["payload"]["redirect_uri"]
                .replace("paypay://oauth2/callback?", "")
                .split("&")
            )
        except:
            raise PayPayLoginError(
                "redirect_uriが見つかりませんでした\n" + str(get_uri)
            )

        headers = {
            "Client-Version": self.version,
            "Device-Uuid": self.device_uuid,
            "System-Locale": "en",
            "User-Agent": f"PaypayApp/{self.version} iOS16.7.5 Ktor",
            "Cache-Control": "no-cache",
            "Is-Emulator": "false",
            "Device-Name": "iPhone10,1",
            "Device-Hardware-Name": "iPhone10,1",
            "Client-Os-Version": "16.7.5",
            "Device-Brand-Name": "apple",
            "Client-Os-Release-Version": "16.7.5",
            "Client-Os-Type": "IOS",
            "Client-Mode": "NORMAL",
            "Client-Type": "PAYPAYAPP",
            "Timezone": "Asia/Tokyo",
            "Accept-Language": "ja-jp",
            "Device-Manufacturer-Name": "apple",
            "Accept-Charset": "UTF-8",
            "Device-Latlon-Timestamp": "",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Network-Status": "WIFI",
            "Client-Uuid": self.client_uuid,
        }
        confirm_data = {
            "clientId": "pay2-mobile-app-client",
            "redirectUri": "paypay://oauth2/callback",
            "code": uri[0].replace("code=", ""),
            "codeVerifier": self.code_verifier,
        }
        get_token = (
            await self.session.post(
                "https://app4.paypay.ne.jp/bff/v2/oauth2/token",
                headers=headers,
                data=confirm_data,
                params=self.params,
            )
        ).json()
        if get_token["header"]["resultCode"] != "S0000":
            raise PayPayLoginError(get_token)

        self.access_token = get_token["payload"]["accessToken"]  # 90日もつよ
        self.refresh_token = get_token["payload"]["refreshToken"]
        self.headers["Authorization"] = f"Bearer {self.access_token}"

        return get_token

    async def resend_url(self) -> dict:
        if not self.timestamp:
            raise PayPayLoginError("まずはワンタイムURLを送信してください")
        headers = {
            "Host": "www.paypay.ne.jp",
            "Content-Type": "application/json",
            "Client-App-Load-Start": self.timestamp,
            "Client-Os-Version": "16.7.5",
            "Accept": "application/json, text/plain, */*",
            "Client-Type": "PAYPAYAPP",
            "Client-Id": "pay2-mobile-app-client",
            "Client-Version": self.version,
            "Accept-Language": "ja-jp",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.paypay.ne.jp",
            "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari jp.pay2.app.ios/{self.version}",
            "Referer": "https://www.paypay.ne.jp/portal/oauth2/otl-request?client_id=pay2-mobile-app-client&mode=navigation-2fa",
            "Client-Os-Type": "IOS",
        }
        parameter = {
            "params": {
                "extension_id": "user-main-2fa-v1",
                "data": {
                    "type": "SELECT_FLOW",
                    "payload": {
                        "flow": "OTL",
                        "sign_in_method": "MOBILE",
                        "base_url": "https://www.paypay.ne.jp/portal/oauth2/l",
                    },
                },
            }
        }
        resend_url = (
            await self.session.post(
                "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/update",
                headers=headers,
                json=parameter,
            )
        ).json()
        if resend_url["header"]["resultCode"] != "S0000":
            raise PayPayLoginError(resend_url)

        return resend_url

    async def token_refresh(self, refresh_token: str) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        refdata = {
            "clientId": "pay2-mobile-app-client",
            "refreshToken": refresh_token,
            "tokenVersion": "v2",
        }
        refresh = (
            await self.session.post(
                "https://app4.paypay.ne.jp/bff/v2/oauth2/refresh",
                headers=self.headers,
                data=refdata,
            )
        ).json()

        if (
            refresh["header"]["resultCode"] == "S0001"
            or refresh["header"]["resultCode"] == "S1003"
        ):
            raise PayPayLoginError(refresh)

        if refresh["header"]["resultCode"] == "S0003":
            raise PayPayLoginError(refresh)

        if refresh["header"]["resultCode"] != "S0000":
            raise PayPayError(refresh)

        self.access_token = refresh["payload"]["accessToken"]  # 90日もつよ
        self.refresh_token = refresh["payload"]["refreshToken"]
        self.headers["Authorization"] = f"Bearer {refresh['payload']['accessToken']}"

        return refresh

    async def get_history(self, size: int = 20, cashback: bool = False) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        params = {"pageSize": size, "payPayLang": "ja"}
        if cashback:
            params["orderTypes"] = "CASHBACK"
        history = (
            await self.session.get(
                f"https://app4.paypay.ne.jp/bff/v3/getPaymentHistory",
                params=params,
                headers=self.headers,
            )
        ).json()

        if history["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(history)

        if history["header"]["resultCode"] != "S0000":
            raise PayPayError(history)

        return history

    async def get_balance(self) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        params = {
            "includePendingBonusLite": "false",
            "includePending": "true",
            "includePreAuth": "true",
            "noCache": "true",
            "includeKycInfo": "true",
            "payPayLang": "ja",
        }
        balance = (
            await self.session.get(
                "https://app4.paypay.ne.jp/bff/v1/getBalanceInfo",
                headers=self.headers,
                params=params,
            )
        ).json()

        if balance["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(balance)

        if balance["header"]["resultCode"] != "S0000":
            raise PayPayError(balance)

        try:
            self.money = balance["payload"]["walletDetail"]["emoneyBalanceInfo"][
                "balance"
            ]
        except:
            self.money = None
        self.money_light = balance["payload"]["walletDetail"]["prepaidBalanceInfo"][
            "balance"
        ]
        self.all_balance = balance["payload"]["walletSummary"]["allTotalBalanceInfo"][
            "balance"
        ]
        self.useable_balance = balance["payload"]["walletSummary"][
            "usableBalanceInfoWithoutCashback"
        ]["balance"]
        self.point = balance["payload"]["walletDetail"]["cashBackBalanceInfo"][
            "balance"
        ]

        return balance

    async def link_check(self, url: str, web: bool = False) -> dict:
        if "https://" in url:
            url = url.replace("https://pay.paypay.ne.jp/", "")
        if web:
            headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Content-Type": "application/json",
            }
            link_info = (
                await self.session.get(
                    f"https://www.paypay.ne.jp/app/v2/p2p-api/getP2PLinkInfo?verificationCode={url}",
                    headers=headers,
                )
            ).json()
        else:
            if not self.access_token:
                raise PayPayLoginError("まずはログインしてください")

            params = {"verificationCode": url, "payPayLang": "ja"}
            link_info = (
                await self.session.get(
                    "https://app4.paypay.ne.jp/bff/v2/getP2PLinkInfo",
                    headers=self.headers,
                    params=params,
                )
            ).json()

        if link_info["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(link_info)

        if link_info["header"]["resultCode"] != "S0000":
            raise PayPayError(link_info)

        self.link_sender_name = link_info["payload"]["sender"]["displayName"]
        self.link_sender_external_id = link_info["payload"]["sender"]["externalId"]
        self.link_sender_icon = link_info["payload"]["sender"]["photoUrl"]
        self.link_order_id = link_info["payload"]["pendingP2PInfo"]["orderId"]
        self.link_chat_room_id = link_info["payload"]["message"]["chatRoomId"]
        self.link_amount = link_info["payload"]["pendingP2PInfo"]["amount"]
        self.link_status = link_info["payload"]["message"]["data"]["status"]
        self.link_money_light = link_info["payload"]["message"]["data"][
            "subWalletSplit"
        ]["senderPrepaidAmount"]
        self.link_money = link_info["payload"]["message"]["data"]["subWalletSplit"][
            "senderEmoneyAmount"
        ]
        self.link_has_password = link_info["payload"]["pendingP2PInfo"]["isSetPasscode"]

        return link_info

    async def link_receive(
        self, url: str, password: str = None, link_info: dict = None
    ) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        if "https://" in url:
            url = url.replace("https://pay.paypay.ne.jp/", "")
        if not link_info:
            params = {"verificationCode": url, "payPayLang": "ja"}
            link_info = (
                await self.session.get(
                    "https://app4.paypay.ne.jp/bff/v2/getP2PLinkInfo",
                    headers=self.headers,
                    params=params,
                )
            ).json()

        payload = {
            "requestId": str(uuid4()).upper(),
            "orderId": link_info["payload"]["pendingP2PInfo"]["orderId"],
            "verificationCode": url,
            "passcode": None,
            "senderMessageId": link_info["payload"]["message"]["messageId"],
            "senderChannelUrl": link_info["payload"]["message"]["chatRoomId"],
        }
        if link_info["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(link_info)

        if link_info["header"]["resultCode"] != "S0000":
            raise PayPayError(link_info)

        if link_info["payload"]["orderStatus"] != "PENDING":
            raise PayPayError(
                "すでに 受け取り / 辞退 / キャンセル されているリンクです"
            )

        if link_info["payload"]["pendingP2PInfo"]["isSetPasscode"] and password == None:
            raise PayPayError("このリンクにはパスワードが設定されています")

        if link_info["payload"]["pendingP2PInfo"]["isSetPasscode"]:
            payload["passcode"] = password

        receive = await self.session.post(
            "https://app4.paypay.ne.jp/bff/v2/acceptP2PSendMoneyLink",
            headers=self.headers,
            json=payload,
            params=self.params,
        )
        try:
            receive = receive.json()
        except:
            raise PayPayNetWorkError("日本以外からは接続できません")

        if receive["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(receive)

        if receive["header"]["resultCode"] != "S0000":
            raise PayPayError(receive)

        return receive

    async def link_reject(self, url: str, link_info: dict = None) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        if "https://" in url:
            url = url.replace("https://pay.paypay.ne.jp/", "")
        if not link_info:
            params = {"verificationCode": url, "payPayLang": "ja"}
            link_info = (
                await self.session.get(
                    "https://app4.paypay.ne.jp/bff/v2/getP2PLinkInfo",
                    headers=self.headers,
                    params=params,
                )
            ).json()

        payload = {
            "requestId": str(uuid4()).upper(),
            "orderId": link_info["payload"]["pendingP2PInfo"]["orderId"],
            "verificationCode": url,
            "senderMessageId": link_info["payload"]["message"]["messageId"],
            "senderChannelUrl": link_info["payload"]["message"]["chatRoomId"],
        }
        if link_info["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(link_info)

        if link_info["header"]["resultCode"] != "S0000":
            raise PayPayError(link_info)

        if link_info["payload"]["orderStatus"] != "PENDING":
            raise PayPayError(
                "すでに 受け取り / 辞退 / キャンセル されているリンクです"
            )

        reject = (
            await self.session.post(
                "https://app4.paypay.ne.jp/bff/v2/rejectP2PSendMoneyLink",
                headers=self.headers,
                json=payload,
                params=self.params,
            )
        ).json()

        if reject["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(reject)

        if reject["header"]["resultCode"] != "S0000":
            raise PayPayError(reject)

        return reject

    async def link_cancel(self, url: str, link_info: dict = None) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        if "https://" in url:
            url = url.replace("https://pay.paypay.ne.jp/", "")
        if not link_info:
            params = {"verificationCode": url, "payPayLang": "ja"}
            link_info = (
                await self.session.get(
                    "https://app4.paypay.ne.jp/bff/v2/getP2PLinkInfo",
                    headers=self.headers,
                    params=params,
                )
            ).json()

        payload = {
            "orderId": link_info["payload"]["pendingP2PInfo"]["orderId"],
            "requestId": str(uuid4()).upper(),
            "verificationCode": url,
        }
        if link_info["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(link_info)

        if link_info["header"]["resultCode"] != "S0000":
            raise PayPayError(link_info)

        if link_info["payload"]["orderStatus"] != "PENDING":
            raise PayPayError(
                "すでに 受け取り / 辞退 / キャンセル されているリンクです"
            )

        cancel = (
            await self.session.post(
                "https://app4.paypay.ne.jp/p2p/v1/cancelP2PSendMoneyLink",
                headers=self.headers,
                json=payload,
                params=self.params,
            )
        ).json()

        if cancel["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(cancel)

        if cancel["header"]["resultCode"] != "S0000":
            raise PayPayError(cancel)

        return cancel

    async def create_link(
        self, amount: int, password: str = None, pochibukuro=None
    ) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        payload = {
            "requestId": str(uuid4()).upper(),
            "amount": amount,
            "theme": "default-sendmoney",
            "source": "sendmoney_home_sns",
        }
        if password:
            payload["passcode"] = password
        if pochibukuro:
            payload["theme"] = "pochibukuro"
        create = await self.session.post(
            "https://app4.paypay.ne.jp/bff/v2/executeP2PSendMoneyLink",
            headers=self.headers,
            json=payload,
            params=self.params,
        )
        try:
            create = create.json()
        except:
            raise PayPayNetWorkError("日本以外からは接続できません")

        if create["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(create)

        if create["header"]["resultCode"] != "S0000":
            raise PayPayError(create)

        self.created_link = create["payload"]["link"]
        self.created_chat_room_id = create["payload"]["chatRoomId"]

        return create

    async def send_money(self, amount: int, receiver_id: str) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        payload = {
            "amount": amount,
            "theme": "default-sendmoney",
            "requestId": str(uuid4()).upper(),
            "externalReceiverId": receiver_id,
            "ackRiskError": False,
            "source": "sendmoney_history_chat",
        }
        send = await self.session.post(
            f"https://app4.paypay.ne.jp/bff/v2/executeP2PSendMoney",
            headers=self.headers,
            json=payload,
            params=self.params,
        )
        try:
            send = send.json()
        except:
            raise PayPayNetWorkError("日本以外からは接続できません")

        if send["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(send)

        if send["header"]["resultCode"] != "S0000":
            raise PayPayError(send)

        return send

    async def send_message(self, chat_room_id: str, message: str) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        if not "sendbird_group_channel_" in chat_room_id:
            chat_room_id = "sendbird_group_channel_" + chat_room_id
        payload = {"channelUrl": chat_room_id, "message": message}
        send = (
            await self.session.post(
                "https://app4.paypay.ne.jp/p2p/v1/sendP2PMessage",
                headers=self.headers,
                json=payload,
                params=self.params,
            )
        ).json()

        if send["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(send)

        if send["header"]["resultCode"] != "S0000":
            raise PayPayError(send)

        return send

    async def create_p2pcode(self, amount: int = None) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        payload = {"amount": None, "sessionId": None}
        if amount:
            payload["amount"] = amount
            payload["sessionId"] = str(uuid4())

        p2pcode = (
            await self.session.post(
                "https://app4.paypay.ne.jp/bff/v1/createP2PCode",
                headers=self.headers,
                json=payload,
                params=self.params,
            )
        ).json()

        if p2pcode["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(p2pcode)

        if p2pcode["header"]["resultCode"] != "S0000":
            raise PayPayError(p2pcode)

        self.created_p2pcode = p2pcode["payload"]["p2pCode"]

        return p2pcode

    async def get_profile(self) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        profile = (
            await self.session.get(
                "https://app4.paypay.ne.jp/bff/v2/getProfileDisplayInfo",
                headers=self.headers,
                params={"includeExternalProfileSync": "true", "payPayLang": "ja"},
            )
        ).json()

        if profile["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(profile)

        if profile["header"]["resultCode"] != "S0000":
            raise PayPayError(profile)

        self.name = profile["payload"]["userProfile"]["nickName"]
        self.external_user_id = profile["payload"]["userProfile"]["externalUserId"]
        self.icon = profile["payload"]["userProfile"]["avatarImageUrl"]

        return profile

    async def set_money_priority(self, paypay_money: bool = False) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        if paypay_money:
            setting = {"moneyPriority": "MONEY_FIRST"}
        else:
            setting = {"moneyPriority": "MONEY_LITE_FIRST"}
        smp = (
            await self.session.get(
                "https://app4.paypay.ne.jp/p2p/v1/setMoneyPriority",
                headers=self.headers,
                json=setting,
                params={"payPayLang": "ja"},
            )
        ).json()

        if smp["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(smp)

        if smp["header"]["resultCode"] != "S0000":
            raise PayPayError(smp)

        return smp

    async def get_chat_rooms(self, size: int = 20, last_message: bool = True) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        params = {
            "pageSize": size,
            "customTypes": "P2P_CHAT,P2P_CHAT_INACTIVE,P2P_PUBLIC_GROUP_CHAT,P2P_LINK,P2P_OLD",
            "requiresLastMessage": last_message,
            "payPayLang": "ja",
        }
        getchat = (
            await self.session.get(
                "https://app4.paypay.ne.jp/p2p/v1/getP2PChatRoomListLite",
                headers=self.headers,
                params=params,
            )
        ).json()

        if getchat["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(getchat)

        if getchat["header"]["resultCode"] == "S5000":
            raise PayPayError("チャットルームが見つかりませんでした")

        if getchat["header"]["resultCode"] != "S0000":
            raise PayPayError(getchat)

        return getchat

    async def get_chat_room_messages(
        self, chat_room_id: str, prev: int = 15, next: int = 0, include: bool = False
    ) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        if not "sendbird_group_channel_" in chat_room_id:
            chat_room_id = "sendbird_group_channel_" + chat_room_id

        params = {
            "chatRoomId": chat_room_id,
            "include": include,
            "prev": str(prev),
            "next": str(next),
            "payPayLang": "ja",
        }
        getchat = (
            await self.session.get(
                "https://app4.paypay.ne.jp/bff/v1/getP2PMessageList",
                headers=self.headers,
                params=params,
            )
        ).json()

        if getchat["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(getchat)

        if getchat["header"]["resultCode"] == "S5000":
            raise PayPayError("チャットルームが見つかりませんでした")

        if getchat["header"]["resultCode"] != "S0000":
            raise PayPayError(getchat)

        return getchat

    async def create_paymentcode(
        self, method: str = "WALLET", method_id: str = "106177237"
    ) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        methods = {
            "paymentMethodType": method,
            "paymentMethodId": method_id,
            "paymentCodeSessionId": str(uuid4()).upper(),
        }
        paymentcode = (
            await self.session.post(
                "https://app4.paypay.ne.jp/bff/v2/createPaymentOneTimeCodeForHome",
                headers=self.headers,
                json=methods,
                params=self.params,
            )
        ).json()

        if paymentcode["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(paymentcode)

        if paymentcode["header"]["resultCode"] != "S0000":
            raise PayPayError(paymentcode)

        return paymentcode

    async def get_point_history(self) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        params = {"origin": "POINT_PORTAL", "payPayLang": "ja"}
        phistory = (
            await self.session.get(
                "https://www.paypay.ne.jp/portal/proxy/bff/v1/getPointBalance",
                headers=self.headers,
                params=params,
            )
        ).json()

        if phistory["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(phistory)

        if phistory["header"]["resultCode"] != "S0000":
            raise PayPayError(phistory)

        return phistory

    async def search_p2puser(
        self, user_id: str, size: int = 10, is_global: bool = True, order: int = 0
    ) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        payload = {
            "searchTerm": user_id,
            "pageToken": "",
            "pageSize": size,
            "isIngressSendMoney": False,
            "searchTypes": "GLOBAL_SEARCH",
        }
        if not is_global:
            payload["searchTypes"] = "FRIEND_AND_CANDIDATE_SEARCH"

        p2puser = (
            await self.session.post(
                "https://app4.paypay.ne.jp/p2p/v3/searchP2PUser",
                headers=self.headers,
                json=payload,
                params=self.params,
            )
        ).json()
        if p2puser["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(p2puser)

        if p2puser["header"]["resultCode"] != "S0000":
            if (
                p2puser["error"]["displayErrorResponse"]["description"]
                == "しばらく時間をおいて、再度お試しください"
            ):
                raise PayPayError("レート制限に達しました")

            raise PayPayError(p2puser)

        if p2puser["payload"]["searchResultEnum"] == "NO_USERS_FOUND":
            raise PayPayError("ユーザーが見つかりませんでした")

        if is_global:
            self.found_user_name = p2puser["payload"]["globalSearchResult"][
                "displayName"
            ]
            self.found_user_icon = p2puser["payload"]["globalSearchResult"]["photoUrl"]
            self.found_user_external_id = p2puser["payload"]["globalSearchResult"][
                "externalId"
            ]
        else:
            self.found_user_name = p2puser["payload"][
                "friendsAndCandidatesSearchResults"
            ]["friends"][order]["displayName"]
            self.found_user_icon = p2puser["payload"][
                "friendsAndCandidatesSearchResults"
            ]["friends"][order]["photoUrl"]
            self.found_user_external_id = p2puser["payload"][
                "friendsAndCandidatesSearchResults"
            ]["friends"][order]["externalId"]

        return p2puser

    async def initialize_chatroom(self, external_id: str) -> dict:
        if not self.access_token:
            raise PayPayLoginError("まずはログインしてください")

        payload = {
            "returnChatRoom": True,
            "shouldCheckMessageForFriendshipAppeal": True,
            "externalUserId": external_id,
        }
        initialize = (
            await self.session.post(
                "https://app4.paypay.ne.jp/p2p/v1/initialiseOneToOneAndLinkChatRoom",
                headers=self.headers,
                json=payload,
                params=self.params,
            )
        ).json()
        if initialize["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(initialize)

        if initialize["header"]["resultCode"] == "S5000":
            raise PayPayError("チャットルームが見つかりませんでした")

        if initialize["header"]["resultCode"] != "S0000":
            raise PayPayError(initialize)

        self.found_chatroom_id = initialize["payload"]["chatRoom"]["chatRoomId"]

        return initialize

    async def alive(self) -> None:
        alive = (
            await self.session.get(
                "https://app4.paypay.ne.jp/bff/v2/getPrioritizedPaymentMethodsConfiguration?onlyPreferredPaymentMethod=true&payPayLang=ja",
                headers=self.headers,
            )
        ).json()
        if alive["header"]["resultCode"] == "S0001":
            raise PayPayLoginError(alive)

        if alive["header"]["resultCode"] != "S0000":
            raise PayPayError(alive)

        await self.session.get(
            "https://app4.paypay.ne.jp/bff/v1/getGlobalServiceStatus?payPayLang=en",
            headers=self.headers,
        )
        await self.session.get(
            "https://app4.paypay.ne.jp/bff/v1/getWalletWidgetInfo?includePayLaterCcInfo=false&payPayLang=ja",
            headers=self.headers,
        )
        await self.session.post(
            "https://app4.paypay.ne.jp/bff/v2/getHomeDisplayInfo?includeBeginnerFlag=false&includeSkinInfoFlag=false&networkStatus=WIFI&payPayLang=ja",
            headers=self.headers,
            json={"userLat": None, "userLon": None},
        )
        await self.session.get(
            "https://app4.paypay.ne.jp/bff/v2/getProfileDisplayInfo?includeExternalProfileSync=true&actionKeys=&payPayLang=ja",
            headers=self.headers,
        )
