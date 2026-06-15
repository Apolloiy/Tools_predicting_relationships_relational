import re
import logging

TAG = __name__
logger = logging.getLogger(__name__)

EMOTION_EMOJI_MAP = {
    "HAPPY": "🙂",
    "SAD": "😔",
    "ANGRY": "😡",
    "NEUTRAL": "😶",
    "FEARFUL": "😰",
    "DISGUSTED": "🤢",
    "SURPRISED": "😲",
    "EMO_UNKNOWN": "😶",
}

def lang_tag_filter(text: str) -> dict | str:
    tag_pattern = r"<\|([^|]+)\|>"
    all_tags = re.findall(tag_pattern, text)
    clean_text = re.sub(tag_pattern, "", text).strip()

    if not all_tags:
        return clean_text

    language = all_tags[0] if len(all_tags) > 0 else "zh"
    emotion = all_tags[1] if len(all_tags) > 1 else "NEUTRAL"

    result = {
        "content": clean_text,
        "language": language,
        "emotion": emotion,
    }

    if emotion in EMOTION_EMOJI_MAP:
        result["emotion"] = EMOTION_EMOJI_MAP[emotion]

    return result