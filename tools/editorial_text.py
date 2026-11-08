"""Spacing rules for generated editorial prose, never for Hebrew or model records."""
import re


def spaced(text):
    text = re.sub(r'([가-힣])(?=\d)', r'\1 ', text)
    text = re.sub(r'(\d)(장|편)(?=\d)', r'\1\2 ', text)
    text = re.sub(r',(?![\s\d])(?=[가-힣A-Za-z])', ', ', text)
    text = re.sub(r'(Genesis|Génesis)(?=\d)', r'\1 ', text)
    text = re.sub(r'(?<=[가-힣])\.(?=[가-힣\d])', '. ', text)
    return text


def passage_prose(passage):
    for field in ('reference', 'title', 'subtitle', 'intro', 'notes', 'glosses'):
        if field not in passage:
            continue
        value = passage[field]
        if isinstance(value, str):
            passage[field] = spaced(value)
        elif isinstance(value, dict):
            passage[field] = {key: spaced(text) for key, text in value.items()}
        else:
            passage[field] = [{key: spaced(text) for key, text in item.items()} for item in value]
