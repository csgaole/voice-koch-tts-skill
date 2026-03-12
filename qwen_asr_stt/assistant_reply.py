#!/usr/bin/env python3
import json
import re
import time
import urllib.parse
import urllib.request


WEATHER_CODE_TEXT = {
    0: "晴",
    1: "大致晴朗",
    2: "多云",
    3: "阴",
    45: "有雾",
    48: "有霜雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "较强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    81: "较强阵雨",
    82: "暴雨阵雨",
    95: "雷暴",
}


def is_weather_query(text: str) -> bool:
    lowered = text.strip().lower()
    keywords = ["天气", "气温", "温度", "下雨", "下雪", "冷不冷", "热不热", "weather", "temperature"]
    return any(keyword in lowered for keyword in keywords)


def temperature_for_model(model: str) -> float | int:
    normalized = (model or "").strip().lower()
    if normalized == "kimi-k2.5":
        return 1
    return 0.3


def post_chat_reply(
    user_text: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
) -> str:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "temperature": temperature_for_model(model),
        "max_tokens": 160,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个简短中文语音助手。"
                    "当用户说的话与机械臂无关时，你应该直接回答用户的问题，而不是拒绝。"
                    "回答要自然、简短、适合直接 TTS 播放，控制在两到三句话内。"
                    "如果问题带有明显高风险、专业建议或你不确定，就明确说明不确定并给出保守回答。"
                    "不要输出 markdown，不要自称只负责机械臂。"
                ),
            },
            {"role": "user", "content": user_text},
        ],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    raw = post_json_request(request, timeout=timeout, retries=1)
    body = json.loads(raw)
    return str(body["choices"][0]["message"]["content"]).strip()


def post_json_request(request: urllib.request.Request, timeout: int, retries: int = 1) -> str:
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            wait_seconds = min(2 * (attempt + 1), 4)
            time.sleep(wait_seconds)
    raise RuntimeError(f"assistant reply request failed: {last_error}") from last_error


def fallback_general_reply(user_text: str) -> str:
    lowered = user_text.strip().lower()
    if any(keyword in lowered for keyword in ["小鹏", "汽车", "车", "特斯拉", "比亚迪"]):
        return "小鹏汽车整体偏智能化和科技感，座舱和辅助驾驶是它比较受关注的点。要是你愿意，我也可以继续用语音给你简单聊聊它的优缺点。"
    return "这个问题我可以陪你聊，不过刚才网络有点慢。你可以再问一次，我会尽量简短回答。"


def _extract_location(query: str, default_location: str) -> str:
    match = re.search(r"(上海|北京|杭州|深圳|广州|苏州|南京|成都|武汉|西安|香港)", query)
    if match:
        return match.group(1)
    return default_location


def get_weather_reply(query: str, default_location: str, timeout: int) -> str:
    location = _extract_location(query, default_location)

    geocode_url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode({"name": location, "count": 1, "language": "zh", "format": "json"})
    )
    with urllib.request.urlopen(geocode_url, timeout=timeout) as response:
        geocode_body = json.loads(response.read().decode("utf-8"))

    results = geocode_body.get("results") or []
    if not results:
        return f"我暂时没查到{location}的天气。"

    first = results[0]
    latitude = first["latitude"]
    longitude = first["longitude"]
    resolved_name = first.get("name", location)

    forecast_url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 1,
            }
        )
    )
    with urllib.request.urlopen(forecast_url, timeout=timeout) as response:
        forecast_body = json.loads(response.read().decode("utf-8"))

    current = forecast_body.get("current", {})
    daily = forecast_body.get("daily", {})
    current_temp = current.get("temperature_2m")
    weather_code = current.get("weather_code")
    wind_speed = current.get("wind_speed_10m")
    max_temp = (daily.get("temperature_2m_max") or [None])[0]
    min_temp = (daily.get("temperature_2m_min") or [None])[0]
    weather_text = WEATHER_CODE_TEXT.get(weather_code, "天气一般")

    return (
        f"{resolved_name}今天天气{weather_text}，现在大约{current_temp}度，"
        f"今天最高{max_temp}度，最低{min_temp}度，风速大约每小时{wind_speed}公里。"
    )
