"""
MobileSasa SMS & WhatsApp Integration Client
Docs: https://docs.mobilesasa.com/

Supports:
- SMS: Single SMS (/v1/send/message), Bulk SMS (/v1/send/bulk), Balance check, Sender IDs list, Message delivery report
- WhatsApp: Send template message (/api/v1/whatsapp/send), List WhatsApp accounts (/api/v1/whatsapp/accounts), Connect account
"""
import logging
import requests
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


class MobileSasaError(Exception):
    """Base exception for MobileSasa API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class MobileSasaClient:
    """
    Client for interacting with MobileSasa API for SMS and WhatsApp
    """
    SMS_BASE_URL = "https://api.mobilesasa.com/v1"
    WHATSAPP_BASE_URL = "https://api.mobilesasa.com/api/v1/whatsapp"
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        api_token: str,
        sender_id: Optional[str] = None,
        account_uuid: Optional[str] = None,
        sender_phone: Optional[str] = None,
    ):
        """
        Initialize MobileSasa client
        :param api_token: Bearer token (mbs_...)
        :param sender_id: Approved SMS Sender ID (e.g. MOBILESASA or custom)
        :param account_uuid: Connected WhatsApp Account UUID
        :param sender_phone: Registered WhatsApp Phone Number (MSISDN)
        """
        self.api_token = (api_token or "").strip()
        self.sender_id = (sender_id or "").strip()
        self.account_uuid = (account_uuid or "").strip()
        self.sender_phone = (sender_phone or "").strip()

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ==========================================
    # SMS METHODS
    # ==========================================

    def send_sms(self, phone: str, message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a single SMS message
        POST https://api.mobilesasa.com/v1/send/message
        Payload: {"senderID": "...", "phone": "07xxxxxxxx", "message": "..."}
        """
        effective_sender = sender_id or self.sender_id
        if not effective_sender:
            raise MobileSasaError("Sender ID is required to send SMS.")
        if not phone:
            raise MobileSasaError("Recipient phone number is required.")
        if not message:
            raise MobileSasaError("Message content cannot be empty.")

        url = f"{self.SMS_BASE_URL}/send/message"
        payload = {
            "senderID": effective_sender,
            "phone": str(phone).strip(),
            "message": message,
        }

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=self.DEFAULT_TIMEOUT)
            data = resp.json() if resp.content else {}
            if resp.status_code in (200, 201) and (data.get("status") is True or data.get("responseCode") in ("0200", 200)):
                return {
                    "success": True,
                    "message_id": data.get("messageId"),
                    "raw": data,
                }
            error_msg = data.get("message") or f"HTTP {resp.status_code}: Failed to send SMS"
            logger.warning(f"MobileSasa send_sms failed: {error_msg} (Response: {data})")
            return {
                "success": False,
                "error": error_msg,
                "raw": data,
                "status_code": resp.status_code,
            }
        except requests.RequestException as e:
            logger.error(f"MobileSasa send_sms network exception: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def send_bulk_sms(self, phones: Union[List[str], str], message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send bulk SMS to multiple phone numbers
        POST https://api.mobilesasa.com/v1/send/bulk
        Payload: {"senderID": "...", "phones": "0712...,0722...", "message": "..."}
        """
        effective_sender = sender_id or self.sender_id
        if not effective_sender:
            raise MobileSasaError("Sender ID is required to send bulk SMS.")

        if isinstance(phones, (list, tuple, set)):
            phones_str = ",".join(str(p).strip() for p in phones if str(p).strip())
        else:
            phones_str = str(phones).strip()

        if not phones_str:
            raise MobileSasaError("At least one recipient phone number is required.")
        if not message:
            raise MobileSasaError("Message content cannot be empty.")

        url = f"{self.SMS_BASE_URL}/send/bulk"
        payload = {
            "senderID": effective_sender,
            "phones": phones_str,
            "message": message,
        }

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=self.DEFAULT_TIMEOUT)
            data = resp.json() if resp.content else {}
            if resp.status_code in (200, 201) and (data.get("status") is True or data.get("responseCode") in ("0200", 200)):
                return {
                    "success": True,
                    "bulk_id": data.get("bulkId"),
                    "raw": data,
                }
            error_msg = data.get("message") or f"HTTP {resp.status_code}: Failed to send bulk SMS"
            logger.warning(f"MobileSasa send_bulk_sms failed: {error_msg} (Response: {data})")
            return {
                "success": False,
                "error": error_msg,
                "raw": data,
                "status_code": resp.status_code,
            }
        except requests.RequestException as e:
            logger.error(f"MobileSasa send_bulk_sms network exception: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_balance(self) -> Dict[str, Any]:
        """
        Check account balance and remaining SMS units
        GET https://api.mobilesasa.com/v1/balance
        """
        url = f"{self.SMS_BASE_URL}/balance"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.DEFAULT_TIMEOUT)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return {
                    "success": True,
                    "data": data,
                }
            return {
                "success": False,
                "error": data.get("message") or f"HTTP {resp.status_code}",
                "raw": data,
            }
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_sender_ids(self) -> Dict[str, Any]:
        """
        Get list of approved sender IDs
        GET https://api.mobilesasa.com/v1/senderids
        """
        url = f"{self.SMS_BASE_URL}/senderids"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.DEFAULT_TIMEOUT)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return {
                    "success": True,
                    "data": data,
                }
            return {
                "success": False,
                "error": data.get("message") or f"HTTP {resp.status_code}",
                "raw": data,
            }
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_delivery_report(self, message_id: str) -> Dict[str, Any]:
        """
        Get delivery report for a sent message
        GET https://api.mobilesasa.com/v1/report/message/<messageId>
        """
        url = f"{self.SMS_BASE_URL}/report/message/{message_id}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.DEFAULT_TIMEOUT)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return {
                    "success": True,
                    "data": data,
                }
            return {
                "success": False,
                "error": data.get("message") or f"HTTP {resp.status_code}",
                "raw": data,
            }
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # WHATSAPP METHODS
    # ==========================================

    def get_whatsapp_accounts(self) -> Dict[str, Any]:
        """
        Fetch connected WhatsApp accounts (WABA)
        GET https://api.mobilesasa.com/api/v1/whatsapp/accounts
        """
        url = f"{self.WHATSAPP_BASE_URL}/accounts"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.DEFAULT_TIMEOUT)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200:
                return {
                    "success": True,
                    "accounts": data.get("data") or data,
                    "raw": data,
                }
            return {
                "success": False,
                "error": data.get("message") or f"HTTP {resp.status_code}",
                "raw": data,
            }
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def send_whatsapp(
        self,
        recipients: Union[List[str], str],
        template_uuid: str,
        params: Optional[List[str]] = None,
        account_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp template message
        POST https://api.mobilesasa.com/api/v1/whatsapp/send
        Payload:
        {
            "account_uuid": "...",
            "template_uuid": "...",
            "recipients": ["0712345678"],
            "params": ["param1", "param2"]
        }
        """
        effective_account = account_uuid or self.account_uuid
        if not effective_account:
            raise MobileSasaError("WhatsApp Account UUID is required.")
        if not template_uuid:
            raise MobileSasaError("WhatsApp Template UUID is required.")

        if isinstance(recipients, (list, tuple, set)):
            recipients_list = [str(r).strip() for r in recipients if str(r).strip()]
        else:
            recipients_list = [str(recipients).strip()]

        if not recipients_list:
            raise MobileSasaError("At least one recipient phone number is required.")

        url = f"{self.WHATSAPP_BASE_URL}/send"
        payload = {
            "account_uuid": effective_account,
            "template_uuid": template_uuid,
            "recipients": recipients_list,
            "params": params or [],
        }

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=self.DEFAULT_TIMEOUT)
            data = resp.json() if resp.content else {}
            if resp.status_code in (200, 201) and (data.get("success") is True or data.get("status") is True):
                return {
                    "success": True,
                    "data": data.get("data") or data,
                    "raw": data,
                }
            error_msg = data.get("message") or f"HTTP {resp.status_code}: Failed to send WhatsApp message"
            logger.warning(f"MobileSasa send_whatsapp failed: {error_msg} (Response: {data})")
            return {
                "success": False,
                "error": error_msg,
                "raw": data,
                "status_code": resp.status_code,
            }
        except requests.RequestException as e:
            logger.error(f"MobileSasa send_whatsapp network exception: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# ==========================================
# CONFIGURATION RESOLVERS
# ==========================================

def get_mobilesasa_sms_client(school=None) -> Optional[MobileSasaClient]:
    """
    Resolve active MobileSasa SMS configuration for a school or globally.
    School admins use their own credentials if configured, or fall back to platform
    global settings ONLY if SuperAdmin granted allow_system_sms.
    """
    from superadmin.models import GlobalSMSConfiguration, SchoolSMSConfiguration

    # 1. Check school-specific configuration if school provided
    if school:
        school_config = SchoolSMSConfiguration.objects.filter(school=school, provider='mobilesasa', is_active=True).first()
        if school_config and school_config.mobilesasa_api_token:
            return MobileSasaClient(
                api_token=school_config.mobilesasa_api_token,
                sender_id=school_config.mobilesasa_sender_id or school_config.custom_sender_id,
            )
        # If school does not have custom active credentials, only allow fallback if Superadmin enabled it
        if not getattr(school, 'allow_system_sms', False):
            return None

    # 2. Check global configuration (platform level or allowed school fallback)
    global_config = GlobalSMSConfiguration.objects.filter(provider='mobilesasa', is_active=True).first()
    if global_config and global_config.mobilesasa_api_token:
        return MobileSasaClient(
            api_token=global_config.mobilesasa_api_token,
            sender_id=global_config.mobilesasa_sender_id or global_config.default_sender_id,
        )

    return None


def get_mobilesasa_whatsapp_client(school=None) -> Optional[MobileSasaClient]:
    """
    Resolve active MobileSasa WhatsApp configuration for a school or globally.
    School admins use their own credentials if configured, or fall back to platform
    global settings ONLY if SuperAdmin granted allow_system_whatsapp.
    """
    from superadmin.models import GlobalWhatsAppConfiguration, SchoolWhatsAppConfiguration

    # 1. Check school-specific configuration
    if school:
        school_config = SchoolWhatsAppConfiguration.objects.filter(school=school, provider='mobilesasa', is_active=True).first()
        if school_config and school_config.mobilesasa_api_token:
            return MobileSasaClient(
                api_token=school_config.mobilesasa_api_token,
                account_uuid=school_config.mobilesasa_account_uuid,
                sender_phone=school_config.mobilesasa_sender_phone or school_config.custom_sender_phone,
            )
        # If school does not have custom active credentials, only allow fallback if Superadmin enabled it
        if not getattr(school, 'allow_system_whatsapp', False):
            return None

    # 2. Check global configuration (platform level or allowed school fallback)
    global_config = GlobalWhatsAppConfiguration.objects.filter(provider='mobilesasa', is_active=True).first()
    if global_config and global_config.mobilesasa_api_token:
        return MobileSasaClient(
            api_token=global_config.mobilesasa_api_token,
            account_uuid=global_config.mobilesasa_account_uuid,
            sender_phone=global_config.mobilesasa_sender_phone or global_config.default_sender_phone,
        )

    return None
