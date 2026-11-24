from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text: str
    html: str


def wrap_html(title: str, body_html: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;color:#222">
      <h2>{escape(title)}</h2>
      {body_html}
      <p style="color:#888;font-size:12px;margin-top:32px">Workflow</p>
    </div>"""
