from pywebpush import webpush, WebPushException
import os
import logging
import json


def send_push_notification(subscription_info, title, message, icon=None, badge=None):
    """Send a web push notification to a user"""
    try:
        # VAPID keys should be generated and stored as environment variables
        # For development, you can generate them using: webpush --gen-vapid-keys
        vapid_private_key = os.environ.get('VAPID_PRIVATE_KEY')
        vapid_public_key = os.environ.get('VAPID_PUBLIC_KEY')
        vapid_claims = {
            "sub": "mailto:admin@example.com"  # Replace with your contact email
        }
        
        if not vapid_private_key or not vapid_public_key:
            logging.warning("VAPID keys not configured. Push notifications will not work.")
            return False
        
        # Prepare notification payload
        payload = {
            "title": title,
            "body": message,
            "icon": icon or "/static/icons/icon-192.svg",
            "badge": badge or "/static/icons/icon-192.svg",
            "tag": "service-reminder",
            "requireInteraction": True,
            "actions": [
                {
                    "action": "view",
                    "title": "View Details",
                    "icon": "/static/icons/icon-192.svg"
                },
                {
                    "action": "dismiss",
                    "title": "Dismiss",
                    "icon": "/static/icons/icon-192.svg"
                }
            ]
        }
        
        # Send the notification
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims
        )
        
        logging.info(f"Push notification sent successfully: {title}")
        return True
        
    except WebPushException as ex:
        logging.error(f"Failed to send push notification: {repr(ex)}")
        if ex.response and ex.response.json():
            extra = ex.response.json()
            logging.error(f"Remote service replied with: {extra.code}: {extra.message}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending push notification: {str(e)}")
        return False


def generate_vapid_keys():
    """Generate VAPID keys for push notifications"""
    # This is a utility function for generating VAPID keys
    # In production, generate these once and store them securely
    from pywebpush import webpush
    return webpush.generate_vapid_keys()
