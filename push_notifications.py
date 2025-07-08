import json
import logging
from pywebpush import webpush, WebPushException
from flask import current_app


class PushNotificationService:
    @staticmethod
    def send_notification(subscription_info, title, body, url=None, icon=None):
        """
        Send a push notification to a specific subscription.
        """
        try:
            # If passed as string, parse to dict
            if isinstance(subscription_info, str):
                subscription_info = json.loads(subscription_info)

            vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
            vapid_claims = current_app.config.get('VAPID_CLAIMS', {})

            if not vapid_private_key or not vapid_claims:
                logging.error("VAPID configuration missing.")
                return False

            payload = {
                'title': title,
                'body': body,
                'icon': icon or '/static/icons/icon-192.svg',
                'url': url or '/dashboard'
            }

            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims
            )
            logging.info(f"Push notification sent: {title}")
            return True

        except WebPushException as e:
            logging.error(f"WebPushException: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logging.error(f"Push service error response: {error_data}")
                except Exception:
                    logging.error("Failed to parse error response from push service.")
            return False

        except json.JSONDecodeError:
            logging.error("Invalid subscription_info JSON format.")
            return False

        except Exception as e:
            logging.error(f"Unexpected error sending push: {str(e)}")
            return False

    @staticmethod
    def send_to_user(user, title, body, url=None, icon=None):
        """
        Send a notification to a specific user based on their stored subscription.
        """
        if not hasattr(user, 'push_subscription') or not user.push_subscription:
            logging.warning(f"No push subscription for user {getattr(user, 'id', 'unknown')}")
            return False

        try:
            return PushNotificationService.send_notification(
                subscription_info=user.push_subscription,
                title=title,
                body=body,
                url=url,
                icon=icon
            )
        except Exception as e:
            logging.error(f"Error sending push to user {getattr(user, 'id', 'unknown')}: {str(e)}")
            return False

    @staticmethod
    def send_test_notification(user):
        """
        Send a test notification to verify push setup.
        """
        return PushNotificationService.send_to_user(
            user,
            "Test Notification",
            "This is a test notification from CarServicePro.",
            "/settings",
            "/static/icons/icon-192.svg"
        )
