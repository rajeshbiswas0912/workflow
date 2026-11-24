from app.emails import welcome
from app.emails.base import EmailContent

_RENDERERS = {
    "welcome_email": welcome.render,
}


def render_email(message_type: str, payload: dict) -> EmailContent:
    return _RENDERERS[message_type](payload)
