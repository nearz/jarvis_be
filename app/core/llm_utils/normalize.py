from typing import Union


def get_msg_content_text(content: Union[str, list[Union[str, dict]]]) -> str:
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, str):
                texts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                texts.append(part.get("text", ""))
        return "\n".join(texts)
    else:
        return str(content)
