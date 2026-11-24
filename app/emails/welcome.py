from html import escape

from app.emails.base import EmailContent, wrap_html


def render(payload: dict) -> EmailContent:
    name = payload["name"]
    password = payload["temporary_password"]

    text = (
        f"Hi {name},\n\n"
        "Your Workflow account has been created.\n\n"
        f"Email: {payload['email']}\n"
        f"Temporary password: {password}\n\n"
        "Please sign in with these details and change your password right away.\n\n"
        "- The Workflow team"
    )

    html = wrap_html(
        f"Welcome to Workflow, {name}!",
        f"""
        <p>Your account has been created.</p>
        <p><b>Email:</b> {escape(payload['email'])}<br>
           <b>Temporary password:</b>
           <code style="background:#f3f3f3;padding:2px 6px">{escape(password)}</code></p>
        <p>Please sign in with these details and change your password right away.</p>
        """,
    )

    return EmailContent(subject="Welcome to Workflow", text=text, html=html)
